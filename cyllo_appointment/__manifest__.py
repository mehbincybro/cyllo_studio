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
    'name': 'Appointments',
    'version': '1.0',
    'category': 'Services/Appointments',
    'summary': 'Advanced Appointment Scheduling with Resources, Staff, and Notifications',
    'description': """
        Appointment Pro - A comprehensive appointment scheduling solution for Odoo 17.

        Features:
        - Appointment Types with configurable settings
        - Resource & Staff Management
        - Time Slot Management (intervals, buffer time, working hours)
        - Email & SMS Notifications and Reminders
        - Rescheduling support
        - Minimum booking notice
        - Confirmation and follow-up messages
        - Beautiful, user-friendly interface
    """,
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': [
        'base',
        'mail',
        'calendar',
        'resource',
        'sms',
        'web',
    ],
    'data': [
        # Security
        'security/appointment_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/appointment_sequence.xml',
        'data/appointment_mail_templates.xml',
        'data/appointment_sms_templates.xml',
        # Views
        'views/appointment_type_views.xml',
        'views/appointment_resource_views.xml',
        'views/appointment_staff_views.xml',
        'views/appointment_slot_views.xml',
        'views/appointment_views.xml',
        'views/appointment_settings_views.xml',
        'views/appointment_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_appointment/static/src/css/appointment_pro.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/src/img/appointment_pro_screenshot.png'],
}
