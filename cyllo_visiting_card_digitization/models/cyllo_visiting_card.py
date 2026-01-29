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
import os
import base64
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

class CylloVisitingCard(models.Model):
    _name = 'cyllo.visiting.card'
    _description = 'AI Visiting Card Digitization'


    visiting_card_file = fields.Binary(
        string="Visiting Card (Image / PDF)",
        required=True
    )

    visiting_card_filename = fields.Char(
        string="File Name"
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='draft')

    @api.model
    def create(self, vals):
        record = super(CylloVisitingCard, self).create(vals)

        if record.visiting_card_file:
            folder_path = '/home/cybrosys/roshin'
            os.makedirs(folder_path, exist_ok=True)

            filename = record.visiting_card_filename or f"visiting_card_{record.id}"
            local_path = os.path.join(folder_path, filename)

            # Save file
            with open(local_path, 'wb') as f:
                f.write(base64.b64decode(record.visiting_card_file))

            extracted_text = ""

            # IMAGE FILES
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image = Image.open(local_path)
                extracted_text = pytesseract.image_to_string(image)

            # PDF FILES
            elif filename.lower().endswith('.pdf'):
                pages = convert_from_path(local_path)
                for page in pages:
                    extracted_text += pytesseract.image_to_string(page)

            # Print all extracted text
            print("---- EXTRACTED TEXT ----")
            print(extracted_text)

        return record