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
    'name': 'Repair Floor',
    'version': '1.0',
    'summary': 'Tablet-friendly interface for Repair Technicians',
    'depends': ['cyllo_repair', 'repair'],
    'data': [
        'security/shopfloor_repair_security.xml',
        'security/ir.model.access.csv',
        'views/repair_floor_action.xml',
        'views/repair_order_views.xml',
        'views/repair_notes_views.xml',

        'wizard/edit_repair_line_views_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_shopfloor_repair/static/src/components/**/*.js',
            'cyllo_shopfloor_repair/static/src/components/**/*.xml',
            'cyllo_shopfloor_repair/static/src/repair_card/**/*.js',
            'cyllo_shopfloor_repair/static/src/repair_card/**/*.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
