# -*- coding: utf-8 -*-
import base64
import json
from odoo import api, fields, models
from odoo.exceptions import AccessError


class SpreadsheetAbstract(models.AbstractModel):
    """ Spreadsheet abstract model for inheriting to spreadsheet model"""
    _name = "spreadsheet.abstract"
    _inherit = "spreadsheet.mixin"
    _description = "Spreadsheet abstract for inheritance"

    name = fields.Char(help="For getting the name", required=True)
    spreadsheet_raw = fields.Serialized(help="Contains the spreadsheet information")
    spreadsheet_revision_ids = fields.One2many("spreadsheet.cy.revision", inverse_name="res_id",
                                               help="Used to store the changes on the spreadsheet",
                                               domain=lambda r: [("model", "=", r._name)])

    def get_spreadsheet_data(self):
        """ Get the spreadsheet data,both content and metadata
            :return: Data related to spreadsheet including import mode"""
        self.ensure_one()
        mode = "normal"
        try:
            self.check_access_rights("write")
            self.check_access_rule("write")
        except AccessError:
            mode = "readonly"
        return {
            "name": self.name,
            "spreadsheet_raw": self.spreadsheet_raw,
            "revisions": [
                {
                    "type": revision.type,
                    "clientId": revision.client_id,
                    "nextRevisionId": revision.next_revision_id,
                    "serverRevisionId": revision.server_revision_id,
                    "commands": json.loads(revision.commands),
                }
                for revision in self.spreadsheet_revision_ids
            ],
            "mode": mode,
        }

    def action_open_spreadsheet(self):
        """ Button action to open spreadsheet
            :return:Client action to open spreadsheet with spreadsheet id
            and model name"""
        self.ensure_one()
        # Client action to open spreadsheet
        return {
            "type": "ir.actions.client",
            "tag": "action_load_spreadsheet",
            "params": {"spreadsheet_id": self.id, "model": self._name},
        }

    def send_spreadsheet_message(self, message):
        """ Passing message and create spreadsheet revision record
            :return: True value
        """
        self.ensure_one()
        channel = (self.env.cr.dbname, "cyllo_spreadsheet", self._name, self.id)
        message.update({"res_model": self._name, "res_id": self.id})
        if message["type"] in ["REVISION_UNDONE", "REMOTE_REVISION", "REVISION_REDONE"]:
            self.env["spreadsheet.cy.revision"].create({
                "model": self._name,
                "res_id": self.id,
                "type": message["type"],
                "client_id": message.get("clientId"),
                "next_revision_id": message["nextRevisionId"],
                "server_revision_id": message["serverRevisionId"],
                "commands": json.dumps(message.get("commands", [])),
            })
        self.env["bus.bus"]._sendone(channel, "cyllo_spreadsheet", message)
        return True

    def write(self, vals):
        """ Unlink the current spreadsheet revision which contains
            previous changes
            :param vals: List of values contains field information
            :return : Record set of current spreadsheet record"""
        if "spreadsheet_raw" in vals:
            self.spreadsheet_revision_ids.unlink()
        return super().write(vals)

    @api.model
    def add_attachment(self, spreadsheet_id):
        """
        Generating excel binary file to for attaching it to the
            ir_attachment
            :param spreadsheet_id : Id of the spreadsheet to be added
            :return : Client action for adding spreadsheet
        """
        sheet_id = self.sudo().browse(spreadsheet_id)
        if sheet_id.data:
            data_file = json.loads(base64.decodebytes(sheet_id.data).decode("UTF-8"))
            # Return client action to the js function
            return {
                'type': "ir.actions.client",
                'tag': "action_share_spreadsheet",
                'params': {
                    'name': sheet_id.name,
                    'data': data_file,
                    'id': sheet_id.id
                },
            }
