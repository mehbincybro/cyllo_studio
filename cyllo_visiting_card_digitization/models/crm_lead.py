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


class CrmLead(models.Model):
    _inherit = 'crm.lead'


    def action_upload_visiting_card(self):
        """
        Opens a wizard to upload a visiting (business) card for the CRM lead.

        This method is intended to be called from a button in the CRM lead form view.
        When triggered, it opens a new form view of the 'visiting.card.upload.wizard' model
        in a modal window, allowing the user to upload a business card associated with this lead.

        Returns:
            dict: An Odoo action dictionary to open the visiting card upload wizard in a modal.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upload Business Card',
            'res_model': 'visiting.card.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
