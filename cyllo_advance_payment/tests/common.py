# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import common


class TestCylloAdvancePayment(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_journal = cls.env['account.journal'].create({
            'name': 'Test Bank',
            'type': 'bank',
            'company_id': cls.env.company.id,
            'code': 'BNKT',
            'sequence': 10,
            'currency_id': cls.env.company.currency_id.id
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Partner A'
        })
        cls.payment = cls.env['account.payment'].create({
            'name': 'Test Payment',
            'payment_type': 'outbound',
            'amount': 10.0,
            'partner_type': 'customer',
            'partner_id': cls.partner.id,
            'journal_id': cls.account_journal.id
        })
        cls.payment2 = cls.env['account.payment'].create({
            'name': 'Test Payment2',
            'payment_type': 'outbound',
            'amount': 50.0,
            'partner_type': 'customer',
            'partner_id': cls.partner.id,
            'journal_id': cls.account_journal.id
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'p1',
            'company_id': cls.env.company.id,
        })
        cls.purchase1 = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'advance_payment_ids': [cls.payment.id, cls.payment2.id],
            'order_line': [
                (fields.Command.create({
                    'product_id': cls.product_a.id,
                    'product_qty': 2.0,
                }))],
        })
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'advance_payment_ids': [cls.payment.id, cls.payment2.id],
            'order_line': [
                (fields.Command.create({
                    'product_id': cls.product_a.id,
                    'product_uom_qty': 2.0,
                }))],
        })
