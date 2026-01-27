# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    """ Class to add a reference field in sale order to connect support service
    and sale order """
    _inherit = "sale.order"

    ticket_reference = fields.Char(help="Reference for support service ticket")
