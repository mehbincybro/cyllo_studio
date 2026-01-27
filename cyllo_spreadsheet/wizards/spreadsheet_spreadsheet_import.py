# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpreadsheetSpreadsheetImport(models.TransientModel):
    """ Wizard for importing spreadsheet data .Determine the mode of importing
        and add data to the spreadsheet"""
    _name = "spreadsheet.spreadsheet.import"
    _description = "Import data to spreadsheet"

    @api.model
    def _default_mode_id(self):
        """ Returns default import mode"""
        return self.env["spreadsheet.spreadsheet.import.mode"].search([], limit=1).id

    name = fields.Char(help="Adding name of spreadsheet", required=True)
    mode_id = fields.Many2one("spreadsheet.spreadsheet.import.mode", help="Mode of import", required=True,
                              default=lambda r: r._default_mode_id())
    mode = fields.Char(string="Code", help="For getting import mode code", related="mode_id.code")
    import_data = fields.Serialized(help="Spreadsheet data")
    spreadsheet_id = fields.Many2one("spreadsheet.spreadsheet", help="Getting spreadsheet")

    def action_insert_spreadsheet(self):
        """ Insert view into spreadsheet.Determine which import mode and
            call the corresponding function dynamically."""
        self.ensure_one()
        return getattr(self, "_insert_spreadsheet_%s" % self.mode_id.code)()

    def _create_spreadsheet_vals(self):
        """ Return name for the new spreadsheet"""
        return {"name": self.name}

    def _insert_spreadsheet_new(self):
        """ Create new spreadsheet and insert data into it
         :return: Client action to open spreadsheet with data
        """
        spreadsheet = self.env["spreadsheet.spreadsheet"].create(
            self._create_spreadsheet_vals())
        import_data = self.import_data
        import_data['name'] = self.name
        import_data["new"] = 1
        return {
            "type": "ir.actions.client",
            "tag": "action_load_spreadsheet",
            "params": {
                "model": spreadsheet._name,
                "spreadsheet_id": spreadsheet.id,
                "import_data": import_data,
            },
        }

    def _insert_spreadsheet_add(self, new_sheet=False):
        """
        Insert data into an existing spreadsheet
        :param new_sheet: added new sheet inside existing spreadsheet if True
        :returns: Client action to open spreadsheet with data
        """
        import_data = self.import_data
        import_data["name"] = self.name
        import_data["new_sheet"] = new_sheet
        return {
            "type": "ir.actions.client",
            "tag": "action_load_spreadsheet",
            "params": {
                "model": "spreadsheet.spreadsheet",
                "spreadsheet_id": self.spreadsheet_id.id,
                "import_data": import_data,
            },
        }

    def _insert_spreadsheet_add_sheet(self):
        """ Adding data as a sheet inside an existing spreadsheet"""
        return self._insert_spreadsheet_add(True)
