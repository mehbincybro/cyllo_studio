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
    'name': 'Cyllo Loan Management',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Complete loan giving & taking with repayment schedules and accounting entries',
    'description': """
Cyllo Loan Management
=====================
A comprehensive loan management module supporting both loan giving and taking.

Key Features:
- Configurable loan types (personal, business, vehicle, mortgage, etc.)
- Loan giving (lending) and loan taking (borrowing) workflows
- Interest calculation: flat/reducing balance methods
- Automatic repayment schedule generation (monthly/quarterly/annually)
- Automated accounting journal entries per repayment installment
- Automated accounting journal entries on disbursement and repayment
- Overdue tracking with penalty/late fee support
- Multi-currency and multi-company support
- Full audit trail via chatter
    """,
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    # 'images': ['static/description/banner.png'],
    'depends': [
        'account',
        'mail',
    ],
    'data': [
        'security/loan_security.xml',
        'data/loan_data.xml',
        'security/ir.model.access.csv',
        'data/loan_sequence_data.xml',
        'data/loan_type_data.xml',
        'views/loan_type_views.xml',
        'views/loan_views.xml',
        'views/loan_repayment_views.xml',
        'views/loan_menu_views.xml',
        'wizards/loan_disburse_wizard_views.xml',
        'wizards/loan_close_wizard_views.xml',
        'reports/loan_report_views.xml',
        'reports/report_loan_schedule.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
