# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    """Extends the 'res.partner' model to add fields related to WhatsApp numbers."""
    _inherit = 'res.partner'

    phone_country_code_id = fields.Many2one('country.code', string="Country Code",
                                            help="Enter the whatsapp phone number country code")
    phone_number = fields.Char(help="Enter the whatsapp phone number")
    whatsapp_number = fields.Char(help="Whatsapp phone number", compute="_compute_whatsapp_number", store=True)

    @api.depends('phone_country_code_id', 'phone_number')
    def _compute_whatsapp_number(self):
        """Compute the WhatsApp number based on the country code and phone number."""
        for record in self:
            if record.phone_country_code_id and record.phone_number:
                country_code = record.phone_country_code_id.code
                contacts = self.sudo().search([('whatsapp_number', '=', f"{country_code}{record.phone_number}"),
                                               ('id', '!=', self.id)])
                if contacts:
                    record.phone_number = False
                    raise UserError(_('Whatsapp number already exist!. Change whatsapp number'))
                record.whatsapp_number = f"{country_code}{record.phone_number}"

