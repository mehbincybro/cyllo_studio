# -*- coding: utf-8 -*-
import datetime

from odoo import fields
from odoo.addons.cyllo_accounting.tests.common import TestCylloAccounting
from odoo.exceptions import UserError


class TestAccountAsset(TestCylloAccounting):

    def test_compute_cum_residual_amount(self):
        self.account_asset_asset._compute_cum_residual_amount()
        self.assertEqual(self.account_asset_asset.cum_residual_amount, 1000)

    def test_compute_original_value(self):
        with self.assertRaises(UserError, msg='All the lines must be posted'):
            self.env['account.asset.asset'].create({
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
                'currency_id': self.asset_type.currency_id.id,
                'date': fields.Date.today(),
                'first_recognition_date': fields.Date.today(),
                'total_value': 10000,
                'not_depreciable_value': 1000,
                'state': 'draft',
                'computation_method': 'no_prorata',
                'invoice_line_ids': self.account_move.line_ids.ids,
                'prorata_date': fields.Date.today(),
                'depreciation_move_ids': [fields.Command.create({
                    'move_type': 'out_invoice',
                    'partner_id': self.partner.id,
                    'invoice_date': '2020-01-10',
                    'asset_amount': 1000
                })]
            })
        self.account_asset_asset._compute_original_value()
        self.assertEqual(self.account_asset_asset.original_value, 100)

    def test_compute_purchase_value(self):
        with self.assertRaises(UserError):
            account_asset = self.env['account.asset.asset'].create({
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
                'currency_id': self.asset_type.currency_id.id,
                'date': fields.Date.today(),
                'first_recognition_date': fields.Date.today(),
                'total_value': 10000,
                'not_depreciable_value': 1000,
                'state': 'draft',
                'computation_method': 'no_prorata',
                'invoice_line_ids': self.account_move.line_ids.ids,
                'prorata_date': fields.Date.today(),
                'depreciation_move_ids': [fields.Command.create({
                    'move_type': 'out_invoice',
                    'partner_id': self.partner.id,
                    'invoice_date': '2020-01-10',
                    'asset_amount': 1000
                })]
            })
            account_asset._compute_purchase_value()

    def test_compute_residual_value(self):
        self.account_asset_asset._compute_residual_value()
        self.assertEqual(self.account_asset_asset.residual_value, 9000)
        self.account_asset_asset.depreciation_move_ids.action_post()
        self.account_asset_asset._compute_residual_value()
        self.assertEqual(self.account_asset_asset.residual_value, 8000)

    def test_compute_entries_count(self):
        self.account_asset_asset._compute_entries_count()
        self.assertEqual(self.account_asset_asset.entries_count, 1)
    
    def test_compute_asset_type(self):
        self.account_asset_asset._compute_asset_type()
        self.assertEqual(self.account_asset_asset.asset_type, 'revenue')
        
    def test_onchange_original_value(self):
        self.account_asset_asset._onchange_original_value()
        self.assertEqual(self.account_asset_asset.total_value, 100.0)
        with self.assertRaises(UserError):
            account_asset_asset = self.env['account.asset.asset'].create({
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
                'purchase_value': 1000,
                'currency_id': self.asset_type.currency_id.id,
                'date': fields.Date.today(),
                'first_recognition_date': fields.Date.today(),
                'total_value': 10000,
                'not_depreciable_value': 1000,
                'state': 'draft',
                'computation_method': 'no_prorata',
                'invoice_line_ids': self.account_move.line_ids.ids,
                'prorata_date': fields.Date.today(),
                'depreciation_move_ids': [fields.Command.create({
                    'move_type': 'out_invoice',
                    'partner_id': self.partner.id,
                    'invoice_date': '2020-01-10',
                    'asset_amount': 1000,
                    'state': 'draft',
                    'line_ids': [fields.Command.create({
                        'product_id': self.product_tem.id,
                    })],
                })]
            })
            account_asset_asset._onchange_original_value()

    def test_onchange_prorata_date(self):
        self.account_asset_asset._onchange_prorata_date()
        self.assertFalse(self.account_asset_asset.prorata_date)
        account_asset_asset = self.env['account.asset.asset'].create({
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
            'purchase_value': 1000,
            'currency_id': self.asset_type.currency_id.id,
            'date': fields.Date.today(),
            'first_recognition_date': fields.Date.today(),
            'total_value': 10000,
            'not_depreciable_value': 1000,
            'state': 'draft',
            'computation_method': 'constant_period',
            'invoice_line_ids': self.account_move.line_ids.ids,
            'prorata_date': fields.Date.today(),
            'depreciation_move_ids': [fields.Command.create({
                'move_type': 'out_invoice',
                'partner_id': self.partner.id,
                'invoice_date': '2020-01-10',
                'asset_amount': 1000,
                'state': 'draft',
                'line_ids': [fields.Command.create({
                    'product_id': self.product_tem.id,
                })],
            })]
        })
        account_asset_asset._onchange_prorata_date()
        self.assertEqual(account_asset_asset.prorata_date, fields.Date.today())
        
    def test_onchange_asset_type_id(self):
        self.account_asset_asset._onchange_asset_type_id()
        self.assertTrue(self.account_asset_asset.journal_id)
        self.assertTrue(self.account_asset_asset.account_id)
        self.assertTrue(self.account_asset_asset.expense_account_id)
        self.assertEqual(self.account_asset_asset.number_of_entries, 5)
        self.assertEqual(self.account_asset_asset.period, '1')
        self.assertEqual(self.account_asset_asset.computation_method,
                         'no_prorata')
    
    def test_compute_depreciation_amount(self):
        depreciation = {'asset_end_date': datetime.date(2024, 2, 29), 'asset_date': datetime.date(2024, 1, 31), 'days': 31}
        self.assertEqual(self.account_asset_asset.compute_depreciation_amount(depreciation, 180, 6), 1500.0)
        account_asset_asset = self.env['account.asset.asset'].create({
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
            'purchase_value': 1000,
            'currency_id': self.asset_type.currency_id.id,
            'date': fields.Date.today(),
            'first_recognition_date': fields.Date.today(),
            'total_value': 10000,
            'not_depreciable_value': 1000,
            'state': 'draft',
            'computation_method': 'daily_compute',
            'invoice_line_ids': self.account_move.line_ids.ids,
            'prorata_date': fields.Date.today(),
            'depreciation_move_ids': [fields.Command.create({
                'move_type': 'out_invoice',
                'partner_id': self.partner.id,
                'invoice_date': '2020-01-10',
                'asset_amount': 1000,
                'state': 'draft',
                'line_ids': [fields.Command.create({
                    'product_id': self.product_tem.id,
                })],
            })]
        })
        self.assertEqual(account_asset_asset.compute_depreciation_amount(depreciation, 180, 6), 1550.0)

    def test_compute_days(self):
        self.assertEqual(self.account_asset_asset.compute_days(False, fields.Date.today()), 31)
        account_asset_asset = self.env['account.asset.asset'].create({
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
            'purchase_value': 1000,
            'currency_id': self.asset_type.currency_id.id,
            'date': fields.Date.today(),
            'first_recognition_date': fields.Date.today(),
            'total_value': 10000,
            'not_depreciable_value': 1000,
            'state': 'draft',
            'computation_method': 'daily_compute',
            'invoice_line_ids': self.account_move.line_ids.ids,
            'prorata_date': fields.Date.today(),
            'depreciation_move_ids': [fields.Command.create({
                'move_type': 'out_invoice',
                'partner_id': self.partner.id,
                'invoice_date': '2020-01-10',
                'asset_amount': 1000,
                'state': 'draft',
                'line_ids': [fields.Command.create({
                    'product_id': self.product_tem.id,
                })],
            })]
        })
        self.assertEqual(
            account_asset_asset.compute_days(
                fields.Date.today(), fields.Date.today()), 1)

    def test_depreciation_board(self):
        self.assertEqual(self.account_asset_asset._depreciation_board(
            9000, 5, fields.Date.today())[0].name, '/')
        self.assertEqual(self.account_asset_asset._depreciation_board(
            9000, 5, fields.Date.today())[1].name, '/')
        self.assertEqual(self.account_asset_asset._depreciation_board(
            9000, 5, fields.Date.today())[2].name, '/')
        self.assertEqual(self.account_asset_asset._depreciation_board(
            9000, 5, fields.Date.today())[3].name, '/')
        self.assertEqual(self.account_asset_asset._depreciation_board(
            9000, 5, fields.Date.today())[4].name, '/')

    def test_compute_depreciation(self):
        self.assertEqual(self.account_asset_asset.compute_depreciation(
            9000, 5, fields.Date.today())[0].name, '/')
        self.assertEqual(self.account_asset_asset.compute_depreciation(
            9000, 5, fields.Date.today())[1].name, '/')
        self.assertEqual(self.account_asset_asset.compute_depreciation(
            9000, 5, fields.Date.today())[2].name, '/')
        self.assertEqual(self.account_asset_asset.compute_depreciation(
            9000, 5, fields.Date.today())[3].name, '/')
        self.assertEqual(self.account_asset_asset.compute_depreciation(
            9000, 5, fields.Date.today())[4].name, '/')

    def test_button_confirm(self):
        self.account_asset_asset.action_confirm()
        self.assertEqual(self.account_asset_asset.state, 'running')
        self.assertEqual(self.account_asset_asset.depreciation_move_ids.name,
                         'INV/2020/00001')

    def test_button_running(self):
        self.account_asset_asset.action_running()
        self.assertEqual(self.account_asset_asset.state, 'running')

    def test_unlink(self):
        res = self.account_asset_asset
        res = res.unlink()
        self.assertTrue(res)
        with self.assertRaises(UserError):
            account_asset_asset = self.env['account.asset.asset'].create({
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
                'purchase_value': 1000,
                'currency_id': self.asset_type.currency_id.id,
                'date': fields.Date.today(),
                'first_recognition_date': fields.Date.today(),
                'total_value': 10000,
                'not_depreciable_value': 1000,
                'state': 'running',
                'computation_method': 'daily_compute',
                'invoice_line_ids': self.account_move.line_ids.ids,
                'prorata_date': fields.Date.today(),
                'depreciation_move_ids': [fields.Command.create({
                    'move_type': 'out_invoice',
                    'partner_id': self.partner.id,
                    'invoice_date': '2020-01-10',
                    'asset_amount': 1000,
                    'state': 'draft',
                    'line_ids': [fields.Command.create({
                        'product_id': self.product_tem.id,
                    })],
                })]
            })
            account_asset_asset.unlink()
        with self.assertRaises(UserError):
            account_asset_asset2 = self.env['account.asset.asset'].create({
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
                'purchase_value': 1000,
                'currency_id': self.asset_type.currency_id.id,
                'date': fields.Date.today(),
                'first_recognition_date': fields.Date.today(),
                'total_value': 10000,
                'not_depreciable_value': 1000,
                'state': 'draft',
                'computation_method': 'daily_compute',
                'invoice_line_ids': self.account_move.line_ids.ids,
                'prorata_date': fields.Date.today(),
                'depreciation_move_ids': [fields.Command.create({
                    'move_type': 'out_invoice',
                    'partner_id': self.partner.id,
                    'invoice_date': '2020-01-10',
                    'asset_amount': 1000,
                    'state': 'draft',
                    'line_ids': [fields.Command.create({
                        'product_id': self.product_tem.id,
                    })],
                })]
            })
            account_asset_asset2.depreciation_move_ids.write({
                'state': 'posted'
            })
            account_asset_asset2.unlink()
    
    def test_button_save_template(self):
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'name'], 'Save Template')
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'res_model'], 'account.asset.type')
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'context']['default_type'], 'revenue')
        self.assertTrue(self.account_asset_asset.action_save_template()[
                            'context']['default_account_id'])
        self.assertTrue(self.account_asset_asset.action_save_template()[
                            'context']['default_expense_account_id'])
        self.assertTrue(self.account_asset_asset.action_save_template()[
                            'context']['default_journal_id'])
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'context']['default_number_of_entries'], 5)
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'context']['default_period'], '1')
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'context']['default_computation_method'],
                         'no_prorata')
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'context']['default_company_id'],
                         self.env.company.id)
        self.assertEqual(self.account_asset_asset.action_save_template()[
                             'context']['default_currency_id'],
                         self.env.company.currency_id.id)

    def test_action_get_entries(self):
        self.assertEqual(self.account_asset_asset.action_get_entries()['name'],
                         'Journal Entries')
        self.assertEqual(self.account_asset_asset.action_get_entries()[
                             'res_model'], 'account.move')
        self.assertDictEqual(self.account_asset_asset.action_get_entries()[
                                 'context'], {'create': False})
        self.assertEqual(self.account_asset_asset.action_get_entries()[
                             'view_mode'], 'tree,form')
        self.assertEqual(self.account_asset_asset.action_get_entries()[
                             'target'], 'current')
        self.assertEqual(self.account_asset_asset.action_get_entries()[
                             'domain'], [
            ('asset_id', '=', self.account_asset_asset.id)])
