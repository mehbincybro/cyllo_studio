# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import Command, fields
from odoo.tests import common


class RentalOrder(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.user.company_id
        journal_vals = {
            'name': 'Purchase Journal',
            'type': 'purchase',  # This indicates that it's a purchase journal
            'code': 'PUR',
            'company_id': 1
        }
        cls.env['account.journal'].create(journal_vals)
        cls.partner = cls.env['res.partner'].create({'name': 'Test partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'is_rental': True,
            'detailed_type': 'product',
        })
        return_date = fields.Datetime.now() + timedelta(days=10)
        cls.order_line = cls.env['rental.order.line'].create({
            'rental_type': 'product',
            'product_id': cls.product.id,
            'product_uom_qty': 1,
            'pickup_date': fields.Datetime.now(),
            'return_date': return_date
        })
        cls.rental_order = cls.env['rental.order'].create({
            'name': 'Test Order',
            'company_id': cls.company.id,
            'partner_id': cls.partner.id,
            'partner_invoice_id': cls.partner.id,
            'order_line_ids': cls.order_line.ids
        })
        cls.rental_contract_line = cls.env['contract.lines'].create({
            'product_id': cls.product.id,
            'product_uom_qty': 1,
            'company_id': cls.company.id,
        })
        cls.rental_contract = cls.env['rental.contract'].create({
            'partner_id': cls.partner.id,
            'contract_line_ids': cls.rental_contract_line.ids,
            'contract_start_date': fields.Date.today(),
            'contract_end_date': return_date,
            'company_id': cls.company.id,
        })
