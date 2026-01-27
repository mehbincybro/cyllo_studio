# -*- coding: utf-8 -*-
from odoo import fields, models


class MailActivity(models.Model):
    """Class to add new fields to res.partner"""
    _inherit = 'mail.activity'

    office_365_identifier = fields.Char(string="Contact id",
                                        help="Id to distinguish each activity imported from office 365")
    connector_ids = fields.Many2many('cyllo.office.connector', help="Connector of the activity")
    office_connectors_ids = fields.One2many('cyllo.office.connector.line', 'activity_id',
                                            string="Connected Instances", help="List of synced instances")
