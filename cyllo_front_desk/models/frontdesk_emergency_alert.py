# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FrontdeskEmergencyAlert(models.Model):
    _name = 'frontdesk.emergency.alert'
    _inherit = ['mail.thread']
    _description = 'Frontdesk Emergency Alert Configuration'
    _order = 'name'

    name = fields.Char(string='Alert Name', required=True, tracking=True)
    station_ids = fields.Many2many(
        'frontdesk.frontdesk', 
        'frontdesk_alert_station_rel', 
        'alert_id', 
        'station_id', 
        string='Stations', 
        required=True,
        help="Stations where this alert can be triggered."
    )
    recipient_employee_ids = fields.Many2many(
        'hr.employee', 
        'frontdesk_alert_employee_rel', 
        'alert_id', 
        'employee_id', 
        string='Notify Specific Employees',
        help="Specific employees who will receive notifications."
    )
    recipient_user_ids = fields.Many2many(
        'res.users', 
        'frontdesk_alert_user_rel', 
        'alert_id', 
        'user_id', 
        string='Notify Specific Users',
        help="Specific users who will receive notifications."
    )
    recipient_channel_ids = fields.Many2many(
        'discuss.channel', 
        'frontdesk_alert_channel_rel', 
        'alert_id', 
        'channel_id', 
        string='Notify Discuss Channels',
        help="Discuss channels (chat rooms) where the emergency message "
             "will be posted publicly. Unlike groups/users which send "
             "private inbox notifications, channel posts are visible "
             "to every channel member in real time — ideal for "
             "situation rooms, security ops channels, or building-wide "
             "announcement channels."
    )
    default_message = fields.Text(
        string='Default Message', 
        default='EMERGENCY ALERT TRIGGERED! Please respond immediately.',
        required=True,
        help="Default message populated when triggering this alert."
    )
    active = fields.Boolean(string='Active', default=True)
