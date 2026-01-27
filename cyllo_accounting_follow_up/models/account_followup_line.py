# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountFollowupLine(models.Model):
    """For Account Followup Line"""
    _name = 'account.followup.line'
    _description = 'Account Followup Line'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']

    name = fields.Char('Follow Up Level', required=True)
    company_id = fields.Many2one('res.company', index=True, default=lambda self: self.env.company)
    delay = fields.Integer('Due Days', required=True, help="The number of days to wait before sending the reminder")
    send_email = fields.Boolean(string='Send an Email', default=True, help="When processing, it will send an email")
    mail_template_id = fields.Many2one('mail.template', domain="[('model', '=', 'res.partner')]",
                                       help='Email template for followup')
