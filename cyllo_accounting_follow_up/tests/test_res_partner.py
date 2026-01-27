# -*- coding: utf-8 -*-
from datetime import date

from odoo import fields
from odoo.tests import common


class TestResPartner(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test partner'
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Product1'
        })
        cls.followup_line = cls.env['account.followup.line'].create({
            'name': 'Level1',
            'company_id': cls.env.company.id,
            'delay': 10,
        })
        cls.followup_line2 = cls.env['account.followup.line'].create({
            'name': 'Level2',
            'company_id': cls.env.company.id,
            'delay': 11,
        })
        cls.res_partner = cls.env['res.partner'].create({
            'name': cls.partner.name,
            'move_ids': cls.create_invoice().ids,
            'done_customer_followup_id': cls.followup_line.id,
        })

    def test_compute_to_do_customer_followup_id(self):
        self.res_partner._compute_to_do_customer_followup_id()
        self.assertTrue(self.res_partner.to_do_customer_followup_id)

    def test_get_min_date(self):
        self.assertEqual(self.res_partner.get_min_date(), date(2021, 10, 7))

    @classmethod
    def create_invoice(cls):
        account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2021-10-05',
            'payment_state': 'not_paid',
            'invoice_date_due': '2021-10-07',
            'line_ids': [fields.Command.create({
                'name': 'Prod',
                'quantity': 1,
                'price_unit': 100
            })]})
        account_move.action_post()
        return account_move

