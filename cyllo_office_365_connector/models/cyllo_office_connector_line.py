# -*- coding: utf-8 -*-
from odoo import fields, models


class CylloOfficeConnectorLine(models.Model):
    """Class to add new fields to res.partner"""
    _name = 'cyllo.office.connector.line'
    _description = "Office Connector Line "

    office_365_identifier = fields.Char(string="Contact id",
                                        help="Id to distinguish each contact imported from office 365")
    connector_id = fields.Many2one('cyllo.office.connector', help="Connector of the contact")
    partner_id = fields.Many2one('res.partner', help="Connector of the contact")
    activity_id = fields.Many2one('mail.activity', help="Connector of the Activity")
    type = fields.Char(string="Type od data", help="Type of data which we are linking")
