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
import base64
import os
from .models.ir_ui_menu import ICONS

icons = {
    'Sales': '/cyllo_base/static/src/icons/sales.svg',
    'Restaurant': '/cyllo_base/static/src/icons/restaurant.svg',
    'Invoicing': '/cyllo_base/static/src/icons/invoicing.svg',
    'CRM': '/cyllo_base/static/src/icons/crm.svg',
    'Website': '/cyllo_base/static/src/icons/website.svg',
    'Inventory': '/cyllo_base/static/src/icons/inventory.svg',
    'Purchase': '/cyllo_base/static/src/icons/purchase.svg',
    'Point of Sale': '/cyllo_base/static/src/icons/pos.svg',
    'Project': '/cyllo_base/static/src/icons/project.svg',
    'eCommerce': '/cyllo_base/static/src/icons/eCommerce.svg',
    'Manufacturing': '/cyllo_base/static/src/icons/manufacturing.svg',
    'Email Marketing': '/cyllo_base/static/src/icons/email-marketing.svg',
    'Expenses': '/cyllo_base/static/src/icons/expenses.svg',
    'Time Off': '/cyllo_base/static/src/icons/time-off.svg',
    'Recruitment': '/cyllo_base/static/src/icons/recruitment.svg',
    'Employees': '/cyllo_base/static/src/icons/employee.svg',
    'Data Recycle': '/cyllo_base/static/src/icons/data-recycling.svg',
    'Maintenance': '/cyllo_base/static/src/icons/maintenance.svg',
    'eLearning': '/cyllo_base/static/src/icons/eLearning.svg',
    'Events': '/cyllo_base/static/src/icons/events.svg',
    'Advanced Events    ': '/cyllo_base/static/src/icons/events.svg',
    'Events Organization': '/cyllo_base/static/src/icons/events.svg',
    'Online Event Ticketing': '/cyllo_base/static/src/icons/events.svg',
    'Discuss': '/cyllo_base/static/src/icons/discuss.svg',
    'Contacts': '/cyllo_base/static/src/icons/contact.svg',
    'Calendar': '/cyllo_base/static/src/icons/calendar.svg',
    'Fleet': '/cyllo_base/static/src/icons/fleet.svg',
    'Live Chat': '/cyllo_base/static/src/icons/live-chat.svg',
    'Surveys': '/cyllo_base/static/src/icons/survey.svg',
    'Repairs': '/cyllo_base/static/src/icons/repair.svg',
    'Task Logs': '/cyllo_base/static/src/icons/task-log.svg',
    'Attendances': '/cyllo_base/static/src/icons/attendance.svg',
    'SMS Marketing': '/cyllo_base/static/src/icons/sms-marketing.svg',
    'To-Do': '/cyllo_base/static/src/icons/todo.svg',
    'Skills Management': '/cyllo_base/static/src/icons/skill-management.svg',
    'Lunch': '/cyllo_base/static/src/icons/lunch.svg',
    'Online Jobs': '/cyllo_base/static/src/icons/online-jobs.svg',
    'Employee Contracts': '/cyllo_base/static/src/icons/employee-contract.svg',
}

def post_init_hook(env):
    change_icons(env)
    change_email_color(env)
    change_app_icons(env)
    change_user_name(env)

def change_icons(env):
    """post init hook"""
    menu_item = env['ir.ui.menu'].search([('parent_id', '=', False)])
    for menu in menu_item:
        icon = ICONS[menu.name] if menu.name in ICONS.keys() else False
        menu.web_icon = icon

def change_email_color(env):
    """function to change primary and button color of email template"""
    companies = env['res.company'].search([])
    for company in companies:
        company.write({
            'primary_color': '#FFFFFF',
            'secondary_color': '#9EA700',
            'email_primary_color': '#FFFFFF',
            'email_secondary_color': '#9EA700',
        })

def change_app_icons(env):
    """Change the application icons"""
    modules = env['ir.module.module'].search([])
    for module in modules:
        if module.shortdesc in icons.keys():
            module.write({'icon': icons[module.shortdesc]})

def change_user_name(env):
    """Change the user name"""
    current_directory = os.path.dirname(os.path.realpath(__file__))
    relative_path = os.path.join(current_directory, 'static/src/img/avatar.jpg')
    with open(relative_path, 'rb') as file:
        binary_data = file.read()
    base64_encoded_image = base64.b64encode(binary_data)
    user = env['res.partner'].search([('active', '=', False), ('name', '=', 'OdooBot')])
    user.write({'name': 'CylloBot',
                'image_1920': base64_encoded_image
                })
