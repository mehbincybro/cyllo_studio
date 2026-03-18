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
    'name': 'Manufacturing MPS',
    'version': "1.0",
    'summary': "",
    'description': "",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['mrp'],

    'data': [
        'views/mrp_mps_schedule_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_manufacturing_mps/static/src/xml/mrp_mps_schedule.xml',
            'cyllo_manufacturing_mps/static/src/js/mrp_mps_schedule.js',

        ],
    },

    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
