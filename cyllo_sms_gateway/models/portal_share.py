# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PortalShare(models.TransientModel):
    """
       Extends the portal share functionality to send SMS notifications to
       partners.
    """
    _inherit = 'portal.share'

    sms_gateway_config_id = fields.Many2one('sms.gateway.config', domain="[('is_active','=',True)]",
                                            string="Provider", help="Select the sms gateway.")
    partner_phone = fields.Char(string="Phone number", help="Partners phone number")

    def action_send_sms(self):
        """
        Send SMS notifications to selected partners using the chosen SMS
        gateway provider.
        """
        if not self.sms_gateway_config_id:
            raise ValidationError("Select any gateway for sending sms")
        for partner_id in self.partner_ids:
            send_sms = self.env['send.sms'].create({
                'sms_id': self.sms_gateway_config_id.id,
                'sms_to': partner_id.phone,
                'text': self.share_link
            })
            send_sms.action_send_sms()

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        """
       Update the 'partner_phone' field based on the selected partners.
       Raises:
           ValidationError: If any selected partner does not have a phone
           number.
       """
        partners = []
        for partner_id in self.partner_ids:
            phone_number = partner_id.mobile or partner_id.phone
            if not phone_number:
                raise ValidationError(f'No Number for {partner_id.name}')
            partners.append(phone_number)
        self.partner_phone = ', '.join(partners)

