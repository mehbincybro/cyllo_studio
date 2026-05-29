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
    'name': "Cyllo Project Product",
    'description': 'Add Products to Project Tasks',
    'summary': 'Add Products to Project Tasks and link with Sale Order',
    'version': '1.0',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'category': 'Services/Project',
    'depends': ['cyllo_project_base', 'sale_project'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/project_task_product_catalog_wizard_views.xml',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_project_product/static/src/js/product_catalog_patch.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
