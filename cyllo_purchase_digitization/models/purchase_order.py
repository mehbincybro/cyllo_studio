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
import json
import logging
import os
import re
import tempfile

# imports of odoo
from odoo import _, api, fields, models, release
from odoo.addons.iap.tools import iap_tools

# Import of unknown third party lib
_logger = logging.getLogger(__name__)

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'

try:
    import camelot
    import fitz
    import numpy as np
    import pandas as pd
except ImportError as e:
    package_name = str(e).split(' ')[-1]
    _logger.debug('Cannot import the required external dependency: %s',
                  package_name)


class PurchaseOrder(models.Model):
    """
        Extends the 'purchase.order' model to include fields and methods for
        OCR digitization of PDF documents.
        """
    _inherit = 'purchase.order'

    ocr_digitize_enabled = fields.Boolean(
        string="OCR Enabled",
        compute='_compute_ocr_digitize_enabled')
    message_main_attachment_id = fields.Many2one(
        string="Main Attachment",
        comodel_name='ir.attachment',
        copy=False)
    ocr_digitize_completed = fields.Boolean(string="OCR success status")
    ocr_digitize_failed = fields.Boolean(string="OCR failed status")
    ocr_digitize_message = fields.Char(
        string="OCR Status",
        readonly=True)

    @api.depends('message_main_attachment_id')
    def _compute_ocr_digitize_enabled(self):
        """
        Compute the OCR digitization status for each record.

        The OCR digitization status is determined based on the configuration
        parameters and the automation type specified in the associated
        purchase digitization settings.
        """
        for rec in self:
            # Check if OCR digitization is enabled in the system
            is_purchase_ocr_digitization = self.env[
                'ir.module.module'].sudo().search(
                [('name', '=', 'cyllo_purchase_digitization'),
                 ('state', '=', 'installed')])
            if is_purchase_ocr_digitization:
                # Retrieve the relevant purchase digitization settings
                purchase_digitization = self.env[
                    'purchase.digitization'].search(
                    [('active_configuration', '=', True)])
                # Determine OCR digitization status based on automation type
                if purchase_digitization.automation_type == 'request_digitize':
                    rec.write({'ocr_digitize_enabled': True})
                else:
                    rec.write({'ocr_digitize_enabled': False})
                # Trigger automatic digitization if configured for auto_digitize
                if (purchase_digitization.automation_type == 'auto_digitize'
                        and rec.ocr_digitize_completed != True) :
                    if rec.state == 'draft' and rec.message_main_attachment_id:
                        rec.action_send_digitization()
            else:
                rec.write({'ocr_digitize_enabled': False})

    def action_send_digitization(self):
        """
         Perform OCR digitization on a PDF document attached to the record.
         This method reads the attached PDF document, extracts text content, and
         processes it to digitize relevant information, such as partner name,
         purchase fields, and purchase order line details.
         :raises: Exception if an error occurs during digitization.
         """
        # Getting the file path from ir.attachments
        file_attachment = self.message_main_attachment_id
        # Check if the file is a PDF
        if file_attachment:
            split_tup = os.path.splitext(file_attachment.name)
            file_path = file_attachment._full_path(file_attachment.store_fname)
            pdf_extension = {'.pdf'}
            if split_tup[1] in pdf_extension:
                # Reading files in the format .pdf
                with open(file_path, mode='rb') as f:
                    pdf_data = f.read()
                text = " "
            else:
                # Notify if the document is not a PDF
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({
                    'ocr_digitize_message':
                        'Digitization now works only on PDF documents'})
                return
            try:
                # Extract text using OCR
                doc = fitz.open(file_path)  # open a document
                for page in doc:  # iterate the document pages
                    text += page.get_text(flags=8)
                text = '\n'.join(
                    [line.strip() for line in text.splitlines() if
                     line.strip()])
                purchase_digitization = self.env[
                    'purchase.digitization'].search(
                    [('active_configuration', '=', True)])
                if (purchase_digitization.automation_method ==
                        'manual_digitization'):
                    if pdf_data:
                        with tempfile.NamedTemporaryFile(
                                suffix='.pdf', delete=False) as temp_pdf_file:
                            temp_pdf_file.write(pdf_data)
                        # Read tables from PDF using camelot
                        tables = camelot.read_pdf(temp_pdf_file.name,
                                                  pages='all',
                                                  backend='poppler')
                        if not tables:
                            tables = camelot.read_pdf(temp_pdf_file.name,
                                                      flavor="stream",
                                                      pages='all')
                        # Check if there are multiple tables
                        if len(tables) > 1:
                            # Merge the tables into a single table
                            combined_table = pd.concat(
                                [table.df for table in tables],
                                ignore_index=True)
                        else:
                            # If there's only one table, you can directly use it
                            combined_table = tables[0].df
                        # Process structured table data
                        table_data = []
                        for table in tables:
                            table_rows = []
                            for row in table.df.itertuples(index=False):
                                row_data = [item.replace('\xa0', ' ').strip()
                                            for
                                            item in row if item.strip()]
                                table_rows.append(row_data)
                            table_data.append(table_rows)
                        # Perform further actions based on extracted data
                        self.find_partner(text)
                        self.action_find_field_values(text)
                        purchase_line_column_values = \
                            self.action_get_purchase_line_columns(
                                combined_table, text)
                        ocr_products = self.action_create_products(
                            combined_table, purchase_line_column_values)
                        self.get_order_line(table_data,
                                            purchase_line_column_values)
                        if self.ocr_digitize_failed:
                            for product in ocr_products:
                                product.id.unlink()
                else:
                    pdf_details = self.get_details_ai(text) if text else None
                    quotation_details = self.get_quotation_details(
                        pdf_details) if pdf_details else None
                    product_details = self.get_product_details(
                        pdf_details) if pdf_details else None
                    # Perform further actions based on extracted data
                    self.find_partner_ai(text, quotation_details)
                    self.action_find_field_values_ai(text, quotation_details)
                    self.action_find_product(product_details)
                # except Exception:
            except Exception as exc:
                # Handle exceptions during digitization
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                logging.error(f"Error while processing segment: {exc}")
                self.write({'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed")})
                if self.ocr_digitize_failed:
                    return {
                        'name': 'AI Digitization',
                        'type': 'ir.actions.act_window',
                        'res_model': 'digitization.ai.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {'default_active_id': self.id},
                    }
        else:
            # Notify if no attachments are found
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({
                'ocr_digitize_message': _(f"No Attachments To Digitize")})

    def find_partner(self, text):
        """
        Find a partner based on the extracted text using 'spacy'
        and configured keywords.
        :param text: Extracted text to search for partner information.
        """
        purchase_digitization = self.env['purchase.digitization'].search(
            [('active_configuration', '=', True)])
        # Get keywords related to the 'partner_id' field
        partner_field_keywords = \
            [keyword.name for field in
             purchase_digitization.purchase_field_details_ids
             for keyword in field.field_keyword_ids if
             field.purchase_field_id.name == 'partner_id']
        # Search for existing partners
        company_partner_id = self.env.company.partner_id
        users = self.env['res.users'].search([('share', '=', False)]).mapped(
            'partner_id')
        if company_partner_id:
            partner_ids = self.env['res.partner'].search(
                [('id', '!=', company_partner_id.id),
                 ('id', 'not in', users.ids)]) if users else self.env[
                'res.partner'].search(
                [('id', '!=', company_partner_id.id)])
        else:
            partner_ids = self.env['res.partner'].search(
                [('id', 'not in', users.ids)]) if users else self.env[
                'res.partner'].search([])
        keyword_match = [
            re.search(rf'({re.escape(keyword.lower())})', text.lower())
            for keyword in
            partner_field_keywords] if partner_field_keywords else []
        text_window = text[
            keyword_match[0].start():keyword_match[
                                         0].start() + 45] if any(
            keyword_match) else []
        found_partners = [partner for partner in partner_ids if
                          partner.name in text_window]
        self.write(
            {'partner_id': found_partners[0].id}) if found_partners else None
        # If no partner is found in the window, search in the entire text
        found_partners_text = [partner for partner in partner_ids if
                               partner.name in text] if not found_partners \
            else []
        self.write(
            {'partner_id': found_partners_text[
                0].id}) if found_partners_text else None
        if not found_partners_text:
            partner_details = self.get_partner_details_ai(text)
            if partner_details:
                partner_name = partner_details.get('partner_name')
                street = partner_details.get('street')
                city = partner_details.get('city')
                state_name = partner_details.get('state')
                state = self.env['res.country.state'].search(
                    [('name', '=', state_name)])
                new_found_partner = self.env['res.partner'].create({
                    'name': partner_name
                }) if partner_name else None
                if new_found_partner:
                    new_found_partner.write({
                        'street': street,
                        'city': city,
                    })
                if state:
                    new_found_partner.write({'state_id': state})
                self.write(
                    {'partner_id': new_found_partner.id}) if (
                    new_found_partner) else None

    def get_partner_details_ai(self, text):
        """
        Retrieve partner details from an AI service based on the provided text.
            Args:
                text (str): The text to be analyzed for partner details.
            Returns:
                dict: A dictionary containing partner details such as name,
                street, city, state, and country.If values are null,
                corresponding keys are assigned blank values.The response
                strictly follows the specified guidelines and does not contain
                any additional text.If extraction fails, returns an empty
                 dictionary.
            """
        try:
            company_name = self.env.company.name
            conversation_history = [
                {'role': 'user',
                 'content': f"Find partner details from this purchase "
                            f"quoatation like customer name and address of the"
                            f" customer. When extracting the customer name,"
                            f" consider the person billed to and do not"
                            f" include {company_name}.The dictionary keys"
                            f" should correspond to partner_name,street, city,"
                            f" state, country.If the values are null,"
                            f" assign a blank value to the corresponding key."
                            f"The response should only contain the dictionary "
                            f"without any additional text and do not add new"
                            f" line command and unwanted spaces."
                            f"(It must strictly follow these guidelines)"}]
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': text,
                    'conversation_history': conversation_history or [],
                    'version': release.version,
                }, timeout=30)
            if response['status'] == 'success':
                if isinstance(response['content'], str):
                    try:
                        partner_details = json.loads(response['content'])
                    except json.JSONDecodeError:
                        start_index = response['content'].find("{")
                        end_index = response['content'].find("}")
                        # Extract the substring containing the list
                        extracted_purchase_details = response['content'][
                            start_index:end_index + 1]
                        partner_details = json.loads(
                            extracted_purchase_details)
                    return partner_details
            elif response['status'] == 'error_prompt_too_long':
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Failed to Identify the Customer")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Failed to Identify the Customer.")})
        except Exception as exc:
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({'ocr_digitize_message': _(
                f"Failed to Identify the Customer.")})
            logging.error(f"AccessError details: {exc}")

    def action_find_field_values(self, text):
        """
        Find and update field values in the invoice based on the provided text.
        :param text: Text content to extract field values from.
        """
        # Retrieve invoice digitization settings
        purchase_digitization = self.env['purchase.digitization'].search(
            [('active_configuration', '=', True)])
        if purchase_digitization.purchase_field_details_ids:
            for field in purchase_digitization.purchase_field_details_ids:
                for keyword in field.field_keyword_ids:
                    keyword_pattern = rf'({re.escape(keyword.name.lower())})'
                    keyword_match = re.search(keyword_pattern, text.lower())
                    # find the text area of the provided keyword
                    if keyword_match:
                        # Get the start position of the match
                        keyword_start = keyword_match.start()
                        window_size = 47
                        text_window = text[
                            keyword_start:keyword_start + window_size]
                        if field.purchase_field_id.ttype == 'char':
                            char_text_window = text[
                                keyword_start:keyword_start + 40]
                            keyword_split = keyword.name.split()
                            if len(keyword_split) > 1:
                                keyword_pattern = \
                                    rf'({re.escape(keyword_split[-1].lower())})'
                                keyword_split_match \
                                    = re.search(keyword_pattern,
                                                char_text_window.lower())
                                keyword_split_start = \
                                    keyword_split_match.start()
                                char_text_window \
                                    = char_text_window[keyword_split_start:
                                                       keyword_split_start + 40]
                            # Split the text window into words
                            split_char_text_window = char_text_window.split()
                            if len(split_char_text_window) > 1:
                                # Extract the desired word after the keyword
                                extracted_word = split_char_text_window[1]
                                self.write({
                                    field.purchase_field_id.name: extracted_word
                                })
                        elif field.purchase_field_id.ttype == 'many2one':
                            model_name = field.purchase_field_id.relation
                            records = self.env[model_name].search([])
                            found_records = [rec for rec in records
                                             if rec.name.lower() in
                                             text_window.lower() or
                                             rec.name in text.lower()]
                            if found_records:
                                self.write({field.purchase_field_id.name
                                            : found_records[0].id})
                            if field.purchase_field_id.name == 'incoterm_id':
                                incoterm_records = [
                                    rec for rec in records if
                                    rec.code in text_window or rec.code in text]
                                if incoterm_records:
                                    self.write({field.purchase_field_id.name
                                                : incoterm_records[0].id})

    def action_get_purchase_line_columns(self, combined_table, text):
        """
        Extracts relevant details from a combined table based on configured
        keywords for purchase digitization.
        Note:
            This method relies on configured keywords and field mappings for
            extracting details such as quantity, tax, discount, and price unit
            from the given combined_table and associated text.

            The extracted values are returned in a dictionary format for further
            processing in the purchase digitization workflow.
        """
        purchase_digitization = self.env['purchase.digitization'].search(
            [('active_configuration', '=', True)])
        purchase_line_values = {}
        if not combined_table.empty:
            for col in combined_table.columns:
                if purchase_digitization.purchase_line_field_details_ids:
                    for field in purchase_digitization.purchase_line_field_details_ids:
                        for keyword in field.line_field_keyword_ids:
                            column_values = combined_table[col].tolist()
                            column_values = [str(item).replace('\n', ' ') for
                                             item
                                             in
                                             column_values]
                            column_values = [str(item).replace('\xa0', ' ') for
                                             item
                                             in
                                             column_values]
                            if any(keyword.name.lower() in str(val).lower() for
                                   val
                                   in column_values):
                                cleaned_column_values = [item for item in
                                                         column_values
                                                         if item.strip() != '']
                                for val in cleaned_column_values:
                                    if keyword.name.lower() in val.lower():
                                        keyword_index = \
                                            cleaned_column_values.index(val)
                                        values_after_keyword \
                                            = cleaned_column_values[
                                            keyword_index + 1:]
                                        if (field.purchase_line_field_id.name
                                                == 'product_qty'):
                                            column_values_copy = \
                                                values_after_keyword.copy()
                                            unit_of_measures = self.env[
                                                'uom.uom'].search([])
                                            currency_symbol = self.env[
                                                'res.currency'].search([])
                                            for unit in unit_of_measures:
                                                for currency in currency_symbol:
                                                    for value in \
                                                            column_values_copy:
                                                        split_value = str(
                                                            value).split()
                                                        for vals in split_value:
                                                            if unit.name.lower() == vals.lower():
                                                                split_value.remove(
                                                                    vals)
                                                                values_after_keyword.remove(
                                                                    value)
                                                                values_after_keyword.append(
                                                                    split_value[
                                                                        0])
                                                            if (currency.symbol
                                                                    == vals):
                                                                values_after_keyword.remove(
                                                                    value)
                                            extracted_numbers = []
                                            for item in values_after_keyword:
                                                # Use regular expression
                                                # to find numeric values
                                                numeric_values = re.findall(
                                                    r'\b\d+\.*\d*\b(?!\%)',
                                                    item)
                                                for value in numeric_values:
                                                    # Check if the numeric value
                                                    # is not associated with a
                                                    # string
                                                    if not any(
                                                            char.isalpha()
                                                            for char in
                                                            item):
                                                        (extracted_numbers.
                                                         append(value))
                                            values_after_keyword = list(
                                                set(extracted_numbers))
                                        elif (field.purchase_line_field_id.name
                                              == 'taxes_id'):
                                            if (purchase_digitization.tax_type
                                                    == 'tax_per_line'):
                                                split_tax_column = [
                                                    val for value in
                                                    values_after_keyword for val
                                                    in value.split()]
                                                percentage_numbers = (
                                                    re.findall(
                                                        r'\d+(?:\.\d+)?%',
                                                        str(split_tax_column)))
                                                values_after_keyword = \
                                                    percentage_numbers
                                        elif (field.purchase_line_field_id.name
                                              == 'discount'):
                                            split_values = [
                                                item.split() for item in
                                                values_after_keyword]
                                            flattened_list = [item for sublist
                                                              in split_values
                                                              for
                                                              item in sublist]
                                            filtered_list = [disc for disc in
                                                             flattened_list if
                                                             '%' not in disc]
                                            values_after_keyword = filtered_list
                                        elif (field.purchase_line_field_id.name
                                              == 'price_unit'):
                                            values_after_keyword = [
                                                val.replace(',', '') for val in
                                                values_after_keyword]
                                            filtered_values_after_keyword = []
                                            for values in values_after_keyword:
                                                if not any(
                                                        val.isalpha() for val in
                                                        values):
                                                    filtered_values_after_keyword.append(
                                                        values)
                                            split_values_after_keyword = [
                                                val
                                                for value
                                                in
                                                filtered_values_after_keyword
                                                for val in value.split()
                                                if
                                                not re.search(
                                                    r'\d+%',
                                                    val)]
                                            price_pattern = \
                                                r'(\d+(\.\d{1,2})?)(?![\d%]*%)'
                                            prices = []
                                            for vals in \
                                                    split_values_after_keyword:
                                                price_match = re.match(
                                                    price_pattern, val)
                                                if price_match:
                                                    price = float(
                                                        price_match.group())
                                                    prices.append(price)
                                                else:
                                                    if not any(
                                                            char.isalpha() for
                                                            char in vals):
                                                        val = ''.join(
                                                            char for char in
                                                            vals
                                                            if
                                                            char.isdigit() or
                                                            char == '.')
                                                        prices.append(val)
                                            prices = [item for item in prices if
                                                      item != '']
                                            values_after_keyword = prices
                                if values_after_keyword:
                                    purchase_line_values[
                                        field.purchase_line_field_id.name] = \
                                        values_after_keyword
                                else:
                                    purchase_line_values[
                                        field.purchase_line_field_id.name] = \
                                        cleaned_column_values
                                break  # Stop searching once the column is found
                            if (purchase_digitization.tax_type ==
                                    'tax_per_invoice'):
                                if (field.purchase_line_field_id.name ==
                                        'taxes_id'):
                                    for line_keyword in (
                                            field.line_field_keyword_ids):
                                        keyword_pattern = rf'\
                                        ({re.escape(line_keyword.name.lower())})'
                                        keyword_match = re.search(
                                            keyword_pattern,
                                            text.lower())
                                        if keyword_match:
                                            # Get the start position
                                            # of the match
                                            keyword_start = keyword_match.start()
                                            window_size = 45
                                            text_window = \
                                                text[keyword_start:
                                                     keyword_start +
                                                     window_size]
                                            percentage_numbers = (
                                                re.findall(
                                                    r'\d+(?:\.\d+)?%',
                                                    str(text_window)))
                                            if not percentage_numbers:
                                                percentage_numbers = re.findall(
                                                    r'\d+(?:\.\d+)?%',
                                                    text)
                                            values_after_keyword = \
                                                percentage_numbers
                                            purchase_line_values[
                                                field.purchase_line_field_id.
                                                name] = values_after_keyword
        return purchase_line_values

    def get_order_line(self, table_data, purchase_line_column_values):
        """
        Create order lines based on extracted table data.
        :param table_data: Structured table data extracted from the PDF.
        :param purchase_line_column_values: Values extracted from the data.
        """
        product_ids = self.env['product.product'].search_read(
            [], ['name', 'default_code', 'lst_price', 'display_name',
                 'standard_price'])
        for product in product_ids:
            product['taxes_id'] = None
        # Find products in the table data based on name, code, or display name
        found_products_with_display_name = [product for data in table_data for
                                            row in
                                            data for product in product_ids if
                                            product['display_name'] in str(row)]

        cleaned_table_data = [
            [[item.replace('\n', '') for item in row] for row in data] for data
            in table_data]
        table_data_copy = cleaned_table_data.copy()
        new_table_data = [[row for row in data if all(
            product['display_name'] not in str(row) for product in product_ids)]
                          for data in table_data_copy]
        found_products_with_name = [product for data in new_table_data for row
                                    in
                                    data for product in product_ids if
                                    product['name'] in str(row)]
        found_products_with_all_name = (
                found_products_with_display_name +
                [item for item in found_products_with_name if item['id'] not in
                 {value['id'] for value in found_products_with_display_name}])
        found_display_name_rows = [row for data in cleaned_table_data for row in
                                   data
                                   for
                                   product in
                                   product_ids if
                                   product['display_name'] in str(row)]
        found_name_rows = [row for data in cleaned_table_data for row in data
                           for
                           product in
                           product_ids if product['name'] in str(row)]
        found_all_name_rows = [list(sublist) for sublist in
                               set(tuple(sublist) for sublist in
                                   found_display_name_rows + found_name_rows)]
        found_products_with_code = [product for data in cleaned_table_data for
                                    row in
                                    data for product in product_ids if
                                    str(product['default_code']) in str(row)]
        found_code_rows = [row for data in cleaned_table_data for row in data
                           for
                           product in
                           product_ids if
                           str(product['default_code']) in str(row)]
        products_with_code_ids = {product['id'] for product in
                                  found_products_with_code}
        filtered_products_with_name = [rec for rec in
                                       found_products_with_all_name
                                       if
                                       rec['id'] not in products_with_code_ids]
        filtered_products_with_code = [rec for rec in found_products_with_code
                                       for row in found_code_rows if
                                       rec['name'] in str(row)]
        filtered_products_with_code = [product for index, product in
                                       enumerate(filtered_products_with_code)
                                       if product
                                       not in filtered_products_with_code[
                                           :index]]
        filtered_found_code_rows = [row for rec in found_products_with_code for
                                    row in found_code_rows if
                                    rec['name'] in str(row)]
        filtered_found_code_rows_set = set(
            tuple(row) for row in filtered_found_code_rows)
        # Remove rows in found_name_rows that are also in found_code_rows
        filtered_found_name_rows = [row for row in found_all_name_rows if
                                    tuple(row)
                                    not in filtered_found_code_rows_set]
        filtered_found_name_rows = set(
            tuple(row) for row in filtered_found_name_rows)
        if not filtered_found_name_rows:
            actual_products = filtered_products_with_code
            actual_rows = filtered_found_code_rows_set
        else:
            actual_products = (filtered_products_with_code
                               + filtered_products_with_name)
            actual_rows = (filtered_found_code_rows_set
                           | filtered_found_name_rows)
        # Replace "\n" with a space in strings in actual_rows
        actual_rows = {tuple(cell.replace('\n', ' ') for cell in row) for
                       row in actual_rows}
        actual_rows = {tuple(cell.replace(',', '') for cell in row) for
                       row in actual_rows}
        final_purchase_lines = []
        # Create final invoice lines based on found products and rows
        if actual_products:
            for product in actual_products:
                for row in actual_rows:
                    if (str(product['default_code']) in str(row) or product[
                        'display_name'].replace(',', '') in str(row) or
                            str(row) in product['display_name']):
                        final_product_price = self.find_product_price(
                            product, row, purchase_line_column_values)
                        final_product_qty = self.find_product_quantity(
                            product, row, purchase_line_column_values)
                        final_product_tax = self.find_product_tax(
                            product, row, purchase_line_column_values)
                        final_product_discount = self.find_product_discount(
                            product, row, purchase_line_column_values)
                purchase_line = {'order_id': self.id,
                                 'product_id': product['id'],
                                 'product_qty': final_product_qty[
                                     'product_qty'] if final_product_qty[
                                     'product_qty'] else 1,
                                 'price_unit': final_product_price[
                                     'price_unit'],
                                 'taxes_id': final_product_tax['taxes_id'] if
                                 final_product_tax['taxes_id'] else None,
                                 'discount': final_product_discount['discount']}
                final_purchase_lines.append(purchase_line)
            if final_purchase_lines:
                for purchase_line in final_purchase_lines:
                    self.order_line.create(purchase_line)
                    self.ocr_digitize_completed = True
                if self.ocr_digitize_completed:
                    self.ocr_digitize_failed = False if (
                        self.ocr_digitize_failed) else False
        else:
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({
                'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed.")})

    def find_product_price(self, product, row, purchase_line_column_values):
        """
        Update the product price based on the extracted row from the uploaded PO.
        :param product: Product information (dictionary).
        :param row: Extracted row from the table.
        :param purchase_line_column_values: Column values from the PO.
        :return: Updated product dictionary with 'price_unit'.
        """
        row = list(row)
        # Remove currency symbols
        currency_symbols = set(
            currency.symbol for currency in self.env['res.currency'].search([])
        )
        row = [value for value in row if not any(
            currency_symbol in str(value) for currency_symbol in
            currency_symbols)]
        # Remove percentages and split row
        row = [value for value in str(row).split() if "%" not in value]

        # Extract numeric values
        price_matches = re.findall(r'\b(\d+(\.\d{1,2})?)\b', str(row))
        filtered_prices = []
        for match in price_matches:
            filtered_prices += (
                tuple(item for item in match if
                      item != '' and not item.startswith('.'))
            )

        # Remove irrelevant numbers (product code etc.)
        filtered_prices = [p for p in filtered_prices if
                           str(p) != str(product.get('default_code', ''))]

        # Decide price based on cost price
        if product.get('standard_price', 0) == 0:
            # If no cost price → take from PO (2nd value preferred)
            if len(filtered_prices) > 1:
                product['price_unit'] = float(filtered_prices[1])
            # elif filtered_prices:
            #     product['price_unit'] = float(filtered_prices[0])
            else:
                product['price_unit'] = float(filtered_prices[0])
        else:
            # If cost price exists → keep that instead of PO price
            product['price_unit'] = product['standard_price']

        return product

    def find_product_quantity(self, product, row, purchase_line_column_values):
        """
        Update the product quantity based on the extracted row and values.
        :param product: Product information.
        :param row: Extracted row from the table.
        :param purchase_line_column_values: Values extracted from the table.
        :return: Updated product information.
        """
        row = list(row)
        # Remove currency symbols from the row
        currency_symbols = set(
            currency.symbol for currency in self.env['res.currency'].search([]))
        row = [value for value in row if not any(
            currency_symbol in str(value).split() for currency_symbol in
            currency_symbols)]
        row = [value for value in str(row).split() if "%" not in value]
        # Find quantity matches in the row
        quantity_match = re.findall(
            r'\b(\d+(\.\d{1,2})?)(?![%])\b', str(row))
        filtered_quantity = []
        for match in quantity_match:
            filtered_quantity += (
                tuple(item for item in match if
                      item != '' and not item.startswith(
                          '.')))
        for qty in filtered_quantity:
            if float(qty) == product['standard_price']:
                filtered_quantity.remove(qty)
                break
        filtered_quantity = [qty for qty in filtered_quantity if
                             str(qty) != product['default_code']]
        # Update the product quantity based on matches with extracted quantities
        product_qty = [float(qty) for qty in filtered_quantity if
                       qty in purchase_line_column_values['product_qty']]
        product['product_qty'] = max(product_qty) if product_qty else max(
            filtered_quantity)
        return product

    def find_product_tax(self, product, row, purchase_line_column_values):
        """
        Update the product tax based on the extracted row and values.
        :param product: Product information.
        :param row: Extracted row from the table.
        :param purchase_line_column_values: Values extracted from the table.
        :return: Updated product information.
        """
        # Retrieve relevant tax configurations and tax rates
        purchase_digitization = self.env['purchase.digitization'].search(
            [('active_configuration', '=', True)])
        purchase_tax = self.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'purchase')])
        row = list(row)
        # Extract percentage numbers from the row
        if purchase_digitization.tax_type == 'tax_per_line':
            percentage_numbers = (
                re.findall(r'\d+(?:\.\d+)?%', str(row).strip()))
            if 'taxes_id' in purchase_line_column_values.keys():
                actual_tax = [percentage for percentage in percentage_numbers if
                              percentage in purchase_line_column_values[
                                  'taxes_id']]
            else:
                actual_tax = percentage_numbers
        else:
            actual_tax = purchase_line_column_values['taxes_id'] if \
                'taxes_id' in purchase_line_column_values.keys() else []
            # Update the product tax based on the actual tax values
        for tax in actual_tax:
            formatted_tax = float(tax.strip('%'))
            for p_tax in purchase_tax:
                if formatted_tax == p_tax.amount:
                    product['taxes_id'] = [p_tax.id]
        return product

    def find_product_discount(self, product, row, purchase_line_column_values):
        """
        Update the product discount based on the extracted row and values.
        :param product: Product information.
        :param row: Extracted row from the table.
        :param purchase_line_column_values: Values extracted from the table.
        :return: Updated product information.
        """
        row = list(row)
        # Remove currency symbols from the row
        currency_symbols = set(
            currency.symbol for currency in self.env['res.currency'].search([]))
        row = [value for value in row if not any(
            currency_symbol in str(value).split() for currency_symbol in
            currency_symbols)]
        row = [value for value in str(row).split() if "%" not in value]
        # Find discount matches in the row
        discount_match = re.findall(
            r'\b(\d+(\.\d{1,2})?)(?![%])\b', str(row))
        filtered_discount = []
        for match in discount_match:
            filtered_discount += (
                tuple(item for item in match if
                      item != '' and not item.startswith(
                          '.')))
        for disc in filtered_discount:
            if float(disc) == product['standard_price']:
                filtered_discount.remove(disc)
                break
        filtered_discount = [qty for qty in filtered_discount if
                             str(qty) != product['default_code']]
        # Update the product discount based on matches with extracted discounts
        if 'discount' in purchase_line_column_values.keys():
            product_discount = [float(qty) for qty in filtered_discount if
                                qty in purchase_line_column_values['discount']]
        else:
            product_discount = []
        product['discount'] = max(
            product_discount) if product_discount else 0.00
        return product

    def action_create_products(self, combined_table,
                               purchase_line_column_values):
        """
        Create products based on the combined table data.
        :param combined_table: Combined table data.
        :param purchase_line_column_values: Values extracted from the table.
        :return: List of created products by OCR.
        """
        # Fetch invoice digitization configuration
        purchase_digitization = self.env['purchase.digitization'].search(
            [('active_configuration', '=', True)])
        # Check if product creation type is 'create_product'
        if purchase_digitization.product_creation_type == 'create_product':
            if not combined_table.empty:
                # Extract relevant columns based on configured keywords
                columns_to_keep = []
                df = combined_table
                for col in df.columns:
                    values = df[col].tolist()
                    cleaned_values = [str(item).replace('\n', '') for item in
                                      values]
                    cleaned_values = [str(item).replace('\xa0', ' ') for item in
                                      cleaned_values]
                    keywords = set(
                        keyword.name.lower() for field in
                        purchase_digitization.purchase_line_field_details_ids
                        if field.purchase_line_field_id.name in [
                            'product_id', 'price_unit',
                            'default_code']
                        for keyword in field.line_field_keyword_ids)
                    for val in cleaned_values:
                        if any(keyword in val.lower() for keyword in keywords):
                            columns_to_keep.append(col)
                df_filtered = df[columns_to_keep]
                df_filtered = df_filtered.applymap(
                    lambda x: np.nan if
                    isinstance(x, str) and x.strip() == '' else x)
                df_filtered = df_filtered.dropna(how='any')
                # Filter and clean rows from combined table data
                date_pattern = r'\d{2}/\d{2}/\d{4}'
                table_rows = []
                for row in df_filtered.itertuples(index=False):
                    row = list(set(row))
                    row_data = []
                    for data in row:
                        row_data.append(data)
                    cleaned_row_data = [item.strip() for item in
                                        row_data if item.strip()]
                    filtered_row_data = [item for item in cleaned_row_data if
                                         not re.match(date_pattern, item)]
                    cleaned_list = [item.replace('\xa0', ' ') for item
                                    in filtered_row_data]
                    filtered_cleaned_list = [item.replace('\n', ' ') for item
                                             in cleaned_list]
                    table_rows.append(filtered_cleaned_list)
                    # Extract relevant field names for product details
                field_names_to_check = ['product_id', 'price_unit',
                                        'default_code']
                keywords = set(
                    keyword.name.lower() for field in
                    purchase_digitization.purchase_line_field_details_ids if
                    field.purchase_line_field_id.name in field_names_to_check
                    for keyword in field.line_field_keyword_ids)
                # Filter rows based on configured keywords
                new_table_rows = [table_rows[table_rows.index(row) + 1:] for row
                                  in
                                  table_rows if any(
                        keyword in str(row).lower() for keyword in keywords)]
                product_ids = self.env['product.product'].search([])
                if new_table_rows:
                    filtered_table_rows = [
                        row for row in new_table_rows[0] if not any(
                            product.name.lower() in str(row).lower() for product
                            in
                            product_ids)]
                else:
                    filtered_table_rows = [
                        row for row in table_rows if not any(
                            product.name.lower() in str(row).lower() for product
                            in
                            product_ids)]
                final_table_rows = []
                # Process filtered rows to extract product details
                for row in filtered_table_rows:
                    split_row = str(row).split()
                    special_char_pattern = r'[^\w.%]+'
                    cleaned_split_row = [
                        re.sub(special_char_pattern, '', item) for item in
                        split_row]
                    price_in_row = [float(num) for num in cleaned_split_row if
                                    re.match(r'-?\d+\.\d+', num)]

                    price_on_row = [
                        float(num) for num in cleaned_split_row if
                        '%' not in num and re.match(r'\d', num)]
                    if price_in_row or price_on_row:
                        final_table_rows.append(row)
                final_product_details = []
                ocr_products = []
                # extract the product code and name to create the product
                for row in final_table_rows:
                    assumed_product_name = []
                    product_code = ''
                    for item in row:
                        for value in purchase_line_column_values['product_id']:
                            if value.lower() in item.lower():
                                column_keys = [
                                    key for key in
                                    purchase_line_column_values.keys()]
                                split_value = value.split()
                                if 'default_code' not in column_keys:
                                    for val in split_value:
                                        if val in [split_value[0],
                                                   split_value[-1]]:
                                            if re.match(r'^[a-zA-Z0-9]+$',
                                                        val) and re.search(
                                                r'\d', val):
                                                product_code = val
                                            elif re.match(
                                                    r'^[a-zA-Z0-9!@#$%^&*\[\]_]+$',
                                                    val) and not val.isalpha():
                                                product_code = val
                                            elif re.match(
                                                    r'^[0-9]+$',
                                                    val) and not val.isalpha():
                                                product_code = val
                                    if product_code:
                                        value = value.replace(product_code,
                                                              '')
                                        assumed_product_name.append(value)
                                    else:
                                        assumed_product_name.append(value)
                                    product_code = [product_code]
                                else:
                                    assumed_product_name.append(value)
                                    product_code = \
                                        [item for item in row if item in
                                         purchase_line_column_values[
                                             'default_code']]
                        # assign product code
                    assumed_product_code = product_code
                    # Remove currencies from row
                    currency_names = self.env['res.currency'].search_read(
                        [('active', 'in', [False, True])], ['name', 'symbol'])
                    for item in row:
                        for currency in currency_names:
                            if currency['name'] in str(row):
                                new_item = item.replace(currency['name'], '')
                                row.remove(item)
                                row.append(new_item)
                    numerical_row = [item for item in row if
                                     not any(char.isalpha() for char in item)]
                    split_numerical_row = str(numerical_row).split()
                    special_char_pattern = r'[^\w.%]+'
                    cleaned_split_numerical_row = [
                        re.sub(special_char_pattern, '', item) for
                        item
                        in split_numerical_row]
                    price_in_row = [float(num) for num in
                                    cleaned_split_numerical_row if
                                    re.match(r'-?\d+\.\d+', num)]
                    if not price_in_row:
                        price_in_row = [float(num) for num in
                                        cleaned_split_numerical_row if
                                        '%' not in num and re.match(r'\d+',
                                                                    num)]
                    assumed_product_price = max(
                        price_in_row) if price_in_row else 0
                    assumed_product_name = [' '.join(item.split()) for item in
                                            assumed_product_name]
                    product_details = {
                        'name': assumed_product_name[0], 'ocr_product': True,
                        'detailed_type': 'product'} if assumed_product_name \
                        else {'name': None, 'ocr_product': True, }
                    product_details['standard_price'] = \
                        assumed_product_price if assumed_product_price else None
                    product_details[
                        'default_code'] = assumed_product_code[
                        0] if assumed_product_code else None
                    final_product_details.append(product_details)
                    # Create the product by extracting details.
                for details in final_product_details:
                    ocr_product = self.env['product.product'].create([details])
                    ocr_products.append(ocr_product)
                return ocr_products

    def action_retry_digitization(self):
        """
                Retry the digitization process by resetting order lines and
                triggering digitization.
                """
        self.order_line = None
        self.action_send_digitization()
        if self.ocr_digitize_failed:
            return {
                'name': 'AI Digitization',
                'type': 'ir.actions.act_window',
                'res_model': 'digitization.ai.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_active_id': self.id},
            }


    def get_details_ai(self, text):
        """
            Uses AI to extract detailed purchase quotation information,
            product specifics, and pricing from the provided text.
            :param text: Text content to extract information from.
            :return: Extracted information as a string.
            """
        company_name = self.env.company.name
        gpt_response = ""
        try:
            conversation_history = [
                {'role': 'user',
                 'content':
                     f'Please extract detailed purchase quotation information, '
                     f'product specifics, and pricing from a provided PDF file.'
                     f' Your task involves capturing key data such as the '
                     f'product code,quantity, individual item price, '
                     f'tax details, and any available discounts. Its crucial to'
                     f'accurately discern the unit price for each product, not'
                     f'solely the total cost. Be aware that discrepancies may'
                     f'occur in cases where figures like price, quantity, or'
                     f' discounts are misaligned, so exercise caution during'
                     f' extraction.To validate accuracy, calculate the total'
                     f' price of each product considering quantity and '
                     f'discounts applied.Compare this calculated amount with'
                     f' the provided total price to identify any discrepancies'
                     f' and rectify them promptly. Further, sum up the '
                     f'individual product prices to derive the total cost of'
                     f' all items and cross-verify it with the total price'
                     f' stated on the quotation. Any errors found during this'
                     f' process can be rectified by pinpointing the mistake'
                     f' and making the necessary corrections.When identifying'
                     f' the correct partner name for billing purposes, it is'
                     f' essential to consider the individual or company to '
                     f'whom the purchase quotation is addressed. Ensure that '
                     f'the context aligns with the customer address provided'
                     f' and avoid using {company_name} in this process.'
                 }]
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': text,
                    'conversation_history': conversation_history or [],
                    'version': release.version,
                }, timeout=30)
            if response['status'] == 'success':
                gpt_response += response['content']
                if _("Continued in next message") in response['content']:
                    conversation_history = [{'role': 'user',
                                             'content': text},
                                            {'role': 'assistant',
                                             'content': response['content']}]
                    response = iap_tools.iap_jsonrpc(
                        olg_api_endpoint + "/api/olg/1/chat", params={
                            'prompt': 'continue',
                            'conversation_history': conversation_history or [],
                            'version': release.version,
                        }, timeout=30)
                    if response['status'] == 'success':
                        gpt_response += response['content']
                        return gpt_response
                else:
                    return response['content']
            elif response['status'] == 'error_prompt_too_long':
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"The PDF content you submitted was too long.")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed.")})
        except Exception as ecx:
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({'ocr_digitize_message': _(
                f"The AI Failed to Digitize the Document.")})
            logging.error(f"AccessError details: {ecx}")

    def get_quotation_details(self, pdf_details):
        """
            Extracts purchase quote details from the provided PDF text using AI
             and returns the details as a dictionary.
            :param pdf_details: Text content of the PDF document containing the
             purchase quote details.
            :return: Dictionary containing the extracted purchase quote details.
            """
        pdf_details = '\n'.join(
            [line.strip() for line in pdf_details.splitlines() if
             line.strip()])
        try:
            company_name = self.env.company.name
            conversation_history = [
                {'role': 'user',
                 'content': f"Find and extract purchase quote details, "
                            f"including partner name,vendor reference, "
                            f"payment terms, incoterm, incoterm location "
                            f"represented as a dictionary. When extracting the"
                            f" partner name do not include {company_name}."
                            f"The dictionary keys should correspond to "
                            f"partner_name,vendor_reference,payment_term,"
                            f"incoterm,incoterm_location.If the values are null"
                            f",assign a blank value to the corresponding key."
                            f"The response should only contain the dictionary"
                            f" without any additional text."
                            f"(It must strictly follow these guidelines)"
                 }]
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': pdf_details,
                    'conversation_history': conversation_history or [],
                    'version': release.version,
                }, timeout=30)
            if response['status'] == 'success':
                if isinstance(response['content'], str):
                    try:
                        purchase_details = json.loads(response['content'])
                    except json.JSONDecodeError:
                        start_index = response['content'].find("{")
                        end_index = response['content'].find("}")
                        # Extract the substring containing the list
                        extracted_quote_details = response['content'][
                            start_index:end_index + 1]
                        purchase_details = json.loads(
                            extracted_quote_details)
                    return purchase_details
            elif response['status'] == 'error_prompt_too_long':
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed.")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Failed to extract the Invoice field details.")})
        except Exception as exc:
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({'ocr_digitize_message': _(
                f"The AI Failed to Digitize the Document.")})
            logging.error(f"AccessError details: {exc}")

    def get_product_details(self, pdf_details):
        """
            Extracts product details from the provided PDF text using AI and
            returns the details as a list of dictionaries.
            :param pdf_details: Text content of the PDF document containing the
             product details.
            :return: List of dictionaries containing the extracted
            product details.
            """
        pdf_details = '\n'.join(
            [line.strip() for line in pdf_details.splitlines() if
             line.strip()])
        purchase_digitization = self.env[
            'purchase.digitization'].search(
            [('active_configuration', '=', True)])
        try:
            if purchase_digitization.tax_type == 'tax_per_line':
                conversation_history = [
                    {'role': 'user',
                     'content': f"Find and extract product details from this "
                                f"quotation,including product name,"
                                f"product code,quantity,product unit of "
                                f"measure,product price,product tax in "
                                f"percentage format with % symbol,discount. "
                                f"The dictionary keys should correspond to"
                                f" product_name(product name without "
                                f"product code),product_code, quantity,"
                                f"quantity_uom,price_unit, product_tax,"
                                f"discount.Add the each product details to"
                                f" the list as dictionary.The response should"
                                f" only contain the list of dictionary, the "
                                f"values of keys must be in string"
                                f"(in double quotes), no other text and the "
                                f"product name without product code needs "
                                f"strictly follow.(it must very very"
                                f"strictly follow) and do not return as python"
                                f" just as string(dont add new line command)."
                     }]
            else:
                conversation_history = [
                    {'role': 'user',
                     'content': f"Find and extract product details from this "
                                f"quotation, including product name, "
                                f"product code,quantity, product unit of"
                                f" measure,product price,product tax in"
                                f" percentage format with % symbol and cosider"
                                f" single tax to all the product,discount."
                                f"The dictionary keys should correspond to"
                                f" product_name(product name without product"
                                f" code),product_code, quantity,quantity_uom, "
                                f"price_unit, product_tax, discount.Add the "
                                f"each product details to the list as "
                                f"dictionary.The response should only contain"
                                f"the list of dictionary, the values of keys "
                                f"must be in string(in double quotes),no other"
                                f"text and the product name without product "
                                f"code needs strictly follow.(it must very very"
                                f"strictly follow) and do not return as python"
                                f"just as string(dont add new line command)."
                     }]
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': pdf_details,
                    'conversation_history': conversation_history or [],
                    'version': release.version,
                }, timeout=120)
            if response['status'] == 'success':
                if isinstance(response['content'], str):
                    try:
                        response_content = response['content'].replace('\n', '')
                        response_content = response_content.replace(",]", "]")
                        quote_details = json.loads(response_content)
                    except json.JSONDecodeError:
                        response_content = response['content'].replace('\n', '')
                        response_content = response_content.replace(",]", "]")
                        start_index = response_content.find("[")
                        end_index = response_content.find("]")
                        # Extract the substring containing the list
                        extracted_quote_details = response_content[
                            start_index:end_index + 1]
                        quote_details = json.loads(
                            extracted_quote_details)
                    return quote_details
            elif response['status'] == 'error_prompt_too_long':
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed.")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Failed to extract the Product details.")})
        except Exception as exc:
            self.write({'ocr_digitize_message': _(
                f"The AI Failed to Digitize the Document.")})
            logging.error(f"AccessError details: {exc}")

    def find_partner_ai(self, text, quotation_details):
        """
        Find a partner based on the extracted text from pdf and create a
        partner if not exist.
        :param text: Extracted text to search for partner information.
        :param quotation_details: Dictionary containing details extracted from
        the pdf using AI Functionality."""
        # Search for existing partners
        partner_ids = self.env['res.partner'].search(
            [('name', '!=', self.env.company.name)])
        found_partners = [partner for partner in partner_ids if
                          partner.name in text]
        if found_partners:
            self.write(
                {'partner_id': found_partners[0].id})
        else:
            # Create a new partner record if not a partner found
            partner_id = self.env['res.partner'].create(
                {'name': quotation_details[
                    'partner_name'], }) if quotation_details[
                'partner_name'] else None
            self.write({'partner_id': partner_id.id}) if partner_id else None

    def action_find_field_values_ai(self, text, quotation_details):
        """
            Finds field values in the provided text based on the quotation
            details and updates the purchase order accordingly.
            :param text: Text content to search for field values.
            :param quotation_details: Dictionary containing details extracted
            from the quotation.
            """
        if quotation_details['vendor_reference']:
            self.write(
                {'partner_ref': quotation_details['vendor_reference']})
        if quotation_details['payment_term']:
            payment_terms = self.payment_term_id.search([])
            found_term = [term for term in payment_terms if
                          term.name.lower() == quotation_details[
                              'payment_term'].lower()] if payment_terms \
                else None
            if found_term:
                self.write({'payment_term_id': found_term[0].id})
            else:
                found_term_in_text = [term for term in payment_terms if
                                      term.name.lower() in text.lower()] \
                    if payment_terms else None
                if found_term_in_text:
                    self.write({'payment_term_id': found_term[0].id})
        if quotation_details['incoterm']:
            incoterms = self.incoterm_id.search(
                [('code', '=', quotation_details['incoterm'])])
            if incoterms:
                self.write({'incoterm_id': incoterms[0].id})
            else:
                incoterms = self.incoterm_id.search([])
                found_incoterm = [term for term in incoterms if
                                  term.code in text] if incoterms else None
                if found_incoterm:
                    self.write({'incoterm_id': found_incoterm[0].id})
        if quotation_details['incoterm_location']:
            self.write(
                {'incoterm_location': quotation_details['incoterm_location']})

    def action_find_product(self, product_details):
        """
            Finds or creates products based on the provided product details and
             adds them to the purchase order.
            :param product_details: List of dictionaries containing details of
             the products to be found or created.
            """
        products = self.env['product.product'].search([])
        supplier_products_details = self.env['product.supplierinfo'].search([])
        for rec in product_details:
            quote_details = {
                'order_id': self.id,
                'product_id': None,
                'product_qty': 1,
            }
            supplier_by_code = [supplier for supplier in
                                supplier_products_details if
                                supplier.product_code if
                                supplier.product_code.lower() == str(
                                    rec['product_code']).lower()] \
                if rec['product_code'] and supplier_products_details else []
            supplier_by_code = self.env['product.supplierinfo'].search(
                [('id', 'in', [spr.id for spr in supplier_by_code])])
            products_by_supplier_code = supplier_by_code.mapped(
                'product_tmpl_id') if supplier_by_code else []
            products_by_supplier_code = self.env['product.product'].search(
                [('product_tmpl_id', 'in', [product.id for product in
                                            products_by_supplier_code])]) if products_by_supplier_code else []
            if not products_by_supplier_code:
                products_by_supplier_code = supplier_by_code.mapped(
                    'product_id') if supplier_by_code else []
            products_by_name = [
                product for product in products if
                rec['product_name'].lower() == product.name.lower()] \
                if not products_by_supplier_code and rec['product_name'] else []
            products_by_display_name = [
                product for product in products
                if rec['product_name'].lower() in product.display_name.lower()
            ] if len(products_by_name) > 1 else []
            if products_by_supplier_code:
                quote_details['product_id'] = products_by_supplier_code[0].id
            elif products_by_display_name:
                quote_details['product_id'] = products_by_display_name[0].id
            elif products_by_name:
                quote_details['product_id'] = products_by_name[0].id

            # Extracting quantity from the product details
            qty_match = re.search(r'\d+(\.\d+)?', str(rec['quantity'])) if rec[
                'quantity'] else None
            if qty_match:
                extracted_quantity = qty_match.group(0)
                quote_details['product_qty'] = float(extracted_quantity)
            # Extracting unit of measure from the product details if available
            uom_list = self.env['uom.uom'].search([])
            found_uom = [uom for uom in uom_list if
                         uom.name == rec['quantity_uom']] if (
                    rec['quantity_uom'] and uom_list) else []
            if found_uom:
                quote_details['product_uom'] = found_uom[0].id

            # Extracting product price from the product details
            price_unit = str(rec['price_unit']).replace(',',
                                                        '')  # Remove commas
            price_match = re.search(r'\d+(\.\d+)?', price_unit) if \
                rec['price_unit'] else None
            if price_match:
                extracted_price = price_match.group(0)
                quote_details['price_unit'] = float(extracted_price)

            # Extracting product tax from the product details
            tax_list = self.env['account.tax'].search(
                [('active', '=', True), ('type_tax_use', '=', 'purchase')])
            tax_rate = rec['product_tax'].rstrip('%') if rec[
                'product_tax'] else 0.0
            product_tax = [tax for tax in tax_list if
                           tax.amount == float(tax_rate)] if tax_list else []
            quote_details['taxes_id'] = [
                product_tax[0].id] if product_tax else None

            # Extracting product discount from the product details
            discount = re.search(r'\d+(\.\d+)?',
                                 str(rec['discount'])) if rec[
                'discount'] else None
            product_discount = discount.group(0) if discount else None
            quote_details['discount'] = float(
                product_discount) if product_discount else 0.0
            if quote_details['product_id']:
                self.order_line.create(quote_details)
            else:
                self.action_create_product_ai(rec, quote_details)
            if self.order_line:
                self.ocr_digitize_completed = True
            if self.ocr_digitize_completed:
                self.ocr_digitize_failed = False if (
                    self.ocr_digitize_failed) else False

    def action_create_product_ai(self, product_details, quote_details):
        """
            Creates a product based on the provided product and quote details.
            :param product_details: Dictionary containing details of the product
             to be created.
            :param quote_details: Dictionary containing details of the quote.
            """
        purchase_digitization = self.env[
            'purchase.digitization'].search(
            [('active_configuration', '=', True)])
        if purchase_digitization.product_creation_type == 'create_product':
            if product_details['product_name']:
                product_values = {
                    'name': product_details['product_name'],
                    'ocr_product': True,
                    'detailed_type': 'product'
                }
                price_unit = quote_details.get('price_unit', None)
                if price_unit is not None:
                    product_values['standard_price'] = quote_details[
                        'price_unit']
                uom_unit = quote_details.get('product_uom', None)
                if uom_unit is not None:
                    product_values['uom_id'] = quote_details['product_uom']
                    product_values['uom_po_id'] = quote_details[
                        'product_uom']
                product_id = self.env['product.product'].create(product_values)
                quote_details['product_id'] = product_id.id
                self.order_line.create(quote_details)
