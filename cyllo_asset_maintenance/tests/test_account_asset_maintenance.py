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
from odoo.exceptions import UserError
from datetime import timedelta


class TestAccountAssetMaintenance(common.TransactionCase):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(TestAccountAssetMaintenance, cls).setUpClass()
        cls.currency = cls.env.ref('base.USD')
        cls.company = cls.env.company
        cls.company_data = cls.setup_company_data(
            'company_1_data', chart_template=chart_template_ref)

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
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

        cls.account_asset_asset = cls.env['asset.asset'].create({
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
            'computation_method': 'no_prorata',
            'currency_id': cls.currency.id,
            'is_reserve': True,
        })
        cls.account_asset_asset2 = cls.env['asset.asset'].create({
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
            'computation_method': 'no_prorata',
            'currency_id': cls.currency.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })
        cls.employee2 = cls.env['hr.employee'].create({
            'name': 'Test Employee2',
        })
        cls.employee3 = cls.env['hr.employee'].create({
            'name': 'employee_C',
            'work_contact_id': cls.partner.id,
        })
        cls.employee4 = cls.env['hr.employee'].create({
            'name': 'Test Employee4',
        })

        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'partner_id': cls.partner.id,
        })

        cls.maintenance_group = cls.env.ref('cyllo_asset_maintenance.group_cyllo_asset_maintenance')
        cls.maintenance_group.users = [(4, cls.user.id)]

        cls.reservation = cls.env['asset.reservation'].create({
            'asset_id': cls.account_asset_asset.id,
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'employee_id': cls.employee2.id,
            'company_id': cls.company.id,
            'status': 'reserve',
        })

        cls.lease = cls.env['asset.lease'].create({
            'asset_id': cls.account_asset_asset.id,
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'customer_id': cls.partner.id,
            'company_id': cls.company.id,
            'lease_amount': 20000,
            'status': 'lease',
        })
        cls.assign = cls.env['asset.assign'].create({
            'asset_id': cls.account_asset_asset.id,
            'assign_date': fields.Date.today(),
            'employee_id': cls.employee4.id,
            'company_id': cls.company.id,
            'status': 'assign',
        })

        cls.rental = cls.env['asset.rental'].create({
            'asset_id': cls.account_asset_asset.id,
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'customer_id': cls.partner.id,
            'company_id': cls.company.id,
            'payment_terms': 'month',
            'payment_type': 'complete',
            'status': 'rent',
        })

        cls.maintenance = cls.env['account.asset.maintenance'].create({
            'asset_id': cls.account_asset_asset.id,
            'issue': 'Test Maintenance Issue',
            'scheduled_date': fields.Date.today(),
            'employee_id': cls.employee.id,
        })

    def test_get_maintenance_user(self):
        domain = self.maintenance.get_maintenance_user()
        self.assertIn(('id', 'in', self.maintenance_group.users.ids), domain)

    def test_onchange_scheduled_date(self):
        self.asset_item.purchase_date = self.maintenance.scheduled_date + timedelta(days=1)
        with self.assertRaises(UserError):
            self.maintenance._onchange_scheduled_date()

    def test_onchange_asset_id(self):
        self.maintenance._onchange_asset_id()
        self.assertEqual(self.maintenance.employee_id, self.reservation.employee_id)
        self.account_asset_asset.is_reserve = False
        self.account_asset_asset.is_lease = True
        self.maintenance._onchange_asset_id()
        self.assertEqual(self.maintenance.employee_id.work_contact_id, self.lease.customer_id)
        self.account_asset_asset.is_reserve = False
        self.account_asset_asset.is_lease = False
        self.account_asset_asset.is_assign = True
        self.maintenance._onchange_asset_id()
        self.assertEqual(self.maintenance.employee_id, self.assign.employee_id)
        self.account_asset_asset.is_reserve = False
        self.account_asset_asset.is_lease = False
        self.account_asset_asset.is_assign = False
        self.account_asset_asset.is_rental = True
        self.maintenance._onchange_asset_id()
        self.assertEqual(self.maintenance.employee_id.work_contact_id, self.rental.customer_id)
        self.account_asset_asset.is_reserve = False
        self.account_asset_asset.is_lease = False
        self.account_asset_asset.is_assign = False
        self.account_asset_asset.is_rental = False
        self.assertEqual(self.maintenance.employee_id.work_contact_id, self.user.partner_id)

    def test_action_confirm(self):
        self.maintenance.action_confirm()
        self.assertEqual(self.maintenance.status, 'confirm')
        self.assertEqual(self.maintenance.asset_id.is_maintenance, True)

    def test_action_start_maintenance(self):
        self.maintenance.action_start_maintenance()
        self.assertEqual(self.maintenance.status, 'ongoing')

    def test_action_done(self):
        self.maintenance.action_done()
        self.assertEqual(self.maintenance.status, 'done')
        self.assertEqual(self.maintenance.asset_id.is_maintenance, False)

    def test_unlink(self):
        self.maintenance.status = 'confirm'
        with self.assertRaises(UserError):
            self.maintenance.unlink()
        self.maintenance.status = 'ongoing'
        with self.assertRaises(UserError):
            self.maintenance.unlink()

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        """Create a new company having the name passed as parameter. A chart
        of accounts will be installed to this company: the same as the current
        company one. The current user will get access to this company.
        :param chart_template: The chart template is to be used in this new
         company.
        :param company_name: The name of the company.
        :return: A dictionary will be returned containing all relevant
         accounting data for testing.
        """
        company = cls.env.company
        cls.env.user.company_ids |= company
        # Install the chart template
        chart_template = chart_template or cls.env[
            'account.chart.template']._guess_chart_template(company.country_id)
        cls.env['account.chart.template'].try_loading(chart_template,
                                                      company=company,
                                                      install_demo=False)
        if not company.account_fiscal_country_id:
            company.account_fiscal_country_id = cls.env.ref('base.us')
        # The currency could be different after the installation of the chart
        # template.
        if kwargs.get('currency_id'):
            company.write({'currency_id': kwargs['currency_id']})
        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'income'),
                ('id', '!=',
                 company.account_journal_early_pay_discount_gain_account_id.id)
            ], limit=1),
            'default_account_expense': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'expense'),
                ('id', '!=',
                 company.account_journal_early_pay_discount_loss_account_id.id)
            ], limit=1),
            'default_account_receivable': cls.env['ir.property'].with_company(
                company)._get(
                'property_account_receivable_id', 'res.partner'),
            'default_account_payable': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'liability_payable')], limit=1),
            'default_account_assets': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'asset_fixed')], limit=1),
            'default_account_deferred_expense': cls.env[
                'account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'asset_current')], limit=1),
            'default_account_deferred_revenue': cls.env[
                'account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'liability_current')], limit=1),
            'default_account_tax_sale': company.account_sale_tax_id.mapped(
                'invoice_repartition_line_ids.account_id'),
            'default_account_tax_purchase': company.account_purchase_tax_id.mapped(
                'invoice_repartition_line_ids.account_id'),
            'default_journal_misc': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'general')], limit=1),
            'default_journal_sale': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'sale')], limit=1),
            'default_journal_purchase': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'purchase')], limit=1),
            'default_journal_bank': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'bank')], limit=1),
            'default_journal_cash': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'cash')], limit=1),
            'default_tax_sale': company.account_sale_tax_id,
            'default_tax_purchase': company.account_purchase_tax_id,
        }
