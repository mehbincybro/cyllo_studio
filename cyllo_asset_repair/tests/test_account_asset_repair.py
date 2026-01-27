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
import logging

from odoo import fields
from odoo.tests import common
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TestAccountAssetRepair(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.currency = cls.env.ref('base.USD')

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })
        cls.employee3 = cls.env['hr.employee'].create({
            'name': 'employee_C',
            'work_contact_id': cls.partner.id,
        })
        cls.asset_type = cls.env['asset.type'].create({
            'name': 'Test Asset Type',
            'company_id': cls.company.id,
        })

        cls.brand = cls.env['asset.brand'].create({
            'name': 'Test Brand',
        })
        cls.account = cls.env['account.account'].create({
            'name': 'Test Account',
            'account_type': 'asset_current',
            'code': 'TESTASSET',
            'reconcile': True,
        })
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'TJR',
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
        cls.asset_asset = cls.env['asset.asset'].create({
            'name': 'Test Asset',
            'asset_item_id': cls.asset_item.id,
            'date': fields.Date.today(),
            'company_id': cls.company.id,
            'original_value': 10000,
            'salvage_value': 1000,
            'status': 'draft',

            # REQUIRED FIELD (was missing)
            'computation_method': 'straight_line',

            'depreciation_method': 'straight_line',
            'method_duration': 5,
            'duration_period': 'year',
            'currency_id': cls.currency.id,
            'is_reserve': True,
        })
        cls.lease = cls.env['asset.lease'].create({
            'asset_id': cls.asset_asset.id,
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'customer_id': cls.partner.id,
            'company_id': cls.company.id,
            'lease_amount': 20000,
            'status': 'lease',
        })
        cls.assign = cls.env['asset.assign'].create({
            'asset_id': cls.asset_asset.id,
            'assign_date': fields.Date.today(),
            'employee_id': cls.employee3.id,
            'company_id': cls.company.id,
            'status': 'assign',
        })
        cls.rental = cls.env['asset.rental'].create({
            'asset_id': cls.asset_asset.id,
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'customer_id': cls.partner.id,
            'company_id': cls.company.id,
            'payment_terms': 'month',
            'payment_type': 'complete',
            'status': 'rent',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee'
        })

        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'partner_id': cls.partner.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Young Tom',
        })
        cls.repair_group = cls.env.ref('cyllo_asset_repair.group_cyllo_asset_repair')
        cls.repair_group.users = [(4, cls.user.id)]
        cls.repair = cls.env['account.asset.repair'].create({
            'asset_id': cls.asset_asset.id,
            'issue': 'Test Issue',
            'employee_id': cls.employee.id,
            'company_id': cls.company.id,
            'scheduled_date': fields.Date.today(),
        })
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner.id,
            'currency_id': cls.currency.id,
            'ref': cls.asset_asset.name,
            'repair_id': cls.repair.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': cls.product.id,
                    'price_unit': 24.02,
                    'tax_ids': [],
                })
            ],
        })
