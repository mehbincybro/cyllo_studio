# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    """Class to add new fields to res.partner"""
    _inherit = 'res.partner'

    office_365_identifier = fields.Char(string="Contact id",
                                        help="Id to distinguish each contact imported from office 365")
    connector_ids = fields.Many2many('cyllo.office.connector', help="Connector of the contact")
    office_connectors_ids = fields.One2many('cyllo.office.connector.line', 'partner_id',
                                            string="Connected Instances", help="List of synced instances")
