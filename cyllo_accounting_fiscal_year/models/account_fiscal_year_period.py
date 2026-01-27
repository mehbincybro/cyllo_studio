# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountFiscalYearPeriod(models.Model):
    """For Account Fiscal Year Period"""
    _name = "account.fiscal.year.period"
    _inherit = ['mail.thread']
    _description = "Fiscal Year Period"

    sequence = fields.Integer(default=1)
    name = fields.Char(string='Period', tracking=True)
    start_date = fields.Date(string='From', required=True, tracking=True)
    end_date = fields.Date(string='To', required=True, tracking=True)
    fiscal_year_id = fields.Many2one('account.fiscal.year', tracking=True, required=True,
                                     help='fiscal year for the period')
    company_id = fields.Many2one('res.company', store=True, related='fiscal_year_id.company_id')
    state = fields.Selection(selection=[('open', 'Open'), ('close', 'Closed')], string='Status', readonly=True,
                             copy=False, tracking=True, default='open')

    def unlink(self):
        """OVERRIDE to unlink the record"""
        for rec in self:
            if rec.state == 'open':
                raise UserError(
                    _("You cannot delete a period in open state first close "
                      "the period.")
                )
        return super().unlink()

    def action_close(self):
        """Button: Close the period"""
        self.ensure_one()
        self.write({'state': 'close'})

    def action_reopen(self):
        """Button: Re-Open the period"""
        self.ensure_one()
        self.write({'state': 'open'})

    def action_close_periods(self):
        """Server action for close periods"""
        for rec in self:
            rec.write({'state': 'close'})

    def action_re_open_periods(self):
        """Server action for re-open periods"""
        for rec in self:
            rec.write({'state': 'open'})
