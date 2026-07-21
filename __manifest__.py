{
    'name': 'Sale Order Stage Dashboard',
    'version': '19.0.1.1.0',
    'summary': 'Dashboard showing Sale Order counts per stage (All Time & Today)',
    'description': """
Sale Order Stage Dashboard
===========================
A dedicated dashboard showing sale order counts broken down by every
custom stage defined in the sale_order_stage_management module.

Features:
- Total orders (all time) per stage
- Today's orders per stage
- Clickable counts that open a filtered sale order list
- Critical and Urgent stages highlighted in color
- Accessible from the Sales menu
    """,
    'category': 'Sales',
    'author': 'WaQas Mustafa',
    'depends': ['sale_management', 'sale_order_stage_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_stage_dashboard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
