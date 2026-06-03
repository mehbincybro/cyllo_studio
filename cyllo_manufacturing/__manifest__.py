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
    'name': 'Cyllo Manufacturing',
    'version': '1.0',
    'summary': 'Central Module for MRP features',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/bom_stock_report_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
