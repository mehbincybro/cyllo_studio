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
##############################################################################
import logging
import base64
import io
import re

import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from pdf2image import convert_from_bytes

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CylloVisitingCard(models.Model):
    _name = 'cyllo.visiting.card'
    _description = 'AI Visiting Card Digitization'

    visiting_card_file = fields.Binary(required=True, attachment=True)
    visiting_card_filename = fields.Char()
    extracted_text = fields.Text(readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='draft')

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _decode_binary(self, data):
        """
            Attempt to decode a Base64-encoded value.

            If the input is valid Base64, it returns the decoded binary data.
            If decoding fails for any reason, the original input is returned
            unchanged.

            Args:
                data: The input data to decode (typically bytes or a Base64 string).

            Returns:
                Decoded binary data if successful; otherwise, the original input.
            """
        try:
            return base64.b64decode(data)
        except Exception:
            return data

    def _parse_contact_text(self, text):
        """
            Parse free-form contact text into structured contact information.

            The function processes multiline text (e.g., OCR output from a business card)
            and attempts to extract common contact fields such as name, designation,
            company, phone numbers, email, website, and address. Lines are analyzed in
            order, with earlier lines given priority for name and role-related fields.

            Args:
                text (str): Raw multiline text containing contact details.

            Returns:
                dict: A dictionary with the following keys:
                    - name (str or None)
                    - designation (str or None)
                    - company (str or None)
                    - phones (list[str])
                    - email (str or None)
                    - website (str or None)
                    - address (str or None)

            Raises:
                ValidationError: If no non-empty text lines are detected.
            """
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            raise ValidationError("No text detected.")

        contact = {
            "name": None,
            "designation": None,
            "company": None,
            "phones": [],
            "email": None,
            "website": None,
            "address": None
        }

        phone_re = r'\+?\d[\d\-\s]+\d'
        email_re = r'\S+@\S+'
        web_re = r'(www\.\S+|\S+\.(com|net|org|io|co))'

        for idx, line in enumerate(lines):
            if idx == 0 and not contact["name"]:
                contact["name"] = line
            elif re.search(email_re, line):
                contact["email"] = line
            elif re.search(phone_re, line):
                contact["phones"] += re.findall(phone_re, line)
            elif re.search(web_re, line):
                contact["website"] = line
            elif not contact["designation"]:
                contact["designation"] = line
            elif not contact["company"]:
                contact["company"] = line
            else:
                contact["address"] = (
                    f"{contact['address']}, {line}"
                    if contact["address"] else line
                )

        return contact

    # ----------------------------------------------------------
    # OCR IMAGE
    # ----------------------------------------------------------
    def _ocr_image(self, file_bytes):
        """
            Perform OCR on an image and extract structured contact information.

            The method preprocesses the image by converting it to grayscale and
            applying autocontrast to improve OCR accuracy. Extracted text is then
            cleaned and passed to the contact text parser.

            Args:
                file_bytes (bytes): Raw image data to be processed via OCR.

            Returns:
                dict: Parsed contact information extracted from the image.
            """
        image = Image.open(io.BytesIO(file_bytes)).convert('RGB')
        image = ImageOps.autocontrast(ImageOps.grayscale(image))
        text = pytesseract.image_to_string(image).replace("\x0c", "").strip()
        return self._parse_contact_text(text)

    # ----------------------------------------------------------
    # OCR PDF
    # ----------------------------------------------------------
    def _ocr_pdf(self, file_bytes):
        """
           Perform OCR on a PDF file and extract structured contact information.

           Each page of the PDF is converted to an image, preprocessed using
           grayscale conversion and autocontrast, and then passed through OCR.
           Text from all pages is combined and parsed into contact fields.

           Args:
               file_bytes (bytes): Raw PDF data to be processed via OCR.

           Returns:
               dict: Parsed contact information extracted from the PDF.
           """
        pages = convert_from_bytes(file_bytes)
        full_text = ""

        for page in pages:
            page = ImageOps.autocontrast(ImageOps.grayscale(page))
            full_text += pytesseract.image_to_string(page)

        return self._parse_contact_text(full_text)

    # ----------------------------------------------------------
    # CREATE
    # ----------------------------------------------------------

    @api.model
    def create(self, vals):
        """
            Create a record and process an uploaded visiting card via OCR.

            After creating the record, this method attempts to extract contact
            information from the uploaded visiting card file (image or PDF).
            The file is decoded, processed with OCR, and parsed into structured
            contact data. Based on the extracted information, a partner and a
            related CRM opportunity are automatically created.

            Workflow:
                - Create the record using the parent `create`
                - Decode the uploaded file
                - Attempt image OCR, fallback to PDF OCR if needed
                - Store extracted data and update processing state
                - Create a partner and a CRM lead from extracted contact details

            Args:
                vals (dict): Values used to create the record.

            Returns:
                recordset: The newly created record.

            Raises:
                ValidationError: If no text can be extracted from the visiting card.
            """
        record = super().create(vals)
        if not record.visiting_card_file:
            return record

        record.state = 'processing'

        try:
            file_bytes = self._decode_binary(record.visiting_card_file)

            try:
                contact = self._ocr_image(file_bytes)
            except (UnidentifiedImageError, ValidationError):
                _logger.info("Image OCR failed, trying PDF OCR")
                contact = self._ocr_pdf(file_bytes)

            record.write({
                'extracted_text': str(contact),
                'state': 'done'
            })

        except Exception:
            record.state = 'failed'
            raise ValidationError("No text detected in visiting card.")

        # --------------------------------------------------
        # Create Partner & Opportunity
        # --------------------------------------------------
        # phone = contact.get('phones')
        #
        # partner = self.env['res.partner'].sudo().create({
        #     'name': contact.get('name'),
        #     'phone': phone[0] if phone else False,
        #     'email': contact.get('email'),
        #     'website': contact.get('website'),
        #     'contact_address': contact.get('address'),
        # })
        # self.env['crm.lead'].sudo().create({
        #     'name': f"{partner.name}'s Opportunity",
        #     'partner_id': partner.id,
        # })
        return record



