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
    'name': 'Visiting Card Digitization',
    'version': '1.0.0',
    'category': 'CRM',
    'summary': "Digitize Visiting Card Automatically",
    'description': """This module helps to retrieve data from pdf/image files and 
    generate the field values of crm module automatically.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'crm', 'cyllo_ocr_digitization', 'cyllo_crm',
                'cyllo_ai'],
    'data': [
        'security/ir.model.access.csv',
        'views/cyllo_visiting_card_views.xml',
        'views/crm_visiting_card_upload.xml',
        'views/res_partner_form_view.xml',
        'wizard/visiting_card_upload_wizard_views.xml',
    ],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
