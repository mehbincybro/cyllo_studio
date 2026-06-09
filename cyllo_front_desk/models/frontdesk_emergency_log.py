# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FrontdeskEmergencyLog(models.Model):
    _name = 'frontdesk.emergency.log'
    _inherit = ['mail.thread']
    _description = 'Frontdesk Emergency Alert Log'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default='/', copy=False)
    station_id = fields.Many2one('frontdesk.frontdesk', string='Station', required=True, readonly=True)
    alert_id = fields.Many2one('frontdesk.emergency.alert', string='Alert Type', required=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Triggered By', required=True, readonly=True, default=lambda self: self.env.user)
    date = fields.Datetime(string='Triggered At', required=True, readonly=True, default=fields.Datetime.now)
    message = fields.Text(string='Message', required=True, readonly=True)
    recipient_summary = fields.Text(string='Notified Recipients', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('frontdesk.emergency.log') or '/'
        return super().create(vals_list)
