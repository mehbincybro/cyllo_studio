# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentTransaction(models.Model):
    """ Adding rental order ids in payment transaction """
    _inherit = 'payment.transaction'

    rental_order_ids = fields.Many2many('rental.order', 'rental_order_transaction_rel',
                                        'transaction_id', 'rental_order_id', string='Rental Orders',
                                        copy=False, readonly=True,
                                        help='This field stores the rental orders associated with the current record.')
