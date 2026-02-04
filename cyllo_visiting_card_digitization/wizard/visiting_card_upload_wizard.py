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
from odoo import models, fields, api
import ast

from odoo.exceptions import UserError


class VisitingCardUploadWizard(models.TransientModel):
    _name = 'visiting.card.upload.wizard'
    _description = 'Upload Visiting Card Wizard'

    visiting_card_file = fields.Binary(
        string="Upload Card",
        required=True
    )

    visiting_card_filename = fields.Char(
        string="File Name"
    )
    type_of_digitization = fields.Selection([('manually', 'Manually'), ('use_ai', 'Use Ai')], required=True)

    def action_upload(self):
        """Upload Visiting Card File"""
        self.ensure_one()
        if self.type_of_digitization == 'use_ai':
            TEST_GOOGLE_API_KEY = self.env[
                'ir.config_parameter'].sudo().get_param(
                'cyllo_agent.api_key')
            if not TEST_GOOGLE_API_KEY:
                raise UserError('API KEY not set')

        record = self.env['cyllo.visiting.card'].create({
            'visiting_card_file': self.visiting_card_file,
            'visiting_card_filename': self.visiting_card_filename,
            'type_of_digitization': self.type_of_digitization,

        })
        data = ast.literal_eval(record.extracted_text)
        phone = data.get('phones')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Visiting Card',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': data.get('name'),
                'default_phone': phone[0] if phone else False,
                'default_email': data.get('email'),
                'default_website': data.get('website'),
                'default_contact_address': data.get('address'),
                'default_is_from_visiting_card': True,
            }
        }


