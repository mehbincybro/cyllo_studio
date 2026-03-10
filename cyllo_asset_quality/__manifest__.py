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
    'name': 'Cyllo Asset Quality Integration',
    'version': '17.0.1.0.0',
    'summary': 'Integration between Cyllo Asset Management and Cyllo Quality',
    'description': """
        This module integrates asset management with quality checks.
        Allows performing quality checks before returning leased or rented assets.
        Automatically creates maintenance requests if quality checks fail.
    """,
    'category': 'Operations',
    'author': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': [
        'cyllo_asset_management',
        'cyllo_quality'
    ],
    'data': [
        'views/quality_control_point_views.xml',
        'views/quality_check_views.xml',
        'views/asset_lease_views.xml',
        'views/asset_rental_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
