# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import common


class TestCylloAccountingFiscalYear(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test partner'
        })
        cls.fiscal_year = cls.env['account.fiscal.year'].create({
            'name': 'Year1',
            'start_date': '2021-01-01',
            'end_date': '2021-12-31',
            'company_id': cls.env.company.id,
            'state': 'draft'
        })
        cls.fiscal_year2 = cls.env['account.fiscal.year'].create({
            'name': 'Year2',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': cls.env.company.id,
            'state': 'draft',
            'period_ids': [fields.Command.create({
                'name': 'period1',
                'start_date': '2026-01-01',
                'end_date': '2026-12-31',
                'state': 'open'
            })]
        })
        cls.fiscal_year3 = cls.env['account.fiscal.year'].create({
            'name': 'Year2',
            'start_date': '2022-01-01',
            'end_date': '2022-12-31',
            'company_id': cls.env.company.id,
            'state': 'draft',
            'period_ids': [fields.Command.create({
                'name': 'period1',
                'start_date': '2022-01-01',
                'end_date': '2022-12-31',
                'state': 'close'
            })]
        })
        cls.year_period = cls.env['account.fiscal.year.period'].create({
            'name': 'period1',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'state': 'open',
            'fiscal_year_id': cls.fiscal_year.id,
        })
        cls.year_period2 = cls.env['account.fiscal.year.period'].create({
            'name': 'period1',
            'start_date': '2021-01-01',
            'end_date': '2021-12-31',
            'state': 'open',
            'fiscal_year_id': cls.fiscal_year.id
        })
        cls.account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2021-10-05',
            'fiscal_year_id': cls.fiscal_year2.id,
            'period_id': cls.year_period2.id
        })
