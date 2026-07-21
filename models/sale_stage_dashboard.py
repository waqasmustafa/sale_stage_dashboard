from odoo import models, fields, api
from datetime import date, datetime


class SaleStageDashboard(models.TransientModel):
    _name = 'sale.stage.dashboard'
    _description = 'Sale Order Stage Dashboard'

    total_orders = fields.Integer(string='Total Orders (All Time)', readonly=True)
    total_today = fields.Integer(string="Total Orders (Today)", readonly=True)
    line_ids = fields.One2many(
        'sale.stage.dashboard.line', 'dashboard_id', string='Stage Lines', readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())

        stages = self.env['sale.order.stage'].search([], order='sequence asc')

        total_all = self.env['sale.order'].search_count([])
        total_today = self.env['sale.order'].search_count([
            ('date_order', '>=', today_start),
            ('date_order', '<=', today_end),
        ])

        lines = []
        for stage in stages:
            all_count = self.env['sale.order'].search_count([('stage_id', '=', stage.id)])
            today_count = self.env['sale.order'].search_count([
                ('stage_id', '=', stage.id),
                ('date_order', '>=', today_start),
                ('date_order', '<=', today_end),
            ])
            lines.append((0, 0, {
                'stage_id': stage.id,
                'stage_name': stage.name,
                'total_count': all_count,
                'today_count': today_count,
                'is_urgent': stage.is_urgent_stage,
                'is_cancel': stage.is_cancel_stage,
            }))

        res.update({
            'total_orders': total_all,
            'total_today': total_today,
            'line_ids': lines,
        })
        return res

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
        dashboard = self.create({})
        return dashboard._get_form_action()

    def action_refresh(self):
        """Reload the dashboard with fresh data."""
        return self.env['sale.stage.dashboard'].create({})._get_form_action()


class SaleStageDashboardLine(models.TransientModel):
    _name = 'sale.stage.dashboard.line'
    _description = 'Sale Stage Dashboard Line'

    dashboard_id = fields.Many2one('sale.stage.dashboard', ondelete='cascade')
    stage_id = fields.Many2one('sale.order.stage', string='Stage', readonly=True)
    stage_name = fields.Char(string='Stage', readonly=True)
    total_count = fields.Integer(string='All Time', readonly=True)
    today_count = fields.Integer(string="Today", readonly=True)
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

    def action_open_today_orders(self):
        """Open today's orders for this stage."""
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        return {
            'type': 'ir.actions.act_window',
            'name': "Today – %s" % self.stage_name,
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('stage_id', '=', self.stage_id.id),
                ('date_order', '>=', today_start),
                ('date_order', '<=', today_end),
            ],
        }
