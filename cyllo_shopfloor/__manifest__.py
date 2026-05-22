# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
    'name': 'Shop Floor',
    'version': '1.0',
    'summary': 'Shopfloor Interface',
    'depends': ['mrp', 'bus', 'web'],
    'data': [
        'security/cyllo_shopfloor_security.xml',
        'security/ir.model.access.csv',
        'data/automated_mo_crone.xml',

        'views/cyllo_shopfloor_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_bom_views.xml',

        'wizards/mrp_add_component_wizard_views.xml',
        'wizards/mrp_scrap_component_wizard_views.xml',
        'wizards/mrp_reroute_wizard_views.xml',
        'wizards/mrp_add_workorder_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_shopfloor/static/src/js/cyllo_shopfloor.js',
            'cyllo_shopfloor/static/src/xml/cyllo_shopfloor_template.xml',
            'cyllo_shopfloor/static/src/js/backend_listener.js',
        ],
    },
    'installable': True,
    'application': True,
}
