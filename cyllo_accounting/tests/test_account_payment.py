# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import datetime

from odoo import fields
from odoo.exceptions import UserError
from odoo.addons.cyllo_accounting.tests.common import TestCylloAccounting


class TestAccountPayment(TestCylloAccounting):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.fiscal_year_id = self.env['account.fiscal.year'].create([{
            'name': 'Test Fiscal Year 2023',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'company_id': self.env.company.id,
            'state': 'draft'
        }])
        self.fiscal_year_id.action_open()

    def test_compute_total_invoice_amount(self):
        self.account_move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2023-05-05',
            'date': '2023-05-05',
            'amount_residual': 1000,
            'fiscal_year_id': self.fiscal_year_id.id,
            'line_ids': [fields.Command.create({
                'product_id': self.product_tem.id,
                'amount_residual_currency': 100,
            })],
        })
        payment = self.env['account.payment'].create({
            'amount': 10.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': self.partner.id,
            'move_ids': self.account_move.ids
        })
        payment._compute_total_invoice_amount()
        self.assertEqual(payment.total_invoice_amount, 1.1500000000000001)

    def test_action_draft(self):
        self.payment.action_cancel()
        self.payment.action_draft()
        self.assertEqual(self.payment.amount, 0.0)
        self.assertEqual(self.payment.payment_line_ids.paid_amount, 0.0)

    def test_compute_payment_line_ids(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Product',
                'quantity': 1,
                'price_unit': 10.0,
                'account_id': self.env['account.account'].search([
                    ('account_type', '=', 'income')
                ], limit=1).id,
            })]
        })
        invoice.action_post()

        self.payment.action_post()
        invoice_receivable_line = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
        )

        payment_receivable_line = self.payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
        )
        # Manual reconciliation
        if invoice_receivable_line.debit > 0 and payment_receivable_line.credit > 0:
            reconcile = self.env['account.partial.reconcile'].create({
                'debit_move_id': invoice_receivable_line.id,
                'credit_move_id': payment_receivable_line.id,
                'amount': min(invoice_receivable_line.debit, payment_receivable_line.credit),
            })
        self.payment.reconciled_invoice_ids = invoice
        self.payment._compute_payment_line_ids()
        self.assertTrue(self.payment.payment_line_ids, "Should have payment lines")

    def test_onchange_partner_id(self):
        with self.assertRaises(UserError, msg='There are already some invoice '
                                              'lines.First remove the lines'):
            self.payment._onchange_partner_id()

    def test_payment_init(self):
        self.account_move.action_post()
        register_payment_id = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.account_move.ids).create({
            'payment_date': fields.Date.today(),
        })
        to_process = [{
            'create_vals': {'date': datetime.date(2024, 1, 5),
                            'amount': 22137.5, 'payment_type': 'inbound',
                            'partner_type': 'customer', 'ref': False,
                            'journal_id': 6, 'company_id': self.env.company.id,
                            'currency_id': self.env.company.currency_id.id,
                            'partner_id': self.partner.id,
                            },
            'to_reconcile': self.account_move.line_ids,
            'batch': {'lines': self.account_move.line_ids,
                      'payment_values': {'partner_id': 10, 'account_id': 6,
                                         'currency_id': 1,
                                         'partner_bank_id': False,
                                         'partner_type': 'customer',
                                         'payment_type': 'inbound'}}}]
        self.assertTrue(self.payment.payment_init(register_payment_id,
                                                  to_process, False))

    def test_payment_post(self):
        to_process = [{
            'create_vals': {'date': datetime.date(2024, 1, 5),
                            'amount': 22137.5, 'payment_type': 'inbound',
                            'partner_type': 'customer', 'ref': False,
                            'journal_id': 6, 'company_id': self.env.company.id,
                            'currency_id': self.env.company.currency_id.id,
                            'partner_id': self.partner.id,
                            },
            'to_reconcile': self.account_move.line_ids,
            'batch': {'lines': self.account_move.line_ids,
                      'payment_values': {'partner_id': 10, 'account_id': 6,
                                         'currency_id': 1,
                                         'partner_bank_id': False,
                                         'partner_type': 'customer',
                                         'payment_type': 'inbound'}}}]
        self.payment.payment_post(to_process, False)
        self.assertEqual(self.payment.state, 'posted')

    def test_action_confirm_invoice_payment(self):
        self.account_move._compute_fiscal_year_id()
        self.account_move.action_post()
        self.payment.action_confirm_invoice_payment()
        self.assertEqual(self.payment.move_ids.residual_amount, 0.0)
