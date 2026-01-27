# -*- coding: utf-8 -*-
import datetime

from odoo import fields
from odoo.addons.cyllo_accounting.tests.common import TestCylloAccounting
from odoo.exceptions import UserError


class TestAccountMove(TestCylloAccounting):

    def test_compute_asset_amount(self):
        self.account_move._compute_asset_amount()
        self.assertEqual(self.account_move.total_residual, 0)

    def test_compute_asset_ids(self):
        with self.assertRaises(UserError):
            account_move2 = self.env['account.move'].create({
                'partner_id': self.partner.id,
                'move_type': 'out_invoice',
                'state': 'draft',
                'invoice_date': '2023-12-05',
                'residual_amount': 1000,
                'asset_amount': 10000,
                'asset_id': self.account_asset_asset.id,
                'line_ids': [fields.Command.create({
                    'product_id': self.product_tem.id,
                    'asset_ids': self.account_asset_asset.ids
                })],
            })
            account_move2._compute_asset_ids()
            self.assertTrue(account_move2.asset_ids)
            self.assertGreaterEqual(account_move2.asset_count, 1)
            self.assertEqual(account_move2.asset_type, 'revenue')
            
    def test_onchange_amount_residual(self):
        self.account_move._onchange_amount_residual()
        self.assertGreaterEqual(self.account_move.residual_amount, 1.15)

    def test_prepare_moves(self):
        vals = {'amount': 1000,
                'asset_id': self.account_asset_asset,
                'asset_date': datetime.date(2024, 1, 31),
                'date': datetime.date(2024, 1, 31),
                'asset_end_date': datetime.date(2024, 2, 29),
                'asset_days': 31}
        self.assertEqual(self.account_move._prepare_moves(vals)[
                             'asset_days'], 31)
        self.assertEqual(self.account_move._prepare_moves(vals)[
                             'asset_amount'], 1000)
        self.assertEqual(self.account_move._prepare_moves(vals)[
                             'move_type'], 'entry')

    def test_create_asset_moves(self):
        account_move2 = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2023-12-05',
            'amount_residual': 1000,
            'line_ids': [fields.Command.create({
                'product_id': self.product_tem.id,
                'name': False,
                'amount_residual_currency': 1000,
                'asset': 1
            })],
        })
        with self.assertRaises(UserError):
            account_move2.create_asset_moves()

    def test_post(self):
        self.assertTrue(self.account_move._post(True))
        
    def test_button_draft(self):
        account_move2 = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2023-12-05',
            'amount_residual': 1000,
            'line_ids': [fields.Command.create({
                'product_id': self.product_tem.id,
                'name': False,
                'amount_residual_currency': 1000,
                'asset': 1
            })],
            'asset_ids': [fields.Command.create({
                'name': 'Test Asset',
                'active': True,
                'asset_type_id': self.asset_type.id,
                'company_id': self.env.company.id,
                'asset_type': self.asset_type.type,
                'journal_id': self.asset_type.journal_id.id,
                'account_id': self.asset_type.account_id.id,
                'expense_account_id': self.asset_type.expense_account_id.id,
                'number_of_entries': 5,
                'period': '1',
                'original_value': 100,
                'currency_id': self.asset_type.currency_id.id,
                'date': fields.Date.today(),
                'first_recognition_date': fields.Date.today(),
                'total_value': 10000,
                'not_depreciable_value': 1000,
                'state': 'running',
                'computation_method': 'no_prorata',
                'prorata_date': fields.Date.today(),
            })]
        })
        account_move2.button_cancel()
        account_move2.button_draft()
