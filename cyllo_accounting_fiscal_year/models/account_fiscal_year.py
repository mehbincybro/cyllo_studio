# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12


class AccountFiscalYear(models.Model):
    """For Account Fiscal Year """
    _name = "account.fiscal.year"
    _description = "Account Fiscal Year"

    name = fields.Char(string='Fiscal Year', required=True, tracking=True, help='Name for the fiscal year')
    start_date = fields.Date(required=True, help='Start date for the fiscal year')
    end_date = fields.Date(required=True, help='End date for the fiscal year')
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    period_ids = fields.One2many('account.fiscal.year.period', 'fiscal_year_id',
                                 'Periods', tracking=True)
    state = fields.Selection(selection=[('draft', 'Draft'), ('open', 'Open'), ('close', 'Closed')], string='Status',
                             readonly=True, copy=False, tracking=True, default='draft')

    @api.constrains("start_date", "end_date", "company_id")
    def _check_start_date(self):
        """Check intersection with the existing fiscal years."""
        for fiscal_year in self:
            if fiscal_year.end_date < fiscal_year.start_date:
                raise UserError(_("The ending date must not be prior to the"
                                  " starting date."))
            domain = fiscal_year._get_domain()
            overlapping_fiscal_year = self.search(domain, limit=1)
            if overlapping_fiscal_year:
                raise UserError(
                    _("This fiscal year %s overlaps with %s.\n "
                      "Please correct the start and/or end dates of your "
                      "fiscal years.", fiscal_year.display_name,
                      overlapping_fiscal_year.display_name))

    def _get_domain(self):
        """Get domain for finding fiscal years overlapping with self"""
        self.ensure_one()
        # Compare with other fiscal years defined for this company
        company_domain = [
            ("id", "!=", self.id),
            ("company_id", "=", self.company_id.id),
        ]
        start_date = self.start_date
        end_date = self.end_date
        intersection_domain_from = [
            "&",
            ("start_date", "<=", start_date),
            ("end_date", ">=", start_date),
        ]
        intersection_domain_to = [
            "&",
            ("start_date", "<=", end_date),
            ("end_date", ">=", end_date),
        ]
        intersection_domain_contain = [
            "&",
            ("start_date", ">=", start_date),
            ("start_date", "<=", end_date),
        ]
        intersection_domain = expression.OR(
            [
                intersection_domain_from,
                intersection_domain_to,
                intersection_domain_contain,
            ]
        )
        return expression.AND(
            [
                company_domain,
                intersection_domain,
            ]
        )

    def unlink(self):
        """OVERRIDE to unlink the record"""
        for rec in self:
            if rec.state == 'open':
                raise UserError(
                    _("You cannot delete a fiscal year in open state first "
                      "close the fiscal year.")
                )
            else:
                for period in self.period_ids:
                    if period.state == 'open':
                        raise UserError(
                            _("You cannot delete a fiscal year if there is "
                              "open periods")
                        )
                    else:
                        period.unlink()
        res = super().unlink()
        return res

    def action_create_periods(self):
        """Button: Create periods for the Fiscal Year"""
        for rec in self:
            if rec.period_ids:
                raise UserError(
                    _("There are already periods for the fiscal year")
                )
            start_date = fields.Date.from_string(rec.start_date)
            end_date = fields.Date.from_string(rec.end_date)
            count = 1
            while start_date < end_date:
                date_month = start_date + relativedelta(months=1, days=-1)
                if date_month > end_date:
                    date_month = end_date
                self.env['account.fiscal.year.period'].create({
                    'sequence': count,
                    'name': '%02d/' % int(count) + start_date.strftime('%Y'),
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': date_month.strftime('%Y-%m-%d'),
                    'fiscal_year_id': rec.id,
                    'state': 'open'
                })
                start_date = start_date + relativedelta(months=1)
                count += 1
            rec.write({'state': 'open'})

    def action_reopen(self):
        """Button: Re-open the fiscal year"""
        self.ensure_one()
        self.period_ids.write({'state': 'open'})
        self.write({'state': 'open'})

    def action_draft(self):
        """Button: Set to Draft"""
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_open(self):
        """Button: Open the fiscal year"""
        for rec in self:
            if not rec.period_ids:
                rec.action_create_periods()
            else:
                rec.write({'state': 'open'})
