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
from odoo.tests import common
import logging

_logger = logging.getLogger(__name__)


class TestAssetRepairLine(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAssetRepairLine, cls).setUpClass()

        cls.company = cls.env.company
        cls.currency = cls.env.ref('base.USD')

        # Partner & Employee
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'employee_C',
            'work_contact_id': cls.partner.id,
        })
        cls.asset_type = cls.env['asset.type'].create({
            'name': 'Test Asset Type',
            'company_id': cls.company.id,
        })
        cls.brand = cls.env['asset.brand'].create({'name': 'Test Brand'})

        # Accounts & Journal
        cls.account = cls.env['account.account'].create({
            'name': 'Test Account',
            'account_type': 'asset_current',
            'code': 'TestAccount',
            'reconcile': True,
        })
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'A',
        })
        cls.asset_item = cls.env['asset.item'].create({
            'name': 'Test Asset Item',
            'asset_type_id': cls.asset_type.id,
            'brand_id': cls.brand.id,
            'depreciation_method': 'straight_line',
            'method_duration': 5,
            'is_auto_calculate': True,
            'depreciating_factor': 0.2,
            'duration_period': 'year',
            'fixed_asset_account_id': cls.account.id,
            'asset_depreciation_account_id': cls.account.id,
            'asset_expense_account_id': cls.account.id,
            'asset_journal_id': cls.journal.id,
            'purchase_date': '2022-06-01',
        })

        # ⚡ Determine a valid computation_method dynamically
        selection_values = dict(cls.env['asset.asset']._fields['computation_method']._description_selection(cls.env))
        valid_computation_method = next(iter(selection_values.keys()))

        # Asset creation
        cls.asset_asset = cls.env['asset.asset'].create({
            'name': 'Test Asset',
            'asset_item_id': cls.asset_item.id,
            'date': fields.Date.today(),
            'company_id': cls.company.id,
            'original_value': 10000,
            'salvage_value': 1000,
            'status': 'draft',
            'depreciation_method': 'straight_line',
            'method_duration': 5,
            'duration_period': 'year',
            'currency_id': cls.currency.id,
            'is_reserve': True,
            'computation_method': valid_computation_method,  # ✅ dynamically valid
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'lst_price': 100.0,
            'uom_id': cls.env.ref('uom.product_uom_unit').id
        })

        # Repair
        cls.repair = cls.env['account.asset.repair'].create({
            'asset_id': cls.asset_asset.id,
            'issue': 'Test Issue',
            'employee_id': cls.employee.id,
            'company_id': cls.company.id,
            'scheduled_date': fields.Date.today(),
        })

        cls.repair_line = cls.env['asset.repair.line'].create({
            'repair_id': cls.repair.id,
            'product_id': cls.product.id,
            'product_qty': 2,
        })

    def test_compute_price_subtotal(self):
        _logger.info('Starts test_compute_price_subtotal')
        self.repair_line._compute_price_subtotal()
        expected_subtotal = self.repair_line.product_qty * self.product.lst_price
        self.assertEqual(
            self.repair_line.price_subtotal,
            expected_subtotal,
            "Subtotal computation is incorrect"
        )
        _logger.info('Ends test_compute_price_subtotal')
