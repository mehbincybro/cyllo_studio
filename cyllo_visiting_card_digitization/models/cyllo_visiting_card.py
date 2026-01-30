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
# #############################################################################
import logging

from odoo import api, fields, models
import base64
import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
import io
from pdf2image import convert_from_bytes
from odoo.exceptions import ValidationError
import re
import ast

_logger = logging.getLogger(__name__)


class CylloVisitingCard(models.Model):
    _name = 'cyllo.visiting.card'
    _description = 'AI Visiting Card Digitization'

    visiting_card_file = fields.Binary(
        string="Visiting Card (Image / PDF)",
        required=True,
        attachment=True
    )
    visiting_card_filename = fields.Char(string="File Name")
    extracted_text = fields.Text(string="Extracted Text", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='draft')

    # ----------------------------------------------------------
    # Convert binary field to bytes (safe for any file)
    # ----------------------------------------------------------
    def _decode_binary(self, binary_data):
        try:
            return base64.b64decode(binary_data)
        except Exception:
            return binary_data

    # ----------------------------------------------------------
    # Try OCR as IMAGE
    # ----------------------------------------------------------
    def _ocr_image(self, file_bytes, filename):
        """Trying OCR as IMAGE..."""
        image = Image.open(io.BytesIO(file_bytes))
        # Image opened: format={image.format}, size={image.size}, mode={image.mode}

        # Fix image mode
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')

        # Preprocess for OCR
        image = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(image)

        text = pytesseract.image_to_string(image)
        text = text.replace("\x0c", "").strip()
        contact_list = [line.strip() for line in text.splitlines() if
                        line.strip()]
        if not contact_list:
            raise ValidationError('No text detected.')
        # Initialize structured dictionary
        contact_info = {
            "name": None,
            "designation": None,
            "company": None,
            "phones": [],
            "email": None,
            "website": None,
            "address": None
        }

        # Regular expressions
        phone_pattern = r'\+?\d[\d\-\s]+\d'
        email_pattern = r'\S+@\S+'
        website_pattern = r'(www\.\S+|\S+\.(com|net|org|io|co))'

        # Simple heuristics to fill dictionary
        for i, line in enumerate(contact_list):
            if i == 0:
                contact_info["name"] = line
            elif re.search(email_pattern, line):
                contact_info["email"] = line
            elif re.search(phone_pattern, line):
                phones = re.findall(phone_pattern, line)
                contact_info["phones"].extend(phones)
            elif re.search(website_pattern, line):
                contact_info["website"] = line
            elif not contact_info["designation"]:
                # assume 2nd line is designation
                contact_info["designation"] = line
            else:
                # remaining lines are part of the address or company
                if not contact_info["company"]:
                    contact_info["company"] = line
                else:
                    if contact_info["address"]:
                        contact_info["address"] += ", " + line
                    else:
                        contact_info["address"] = line
        return contact_info


    # ----------------------------------------------------------
    # Try OCR as PDF
    # ----------------------------------------------------------
    def _ocr_pdf(self, file_bytes, filename):
        """Trying OCR as PDF..."""

        pages = convert_from_bytes(file_bytes)
        texts = []

        for i, page in enumerate(pages, start=1):
            # OCR on PDF page {i}
            page = ImageOps.grayscale(page)
            page = ImageOps.autocontrast(page)
            page_text = pytesseract.image_to_string(page).replace("\x0c",
                                                                  "").strip()
            if page_text:
                texts.append(f"--- Page {i} ---\n{page_text}")
            contact_list = [line.strip() for line in page_text.splitlines() if
                            line.strip()]
            if not contact_list :
                raise ValidationError('No text detected.')
            contact_info = {
                "name": None,
                "designation": None,
                "company": None,
                "phones": [],
                "email": None,
                "website": None,
                "address": None
            }

            # Regular expressions
            phone_pattern = r'\+?\d[\d\-\s]+\d'
            email_pattern = r'\S+@\S+'
            website_pattern = r'(www\.\S+|\S+\.(com|net|org|io|co))'

            # Simple heuristics to fill dictionary
            for i, line in enumerate(contact_list):
                if i == 0:
                    contact_info["name"] = line
                elif re.search(email_pattern, line):
                    contact_info["email"] = line
                elif re.search(phone_pattern, line):
                    phones = re.findall(phone_pattern, line)
                    contact_info["phones"].extend(phones)
                elif re.search(website_pattern, line):
                    contact_info["website"] = line
                elif not contact_info["designation"]:
                    # assume 2nd line is designation
                    contact_info["designation"] = line
                else:
                    # remaining lines are part of the address or company
                    if not contact_info["company"]:
                        contact_info["company"] = line
                    else:
                        if contact_info["address"]:
                            contact_info["address"] += ", " + line
                        else:
                            contact_info["address"] = line
        return contact_info

    # ----------------------------------------------------------
    # CREATE
    # ----------------------------------------------------------

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not record.visiting_card_file:
            return record

        record.state = 'processing'

        try:
            file_bytes = self._decode_binary(record.visiting_card_file)

            # Try IMAGE first, fallback to PDF
            try:
                extracted_text = self._ocr_image(file_bytes,
                                                 record.visiting_card_filename)
            except (UnidentifiedImageError, ValidationError):
                _logger.warning("Not an image or OCR failed. Trying PDF.")
                extracted_text = self._ocr_pdf(file_bytes,
                                               record.visiting_card_filename)

            if not extracted_text:
                raise ValidationError("No text detected.")

            record.write({'extracted_text': extracted_text, 'state': 'done'})

        except Exception:
            raise ValidationError("No text detected.")

        # ----------------------
        # Partner & Opportunity
        # ----------------------
        contacts = ast.literal_eval(record.extracted_text)
        phone = contacts.get('phones')

        partner_vals = {
            'name': contacts.get('name') or False,
            'phone': phone[0] if phone else False,
            'email': contacts.get('email') or False,
            'website': contacts.get('website') or False,
            'contact_address': contacts.get('address') or False,
        }

        partner = self.env['res.partner'].sudo().create(partner_vals)

        self.env['crm.lead'].sudo().create({
            'name': f"{partner.name}'s Opportunity",
            'partner_id': partner.id,
        })

        return record