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
# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import UserError
import ast
import logging

_logger = logging.getLogger(__name__)


class VisitingCardUploadWizard(models.TransientModel):
    """
    Wizard to upload one or more visiting cards and automatically create
    corresponding partners in Odoo.

    Workflow:
        1. User uploads one or more visiting card files (images or PDFs).
        2. Each card is processed using either OCR or AI extraction.
        3. Structured contact data is extracted from each card.
        4. A partner is created for each successfully processed card.
        5. If a card fails extraction, it is skipped and a warning is shown.
        6. The wizard returns either:
           - Form view if only one partner is created.
           - List view if multiple partners are created.
    """

    _name = 'visiting.card.upload.wizard'
    _description = 'Upload Visiting Cards Wizard'

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string="Business Cards",
        help="Upload one or more business card images or PDFs"
    )

    type_of_digitization = fields.Selection(
        [('manually', 'Manually'), ('use_ai', 'Use AI')],
        required=True,
        string="Digitization Type",
        help="Choose whether to process the visiting cards manually (OCR) or via AI."
    )

    # ----------------------------------------------------------
    # Helper Methods
    # ----------------------------------------------------------

    def _safe_string(self, value):
        """
        Ensure the given value is a single string, not a list or None.

        Args:
            value: Any value, possibly a list.

        Returns:
            str or False: First element if list, or string itself. Returns False if empty.
        """
        if isinstance(value, list):
            return value[0] if value else False
        return value or False

    def _get_primary_phone(self, phone_list):
        """
        Extract the primary phone number from a list of phone numbers.

        Args:
            phone_list (list or str): List of phone numbers or a single string.

        Returns:
            str or False: First phone number in the list, or the string itself.
        """
        if isinstance(phone_list, list) and phone_list:
            return phone_list[0]
        elif isinstance(phone_list, str):
            return phone_list
        return False

    # ----------------------------------------------------------
    # Main Action
    # ----------------------------------------------------------

    def action_upload(self):
        """
        Process the uploaded visiting cards, create partners, and return
        the appropriate view (form or tree) based on the number of partners created.

        Returns:
            dict: Odoo action dictionary to open form or tree view of created partners.

        Raises:
            UserError: If no attachments are uploaded, or if no card could be processed.
        """
        self.ensure_one()

        if not self.attachment_ids:
            raise UserError("Please upload at least one business card.")

        if self.type_of_digitization == 'use_ai':
            api_key = self.env['ir.config_parameter'].sudo().get_param(
                'cyllo_agent.api_key'
            )
            if not api_key:
                raise UserError("Google API key is not configured in system parameters.")

        created_partners = self.env['res.partner']
        failed_cards = []

        # ------------------------------------------------------
        # Process each uploaded card individually
        # ------------------------------------------------------
        for attachment in self.attachment_ids:
            visiting_card = self.env['cyllo.visiting.card'].create({
                'visiting_card_file': attachment.datas,
                'visiting_card_filename': attachment.name,
                'type_of_digitization': self.type_of_digitization,
            })

            if visiting_card.state != 'done' or not visiting_card.extracted_text:
                failed_cards.append(attachment.name)
                continue

            try:
                # Convert extracted text string to Python dictionary
                extracted_data = ast.literal_eval(visiting_card.extracted_text)
            except Exception:
                _logger.exception("Failed to parse extracted text for attachment: %s", attachment.name)
                failed_cards.append(attachment.name)
                continue

            try:
                partner = self.env['res.partner'].create({
                    'name': self._safe_string(extracted_data.get('name')),
                    'phone': self._get_primary_phone(extracted_data.get('phones')),
                    'email': self._safe_string(extracted_data.get('email')),
                    'website': self._safe_string(extracted_data.get('website')),
                    'contact_address': self._safe_string(extracted_data.get('address')),
                    'is_from_visiting_card': True,
                })
                created_partners |= partner

            except Exception:
                _logger.exception("Partner creation failed for attachment: %s", attachment.name)
                failed_cards.append(attachment.name)

        if not created_partners:
            raise UserError("No visiting cards could be processed successfully.")

        # ------------------------------------------------------
        # Determine which view to return
        # ------------------------------------------------------
        if len(created_partners) == 1:
            # Open the partner form view if only one partner is created
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Contact',
                'res_model': 'res.partner',
                'res_id': created_partners.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Open tree view if multiple partners are created
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Contacts',
                'res_model': 'res.partner',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_partners.ids)],
            }

        # ------------------------------------------------------
        # Add warning for any failed cards
        # ------------------------------------------------------
        if failed_cards:
            action['warning'] = {
                'title': 'Some cards were skipped',
                'message': (
                    "The following visiting cards could not be processed:\n\n"
                    + "\n".join(failed_cards)
                )
            }

        return action

