# -*- coding: utf-8 -*-
"""To create access token"""
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from odoo import http
from odoo.http import request


class TwilioAccessToken(http.Controller):
    """Class for connecting odoo with twilio"""

    @http.route('/access/token', auth='public', type='json')
    def access_token(self, redirect=None, **kw):
        """To create the access token"""
        account_sid = request.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.account_sid")
        api_secret = request.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.api_secret")
        api_key = request.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.api_key")
        outgoing_application_sid = (request.env["ir.config_parameter"].sudo().
                                    get_param("cyllo_twilio_voice_call.outgoing_application_sid"))
        if account_sid and api_key and api_secret and outgoing_application_sid:
            token = AccessToken(account_sid, api_key, api_secret, identity='user_odoo_17')
            voice_grant = VoiceGrant(outgoing_application_sid=outgoing_application_sid, incoming_allow=True)
            token.add_grant(voice_grant)
            return token.to_jwt()
        else:
            return True
