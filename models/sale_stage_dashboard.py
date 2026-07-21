from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class SaleStageDashboard(models.TransientModel):
    _name = 'sale.stage.dashboard'
    _description = 'Sale Order Stage Dashboard'

    date_filter = fields.Selection(
        selection=[
            ('today', 'Today'),
            ('week', 'Last 7 Days'),
            ('month', 'Last 30 Days'),
            ('custom', 'Custom Range'),
        ],
        string='Period Filter',
        default='today',
        required=True,
    )
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    period_label = fields.Char(string='Period Label', readonly=True)
    total_orders = fields.Integer(string='Total Orders (All Time)', readonly=True)
    total_period = fields.Integer(string='Total Orders (Period)', readonly=True)
    line_ids = fields.One2many(
        'sale.stage.dashboard.line', 'dashboard_id', string='Stage Lines', readonly=True
    )

    def _local_to_utc(self, local_datetime):
        """Convert a naive local datetime to UTC datetime for database querying."""
        return fields.Datetime.context_timestamp(self, local_datetime)

    def _get_period_bounds(self):
        self.ensure_one()
        today = fields.Date.context_today(self)

        def date_to_start_utc(d):
            """Convert date to start of day in UTC."""
            naive_local = datetime.combine(d, datetime.min.time())
            return self._local_to_utc(naive_local)

        def date_to_end_utc(d):
            """Convert date to end of day in UTC."""
            naive_local = datetime.combine(d, datetime.max.time())
            return self._local_to_utc(naive_local)

        if self.date_filter == 'today':
            return (
                date_to_start_utc(today),
                date_to_end_utc(today),
                _('Today'),
            )
        if self.date_filter == 'week':
            start_date = today - timedelta(days=6)
            return (
                date_to_start_utc(start_date),
                date_to_end_utc(today),
                _('Last 7 Days'),
            )
        if self.date_filter == 'month':
            start_date = today - timedelta(days=29)
            return (
                date_to_start_utc(start_date),
                date_to_end_utc(today),
                _('Last 30 Days'),
            )
        if self.date_filter == 'custom':
            if not self.date_from or not self.date_to:
                raise UserError(_('Please select both From and To dates for a custom range.'))
            if self.date_from > self.date_to:
                raise UserError(_('The From date must be before the To date.'))
            return (
                date_to_start_utc(self.date_from),
                date_to_end_utc(self.date_to),
                '%s - %s' % (self.date_from, self.date_to),
            )
        return None, None, _('All Time')

    @api.model
    def _prepare_dashboard_vals(self, vals=None):
        vals = dict(vals or {})
        dashboard = self.new(vals)
        period_start, period_end, period_label = dashboard._get_period_bounds()

        stages = self.env['sale.order.stage'].search([], order='sequence asc')
        total_all = self.env['sale.order'].search_count([])

        period_domain = []
        if period_start and period_end:
            period_domain = [
                ('date_order', '>=', period_start),
                ('date_order', '<=', period_end),
            ]
        total_period = self.env['sale.order'].search_count(period_domain)

        lines = []
        for stage in stages:
            all_count = self.env['sale.order'].search_count([('stage_id', '=', stage.id)])
            period_count = self.env['sale.order'].search_count([
                ('stage_id', '=', stage.id),
                *period_domain,
            ])
            lines.append((0, 0, {
                'stage_id': stage.id,
                'stage_name': stage.name,
                'total_count': all_count,
                'period_count': period_count,
                'is_urgent': stage.is_urgent_stage,
                'is_cancel': stage.is_cancel_stage,
            }))

        vals.update({
            'period_label': period_label,
            'total_orders': total_all,
            'total_period': total_period,
            'line_ids': [(5, 0, 0)] + lines,
        })
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = [self._prepare_dashboard_vals(vals) for vals in vals_list]
        return super().create(prepared_vals_list)

    def _get_form_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': 'sale.stage.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('sale_stage_dashboard.view_sale_stage_dashboard_form').id,
            'target': 'current',
        }

    @api.model
    def action_open_dashboard(self):
        """Create a saved dashboard record so line buttons work immediately."""
        dashboard = self.create({'date_filter': 'today'})
        return dashboard._get_form_action()

    def action_refresh(self):
        """Reload the dashboard using the selected period filter."""
        self.ensure_one()
        dashboard = self.env['sale.stage.dashboard'].create({
            'date_filter': self.date_filter,
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        return dashboard._get_form_action()


class SaleStageDashboardLine(models.TransientModel):
    _name = 'sale.stage.dashboard.line'
    _description = 'Sale Stage Dashboard Line'

    dashboard_id = fields.Many2one('sale.stage.dashboard', ondelete='cascade')
    stage_id = fields.Many2one('sale.order.stage', string='Stage', readonly=True)
    stage_name = fields.Char(string='Stage', readonly=True)
    total_count = fields.Integer(string='All Time', readonly=True)
    period_count = fields.Integer(string='Period', readonly=True)
    is_urgent = fields.Boolean(readonly=True)
    is_cancel = fields.Boolean(readonly=True)

    def action_open_all_orders(self):
        """Open all orders for this stage."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orders – %s' % self.stage_name,
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('stage_id', '=', self.stage_id.id)],
            'context': {'search_default_stage_id': self.stage_id.id},
        }

    def action_open_period_orders(self):
        """Open orders for this stage within the selected dashboard period."""
        self.ensure_one()
        dashboard = self.dashboard_id
        period_start, period_end, period_label = dashboard._get_period_bounds()
        domain = [('stage_id', '=', self.stage_id.id)]
        if period_start and period_end:
            domain.extend([
                ('date_order', '>=', period_start),
                ('date_order', '<=', period_end),
            ])
        return {
            'type': 'ir.actions.act_window',
            'name': '%s – %s' % (period_label, self.stage_name),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': domain,
        }
