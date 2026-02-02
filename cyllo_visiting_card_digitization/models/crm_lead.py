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
from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'


    def action_upload_visiting_card(self):
        """Action button for visiting card: When it clicks user can upload visiting card"""
        # TEST_GOOGLE_API_KEY = self.env[
        #     'ir.config_parameter'].sudo().get_param(
        #     'cyllo_agent.api_key')
        # if not TEST_GOOGLE_API_KEY:
        #     raise UserError('API KEY not set')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Upload Visiting Card',
            'res_model': 'visiting.card.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    # def _on_visiting_card_uploaded(self, visiting_card):
    #     visiting_card = self.env['cyllo.visiting.card'].browse(visiting_card.id)
    #     print('Hiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii')
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Confirm Your Partner',
    #         'res_model': 'res.partner',
    #         'view_mode': 'form',
    #         'target': 'new',
    #     }
        # print(visiting_card.extracted_text)

    # @api.depends('visiting_card_id.id')
    # def _compute_visiting_card(self):
    #     """Compute visiting card id"""
    #     print('Heyyyyy')
