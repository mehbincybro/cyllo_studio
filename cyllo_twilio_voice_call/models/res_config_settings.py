# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Extends the `res.config.settings` model to add the credential's
    for the twilio configuration."""
    _inherit = 'res.config.settings'

    account_sid = fields.Char(help="To add the account sidfor the twilio account",
                              config_parameter='cyllo_twilio_voice_call.account_sid')
    api_key = fields.Char(help="To add the api key for the twilio account",
                          config_parameter='cyllo_twilio_voice_call.api_key')
    api_secret = fields.Char(help="To add the api secret for the twilio account",
                             config_parameter='cyllo_twilio_voice_call.api_secret')
    outgoing_application_sid = fields.Char(help="To add the outgoing application sid for the twilio account",
                                           config_parameter='cyllo_twilio_voice_call.outgoing_application_sid')
    auth_token = fields.Char(help="To add the auth token for the twilio account",
                             config_parameter='cyllo_twilio_voice_call.auth_token')
    from_number = fields.Char(string="Phone Number", help="To add the twilio phone number to call",
                              config_parameter='cyllo_twilio_voice_call.from_number')
