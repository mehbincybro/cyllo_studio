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
    'name': 'Installment Payment',
    'version': '1.0.0',
    'summary': """Installment Payment for Invoices""",
    'description': "Installment payment option on invoice",
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['account', 'cyllo_advance_payment'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/installment_payment_views.xml',
        'views/account_move_views.xml',
        'report/report_invoice.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_installment_payment/static/src/css/installment_style.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
