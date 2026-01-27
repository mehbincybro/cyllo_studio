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
from odoo import fields
from odoo.addons.cyllo_accounting.tests.common import TestCylloAccounting


class TestAccountMoveLine(TestCylloAccounting):

    def test_compute_move_asset_type(self):
        account_move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2023-12-05',
            'amount_residual': 1000,
            'line_ids': [fields.Command.create({
                'product_id': self.product_tem.id,
                'amount_residual_currency': 1000,
                'asset': 1,
                'multi_invoice_payment': False,
                'asset_type_id': self.asset_type.id,
                'asset_ids': self.account_asset_asset.ids,
                'move_type': 'out_invoice',
                'move_id': self.account_move.id
            })],
        })
        account_move.line_ids._compute_move_asset_type()
        self.assertEqual(account_move.line_ids[0].move_asset_type, 'revenue')
        account_move2 = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'in_invoice',
            'state': 'draft',
            'invoice_date': '2023-12-05',
            'amount_residual': 1000,
            'line_ids': [fields.Command.create({
                'product_id': self.product_tem.id,
                'amount_residual_currency': 1000,
                'asset': 1,
                'multi_invoice_payment': False,
                'asset_type_id': self.asset_type.id,
                'asset_ids': self.account_asset_asset.ids,
                'move_type': 'out_invoice',
                'move_id': self.account_move.id
            })],
        })
        account_move2.line_ids._compute_move_asset_type()
        self.assertEqual(account_move2.line_ids[0].move_asset_type, 'expense')
