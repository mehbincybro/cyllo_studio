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
from odoo import fields, models


class CrmLeadNotification(models.Model):
    """ This model represents crm.lead.notification. for crm dashboard"""
    _name = 'crm.lead.notification'
    _description = 'CrmLeadNotification'
    _order = 'create_date desc'

    title = fields.Char('Title', required=True)
    message = fields.Text('Message', required=True)
    notification_type = fields.Selection([
        ('new_lead', 'New Lead'),
        ('lead_updated', 'Lead Updated'),
        ('stage_changed', 'Stage Changed'),
        ('activity_due', 'Activity Due'),
        ('won', 'Deal Won'),
        ('lost', 'Deal Lost'),
        ('email', 'Email'),
        ('call', 'Call'),
        ('meeting', 'Meeting'),
    ], string='Type', default='new_lead')
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
    ], string='Priority', default='normal')
    is_read = fields.Boolean('Is Read', default=False)
    lead_id = fields.Many2one('crm.lead', string='Related Lead')
    user_id = fields.Many2one('res.users', string='User',
                              default=lambda self: self.env.user)
    is_marked_notification = fields.Boolean(
        string='Marked Notification',
        default=False,
        help="This field is used to indicate if"
             " the notification for this lead has"
             " been marked as read by the user."
    )
    unread_visible = fields.Boolean(
        string='Unread Visible',
        compute='_compute_unread_visible',
        store=False,
    )
