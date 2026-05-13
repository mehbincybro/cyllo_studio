# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'Green Metrics',
    'version': '1.0',
    'category': 'Sustainability',
    'summary': 'Carbon emission sources, factors, and assignment rules',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['base', 'project', 'mrp', 'fleet', 'account', 'product'],
    'icon': '/cyllo_green_metrics/static/description/cyllo_green_metrics.svg',
    'data': [
        'data/project_data.xml',
        'data/credit_product_data.xml',
        'security/ir.model.access.csv',
        'views/carbon_gas_views.xml',
        'views/carbon_scope_views.xml',
        'views/carbon_source_views.xml',
        'views/carbon_factor_views.xml',
        'views/carbon_rule_views.xml',
        'views/carbon_activity_views.xml',
        'views/carbon_wizard_views.xml',
        'views/carbon_calculation_views.xml',
        'views/mrp_routing_workcenter_views.xml',
        'views/mrp_workorder_views.xml',
        'views/project_task_views.xml',
        'views/carbon_dashboard_action.xml',
        'views/res_config_settings_views.xml',
        'views/credit_transfer_views.xml',
        'views/product_views.xml',
        'views/carbon_menu.xml',
        'views/res_company_views.xml',
        'views/fleet_vehicle_views.xml',
        'reports/carbon_report.xml',
        'data/fleet_cron.xml',
    ],
    'demo': [
        'demo/carbon_demo.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'cyllo_green_metrics/static/src/css/green_dashboard.scss',
            'cyllo_green_metrics/static/src/js/green_dashboard.js',
            'cyllo_green_metrics/static/src/xml/green_dashboard.xml',
        ],
    },
    'application': True,
}
