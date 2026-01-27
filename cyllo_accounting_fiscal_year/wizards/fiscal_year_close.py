# -*- coding: utf-8 -*-
from odoo import fields, models


class FiscalYearClose(models.TransientModel):
    """Wizard for close fiscal period"""
    _name = 'fiscal.year.close'
    _description = 'Close fiscal year'

    all_periods = fields.Boolean(string="Close All Periods", help="It will close all the periods in the fiscal year")
    end_period_id = fields.Many2one(comodel_name="account.fiscal.year.period", string="Until this Period",
                                    help="Close until this Month Period")
    fiscal_year_id = fields.Many2one('account.fiscal.year', tracking=True, required=True,
                                     help='fiscal year for the period')

    def default_get(self, fields_list):
        """Default values to the wizard"""
        res = super(FiscalYearClose, self).default_get(fields_list)
        fiscal_year_id = self.env["account.fiscal.year"].browse(self._context.get("active_id"))
        if fiscal_year_id:
            res["fiscal_year_id"] = fiscal_year_id.id
        return res

    def action_close_fiscal_year(self):
        """Close fiscal year periods based on conditions"""
        self.ensure_one()
        active_id = self.env["account.fiscal.year"].browse(self._context.get("active_id"))
        if active_id:
            if self.all_periods:
                active_id.period_ids.write({'state': 'close'})
            else:
                period_ids = self.env["account.fiscal.year.period"].search(
                    [('end_date', '<=', self.end_period_id.end_date),
                     ('fiscal_year_id', '=', active_id.id)])
                if period_ids:
                    period_ids.write({'state': 'close'})
            if 'open' not in active_id.period_ids.mapped('state'):
                active_id.write({'state': 'close'})
