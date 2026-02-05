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
# -*- coding: utf-8 -*-

import logging
import base64
import io
import re
import json
import imghdr

import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from pdf2image import convert_from_bytes

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

_logger = logging.getLogger(__name__)


class CylloVisitingCard(models.Model):
    """
    Model for AI-based visiting card digitization.

    This model allows users to upload visiting cards (image or PDF) and
    automatically extracts contact information using either OCR or an AI model.

    Fields:
        visiting_card_file (Binary): Uploaded visiting card file (required).
        visiting_card_filename (Char): Name of the uploaded file.
        extracted_text (Text): Extracted contact data in JSON format (readonly).
        state (Selection): Current state of processing ('draft', 'processing', 'done', 'failed').
        type_of_digitization (Selection): Method of extraction ('manually' using OCR or 'use_ai').
    """
    _name = 'cyllo.visiting.card'
    _description = 'AI Visiting Card Digitization'

    visiting_card_file = fields.Binary(
        string="Visiting Card File",
        required=True,
        attachment=True
    )

    visiting_card_filename = fields.Char(string="Filename")

    extracted_text = fields.Text(
        string="Extracted Data",
        readonly=True
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('processing', 'Processing'),
            ('done', 'Done'),
            ('failed', 'Failed')
        ],
        default='draft'
    )

    type_of_digitization = fields.Selection(
        [('manually', 'Manually'), ('use_ai', 'Use AI')],
        default='manually',
        required=True
    )

    def _decode_binary(self, encoded_data):
        """
        Decode a base64-encoded binary string into bytes.

        Args:
            encoded_data (str or bytes): Base64-encoded data.

        Returns:
            bytes: Decoded binary data.
        """
        try:
            return base64.b64decode(encoded_data)
        except Exception:
            return encoded_data

    def _parse_contact_text(self, raw_text):
        """
        Parse raw text extracted from a visiting card into structured contact data.

        Args:
            raw_text (str): Text extracted from OCR or AI processing.

        Returns:
            dict: Parsed contact details including name, designation, company, phones, email, website, and address.

        Raises:
            ValidationError: If no text is detected in the raw input.
        """
        text_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not text_lines:
            raise ValidationError("No text detected.")

        parsed_contact = {
            'name': None,
            'designation': None,
            'company': None,
            'phones': [],
            'email': None,
            'website': None,
            'address': None
        }

        phone_pattern = r'\+?\d[\d\-\s]+\d'
        email_pattern = r'\S+@\S+'
        website_pattern = r'(www\.\S+|\S+\.(com|net|org|io|co))'

        for index, line in enumerate(text_lines):
            if index == 0:
                parsed_contact['name'] = line
            elif re.search(email_pattern, line):
                parsed_contact['email'] = line
            elif re.search(phone_pattern, line):
                parsed_contact['phones'].extend(re.findall(phone_pattern, line))
            elif re.search(website_pattern, line):
                parsed_contact['website'] = line
            elif not parsed_contact['designation']:
                parsed_contact['designation'] = line
            elif not parsed_contact['company']:
                parsed_contact['company'] = line
            else:
                parsed_contact['address'] = (
                    f"{parsed_contact['address']}, {line}"
                    if parsed_contact['address'] else line
                )

        return parsed_contact

    def _perform_image_ocr(self, image_bytes):
        """
        Perform OCR on an image file and parse extracted text into contact data.

        Args:
            image_bytes (bytes): Binary content of an image.

        Returns:
            dict: Parsed contact information.
        """
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        image = ImageOps.autocontrast(ImageOps.grayscale(image))
        extracted_text = pytesseract.image_to_string(image)
        return self._parse_contact_text(extracted_text)

    def _perform_pdf_ocr(self, pdf_bytes):
        """
        Perform OCR on a PDF file and parse extracted text into contact data.

        Args:
            pdf_bytes (bytes): Binary content of a PDF file.

        Returns:
            dict: Parsed contact information.
        """
        pages = convert_from_bytes(pdf_bytes)
        full_text = ""

        for page in pages:
            page = ImageOps.autocontrast(ImageOps.grayscale(page))
            full_text += pytesseract.image_to_string(page)

        return self._parse_contact_text(full_text)

    def _process_with_ai(self):
        """
        Use an AI model to extract contact information from the visiting card file.

        Returns:
            dict: Extracted contact information from AI.

        Raises:
            ValidationError: If the file type is unsupported.
        """
        file_bytes = base64.b64decode(self.visiting_card_file)

        image_type = imghdr.what(None, file_bytes)
        if image_type:
            mime_type = f"image/{image_type}"
        elif file_bytes[:4] == b'%PDF':
            mime_type = "application/pdf"
        else:
            raise ValidationError("Unsupported file type.")

        api_key = self.env['ir.config_parameter'].sudo().get_param('cyllo_agent.api_key')
        model_id = int(self.env['ir.config_parameter'].sudo().get_param('agent.llm_model_id'))
        model_name = self.env['cyllo.llm'].sudo().browse(model_id).name

        visiting_card_media = {
            "type": "media",
            "data": file_bytes,
            "mime_type": mime_type
        }

        prompt_message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        "Extract the contact information from this visiting card. "
                        "Return JSON with keys: name, designation, company, phones (list), "
                        "email, website, address."
                    )
                },
                visiting_card_media
            ]
        )

        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key
        )

        response = llm.invoke([prompt_message])
        cleaned_response = re.sub(r'```json\s*|\s*```', '', response.content).strip()
        return json.loads(cleaned_response)

    @api.model
    def create(self, values):
        """
        Override the default create method to automatically process the visiting card
        using OCR or AI after the record is created.

        Args:
            values (dict): Values to create the record.

        Returns:
            recordset: The newly created visiting card record with extracted data.
        """
        record = super().create(values)

        if not record.visiting_card_file:
            return record

        record.state = 'processing'

        try:
            if record.type_of_digitization == 'use_ai':
                extracted_contact = record._process_with_ai()
            else:
                binary_data = self._decode_binary(record.visiting_card_file)
                try:
                    extracted_contact = record._perform_image_ocr(binary_data)
                except (UnidentifiedImageError, ValidationError):
                    extracted_contact = record._perform_pdf_ocr(binary_data)

            record.write({
                'extracted_text': str(extracted_contact),
                'state': 'done'
            })

        except Exception:
            _logger.exception("Visiting card processing failed (ID: %s)", record.id)
            record.write({
                'state': 'failed',
                'extracted_text': False
            })

        return record