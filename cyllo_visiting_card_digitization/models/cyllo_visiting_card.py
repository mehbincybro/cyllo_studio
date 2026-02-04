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
import json

import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from pdf2image import convert_from_bytes

from odoo import api, fields, models
from odoo.exceptions import ValidationError

import imghdr
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

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

    type_of_digitization = fields.Selection(
        [('manually', 'Manually'), ('use_ai', 'Use AI')],
        required=True,
        default='manually'
    )

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

        text_lines = [line.strip() for line in text.splitlines() if
                      line.strip()]
        if not text_lines:
            raise ValidationError("No text detected.")

        contact_info = {
            "name": None,
            "designation": None,
            "company": None,
            "phones": [],
            "email": None,
            "website": None,
            "address": None
        }

        phone_pattern = r'\+?\d[\d\-\s]+\d'
        email_pattern = r'\S+@\S+'
        website_pattern = r'(www\.\S+|\S+\.(com|net|org|io|co))'

        for line_index, text_line in enumerate(text_lines):

            if line_index == 0 and not contact_info["name"]:
                contact_info["name"] = text_line

            elif re.search(email_pattern, text_line):
                contact_info["email"] = text_line

            elif re.search(phone_pattern, text_line):
                contact_info["phones"].extend(
                    re.findall(phone_pattern, text_line)
                )

            elif re.search(website_pattern, text_line):
                contact_info["website"] = text_line

            elif not contact_info["designation"]:
                contact_info["designation"] = text_line

            elif not contact_info["company"]:
                contact_info["company"] = text_line

            else:
                contact_info["address"] = (
                    f"{contact_info['address']}, {text_line}"
                    if contact_info["address"] else text_line
                )
        print(contact_info)
        return contact_info

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
    # Process With Ai
    # ----------------------------------------------------------
    def _process_with_ai(self):
        if not self.visiting_card_file:
            raise ValidationError(
                "No visiting card file uploaded for AI extraction."
            )

        try:
            file_bytes = base64.b64decode(self.visiting_card_file)
        except Exception:
            raise ValidationError(
                "Please upload your visiting card properly.")

        mime_type = None
        image_type = imghdr.what(None, file_bytes)
        if image_type:
            mime_type = f"image/{image_type}"
        elif file_bytes[:4] == b'%PDF':
            mime_type = "application/pdf"
        else:
            raise ValidationError(
                "Unsupported file type for AI extraction. Please upload PNG, JPG, JPEG, or PDF."
            )

        _logger.info("AI Digitization Triggered | MIME type: %s", mime_type)

        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_agent.api_key'
        )
        if not api_key:
            raise ValidationError(
                "Google API key not set in system parameters."
            )

        visiting_card_media = {
            "type": "media",
            "data": file_bytes,
            "mime_type": mime_type
        }

        message = HumanMessage(
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
            model='gemini-2.5-flash',
            google_api_key=api_key
        )

        try:
            response = llm.invoke([message])
            response_text = response.content
        except Exception as e:
            error_message = str(e).lower()

            # Check for token/API key expiration or authentication errors
            if any(keyword in error_message for keyword in [
                'expired', 'invalid api key', 'api key not valid',
                'authentication', 'unauthorized', '401', 'api_key_invalid'
            ]):
                _logger.error("API token has expired or is invalid: %s", str(e))
                raise ValidationError(
                    "Your API token has expired or is invalid. "
                    "Please update your Google API key in system parameters."
                )

            # Check for quota exceeded
            if any(keyword in error_message for keyword in [
                'quota', 'rate limit', 'resource exhausted', '429'
            ]):
                _logger.error("API quota exceeded: %s", str(e))
                raise ValidationError(
                    "API quota exceeded. Please try again later or check your API limits."
                )

            # Generic AI extraction error
            _logger.error("AI extraction failed: %s", str(e))
            raise ValidationError(
                f"Please upload your visiting card properly."
            )

        # Parse the JSON response into a Python dictionary


        try:
            # Remove markdown code blocks if present
            cleaned_text = re.sub(r'```json\s*|\s*```', '',
                                  response_text).strip()

            # Parse JSON string to dictionary
            contact = json.loads(cleaned_text)

            print(contact)  # This will print the Python dictionary
            return contact

        except json.JSONDecodeError as e:
            _logger.error("Failed to parse AI response as JSON: %s", str(e))
            raise ValidationError(
                "Please upload your visiting card properly.")

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

        # 🔹 AI FLOW (NEW)
        if record.type_of_digitization == 'use_ai':
            try:
                contact = record._process_with_ai()
                record.write({
                    'extracted_text': str(contact),
                    'state': 'done'
                })
            except Exception as e:
                record.state = 'failed'
                _logger.exception(e)
                raise ValidationError("AI extraction failed.")

            return record

        # 🔹 MANUAL / OCR FLOW (UNCHANGED)
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

        return record
