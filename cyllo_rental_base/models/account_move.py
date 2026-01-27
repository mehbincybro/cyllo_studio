# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    """ Adding contract id in account.move."""
    _inherit = 'account.move'

    contract_id = fields.Many2one('rental.contract',
                                  help='Select the associated contract for this record.')


class AccountMoveLine(models.Model):
    """Adding Many2Many relationship to account move line model"""
    _inherit = "account.move.line"

    rental_order_ids = fields.Many2many("rental.order", string='Rental Orders')
