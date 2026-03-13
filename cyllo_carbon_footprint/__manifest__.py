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
    'name': 'Carbon Footprint',
    'version': '1.0.0',
    'category': 'Sustainability',
    'summary': 'Carbon emission sources, factors, and assignment rules',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['base'],
    'icon': '/cyllo_carbon_footprint/static/description/cyllo_carbon_footprint.svg',
    'data': [
        'security/ir.model.access.csv',
        'views/carbon_gas_views.xml',
        'views/carbon_scope_views.xml',
        'views/carbon_source_views.xml',
        'views/carbon_factor_views.xml',
        'views/carbon_rule_views.xml',
        'views/carbon_activity_views.xml',
        'views/carbon_wizard_views.xml',
        'views/carbon_calculation_views.xml',
        'views/carbon_menu.xml',
        'reports/carbon_report.xml',
    ],
    'demo': [
        'demo/carbon_demo.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
