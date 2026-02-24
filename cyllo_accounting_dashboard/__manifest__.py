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
#acc
#############################################################################
{
    'name': 'Accounting Dashboard',
    'version': '1.0',
    'category': 'Accounting',
    'summary': """Accounting Dashboard""",
    'description': "Adding the dashboard functionalities for the accounting module from cyllo anlytics",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_analytics', 'account'],
    # 'icon': '',
    'data': [
        'data/dashboard_sheets.xml',
        'data/dashboard_tables.xml',
        'data/dashboard_axes.xml',
        'data/dashboard_filters.xml',
        'data/dashboard_config.xml',
        'data/dashboard_sheet_options.xml',
        'data/dashboard_menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': True,
}
