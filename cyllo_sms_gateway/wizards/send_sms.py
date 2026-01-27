# -*- coding: utf-8 -*-
""" This module helps to add the sms details in the wizard and send SMS. """
from __future__ import print_function
import clicksend_client
import json
import requests
from clicksend_client import SmsMessage
from twilio.rest import Client
from ast import literal_eval
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SendSms(models.TransientModel):
    """
    Class for the wizard to send SMS.
    Methods:
        action_send_sms():
            Button action to send SMS.
    """
    _name = 'send.sms'
    _description = 'Wizard to send SMS'
    _check_company_auto = True

    sms_id = fields.Many2one('sms.gateway.config', string='Provider', domain="[('is_active','=',True)]",
                             required=True, help='Gateway record with credentials')
    sms_to = fields.Char(string='Phone Number', help='Enter the number to send the SMS')
    text = fields.Text(required=True, help='Enter the text for the SMS')
    partner_ids = fields.Many2many('res.partner', string="Customer", help="Select customer.")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, help='Active company.')

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        """
            Function to add recipient data for sms_to field
        """
        partners = []
        for partner_id in self.partner_ids:
            phone_number = partner_id.mobile or partner_id.phone
            partners.append(
                phone_number or f"No phone number for {partner_id.name}")
        self.sms_to = ', '.join(partners)

    def action_send_sms(self):
        """
        Function to send SMS using different SMS gateway
        """
        if self.sms_id.name == 'TWILIO':
            for number in self.sms_to.split(','):
                if number:
                    try:
                        client = Client(self.sms_id.twilio_account_sid, self.sms_id.twilio_auth_token)
                        response = client.messages.create(body=self.text, from_=self.sms_id.twilio_phone_number,
                                                          to=number)
                        self.sudo().create_sms_history(response.status)
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {'title': _('Success'),
                                       'type': 'success',
                                       'message': _(
                                           'Message has successfully sent.'),
                                       'next': {
                                           'type': 'ir.actions.act_window_close'},
                                       }}
                    except Exception as e:
                        self.create_sms_history(e)
                        return {'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {'title': _('Error'),
                                           'type': 'warning',
                                           'message': e,
                                           'next': {
                                               'type': 'ir.actions.act_window_close'}}}
        elif self.sms_id.name == 'D7':
            for number in self.sms_to.split(','):
                if number:
                    payload = json.dumps({
                        "messages": [{"channel": "sms", "recipients": [number],
                                      "content": self.text, "msg_type": "text",
                                      "data_coding": "text"}],
                        "message_globals": {
                            "originator": "SignOTP",
                            "report_url": "https://the_url_to_recieve_delivery_report.com"}})
                    headers = {'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'Authorization': 'Bearer ' + self.sms_id.d7_api}
                    try:
                        response = requests.request("POST", "https://api.d7networks.com/messages/v1/send",
                                                    headers=headers, data=payload)
                        if response.status_code == 200:
                            code = "Success"
                            self.create_sms_history(code)
                            return {'type': 'ir.actions.client',
                                    'tag': 'display_notification',
                                    'params': {
                                        'title': _('Success'),
                                        'type': 'success',
                                        'message': _('Message has successfully sent.'),
                                        'next': {
                                            'type': 'ir.actions.act_window_close'}}}
                        else:
                            code = response.json()["detail"][0]['code'] if isinstance(response.json()["detail"], list)\
                                else response.json()["detail"]['code']
                            self.create_sms_history(code)
                            return {'type': 'ir.actions.client',
                                    'tag': 'display_notification',
                                    'params': {
                                        'title': _('Error'),
                                        'type': 'warning',
                                        'message': code,
                                        'next': {
                                            'type': 'ir.actions.act_window_close'}}}
                    except Exception as e:
                        raise ValidationError(_(e))
        elif self.sms_id.name == 'CLICK SEND':
            configuration = clicksend_client.Configuration()
            configuration.username = self.sms_id.click_send_email
            configuration.password = self.sms_id.click_send_api
            api_instance = clicksend_client.SMSApi(
                clicksend_client.ApiClient(configuration))
            for number in self.sms_to.split(','):
                if number:
                    sms_message = SmsMessage(source="php", body=self.text, to=number, schedule=1436874701)
                    sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])
            try:
                response = api_instance.sms_send_post(sms_messages)
                response = response.replace("\'", "\"")
                response = literal_eval(response)
                status = response['data']['messages'][0]['status']
                self.create_sms_history(status)
                return {'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'type': 'success',
                            'message': _(
                                'Successfully authenticated.'),
                            'next': {
                                'type': 'ir.actions.act_window_close'}, }}
            except Exception as e:
                self.create_sms_history(e.reason)
                return {'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Error'),
                            'type': 'warning',
                            'message': e.reason,
                            'next': {
                                'type': 'ir.actions.act_window_close'}, }}

    def create_sms_history(self, response):
        """Create an entry in the SMS history with details of the SMS
        """
        status = response
        self.env['sms.history'].sudo().create({
            'user_id': self.env.user.id,
            'sms_gateway_id': self.sms_id.id,
            'sms_mobile': self.sms_to,
            'sms_text': self.text,
            'sms_status': status})
