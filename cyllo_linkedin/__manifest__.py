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
    'name': 'Cyllo LinkedIn',
    'version': '1.0',
    'category': 'Marketing',
    'summary': 'LinkedIn Integration for Cyllo',
    'description': 'LinkedIn Integration for Cyllo',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'icon': '/cyllo_linkedin/static/description/linkedin.svg',
    'depends': ['base', 'mail', 'cyllo_social_media_marketing'],
    'data': [
        'security/ir.model.access.csv',
        'views/linkedin_account_views.xml',
        'views/social_media_post_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
