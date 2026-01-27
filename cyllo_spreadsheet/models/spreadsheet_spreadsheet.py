# -*- coding: utf-8 -*-
import base64
import io
import json
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SpreadsheetSpreadsheet(models.Model):
    """ Used to store spreadsheet datas also passes client action to display
            the data to spreadsheet template """
    _name = "spreadsheet.spreadsheet"
    _inherit = ["spreadsheet.abstract", "spreadsheet.mixin", "mail.thread",
                "mail.activity.mixin"]
    _description = "Spreadsheet"

    data = fields.Binary(readonly=True, help="For adding spreadsheet data as a data file ")
    spreadsheet_data = fields.Binary(help="For uploading your excel file and edit it inside spreadsheet ")
    excel_file_name = fields.Char(help="Storing uploaded file name")
    filename = fields.Char(string="File Name", help="For getting file name", compute="_compute_filename")
    spreadsheet_raw = fields.Serialized(help="Saving spreadsheet information from the js file",
                                        compute="_compute_spreadsheet_raw", inverse="_inverse_spreadsheet_raw")
    owner_id = fields.Many2one("res.users", help="Owner who created the spreadsheet", required=True,
                               default=lambda r: r.env.user.id)
    contributor_ids = fields.Many2many("res.users", relation="spreadsheet_contributor", column1="spreadsheet_id",
                                       column2="user_id", string="Contributors", help="Person who can edit the spreadsheet")
    reader_ids = fields.Many2many("res.users", relation="spreadsheet_reader", column1="spreadsheet_id",
                                  column2="user_id", string="Readers", help="Person who can only read the spreadsheet")
    company_id = fields.Many2one('res.company', help="Company Name", default=lambda self: self.env.company)
    create_date = fields.Date(string="Created Date", help="Date when the spreadsheet is created",
                              default=fields.Date.today())
    image_1920 = fields.Image()

    @api.depends("name")
    def _compute_filename(self):
        """ Calculating the json file name"""
        for record in self:
            record.filename = "%s.json" % (self.name or _("Unnamed"))

    @api.depends("data")
    def _compute_spreadsheet_raw(self):
        """ Read and store the spreadsheet row details while opening
                                the spreadsheet """
        for dashboard in self:
            if dashboard.data:
                dashboard.spreadsheet_raw = json.loads(base64.decodebytes(dashboard.data).decode("UTF-8"))
            else:
                dashboard.spreadsheet_raw = {}

    def _inverse_spreadsheet_raw(self):
        """ Inverse function for the spreadsheet_raw field"""
        for record in self:
            record.data = base64.encodebytes(json.dumps(record.spreadsheet_raw).encode("UTF-8"))

    def _get_spreadsheet_data(self):
        """ For getting excel content while adding a new spreadsheet.
                       Returns file as a json content"""
        if self.spreadsheet_data:
            raw_file = base64.decodebytes(self.spreadsheet_data)
            input_files = io.BytesIO(raw_file)
            data = {}
            input_zip_file = zipfile.ZipFile(input_files)
            for info in input_zip_file.infolist():
                try:
                    file_content = input_zip_file.read(info.filename).decode('utf-8')
                except UnicodeDecodeError:
                    file_content = base64.b64encode(input_zip_file.read(info.filename)).decode('utf-8')
                data[info.filename] = file_content
            self.spreadsheet_raw = data

    @api.model_create_multi
    def create(self, vals_list):
        """
        Passing the Excel file content to the spreadsheet raw field
        :param vals_list :List of dictionary contains field value
        :return : Record set of spreadsheet
        """
        spreadsheet = super(SpreadsheetSpreadsheet, self).create(vals_list)
        spreadsheet._get_spreadsheet_data()
        return spreadsheet

    def get_xlsx_file(self, files):
        """
        Generate xlsx content using zip files and passed it to the controller.
            :param files: Spreadsheet file content
            :return : Excel file binary values
        """
        stream = io.BytesIO()
        zip_file = zipfile.ZipFile(stream, 'w')
        for file in files:
            if 'content' in file:
                zip_file.writestr(file['path'], file['content'])
        zip_file.close()
        return stream.getvalue()

    @api.onchange('spreadsheet_data')
    def _onchange_spreadsheet_data(self):
        """"Method used to ensure the uploading file is xlsx"""
        if self.spreadsheet_data and self.excel_file_name.rsplit('.', 1)[1] != 'xlsx':
            raise ValidationError("Choose xlsx file")

    def write(self, vals):
        """Used to update the spreadsheet when changing the spreadsheet"""
        res = super(SpreadsheetSpreadsheet, self).write(vals)
        if 'spreadsheet_data' in vals.keys():
            self._get_spreadsheet_data()
        return res

    @api.model
    def share_sheet_multiple(self, sheets, contributors, readers):
        """ Share the sheet for multiple contributors"""
        for sheet in sheets:
            sheet_record = self.browse(sheet)
            sheet_record.reader_ids = [fields.Command.link(reader) for reader in readers]
            sheet_record.contributor_ids = [fields.Command.link(contributor) for contributor in contributors]
