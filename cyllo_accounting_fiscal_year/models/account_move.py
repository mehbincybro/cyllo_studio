# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError


class AccountMove(models.Model):
    """Inheriting account.move for adding new functionalities"""
    _inherit = 'account.move'

    fiscal_year_id = fields.Many2one('account.fiscal.year', tracking=True,
                                     compute='_compute_fiscal_year_id', help='The invoice date within the fiscal year')
    period_id = fields.Many2one('account.fiscal.year.period', tracking=True,
                                compute='_compute_fiscal_year_id',
                                help='The invoice date within the fiscal year')

    def _compute_fiscal_year_id(self):
        """Compute period and fiscal year based on invoice date"""
        for rec in self:
            if rec.date:
                rec.fiscal_year_id = False
                rec.period_id = False
                fiscal_year_id = self.env['account.fiscal.year'].sudo().with_context(
                    company_id=rec.company_id.id).search(
                    [('start_date', '<=', rec.date),
                     ('end_date', '>=', rec.date),
                     ('company_id', '=', rec.company_id.id)], limit=1)
                if fiscal_year_id:
                    period_id = self.env['account.fiscal.year.period'].sudo().with_context(
                        company_id=rec.company_id.id).search(
                        [('start_date', '<=', rec.date),
                         ('end_date', '>=', rec.date),
                         ('fiscal_year_id', '=', fiscal_year_id.id)], limit=1)
                    rec.period_id = period_id if period_id else False
                    rec.fiscal_year_id = fiscal_year_id

    def _check_fiscalyear_lock_date(self):
        """Check the date is within the fiscal year period"""
        res = super(AccountMove, self)._check_fiscalyear_lock_date()
        if res:
            for rec in self:
                fiscal_year_id = rec.fiscal_year_id
                period_id = rec.period_id
                if not fiscal_year_id:
                    action = self.env.ref(
                        'cyllo_accounting_fiscal_year.action_view_fiscal_years')
                    raise RedirectWarning(
                        message=(_(
                            'The Date %s Must Be Within a Fiscal Year '
                            'Period') % rec.date),
                        action=action.id,
                        button_text=_("Create Fiscal Year"),
                    )
                elif fiscal_year_id.state == 'open':
                    if not period_id:
                        action = self.env.ref('cyllo_accounting_fiscal_year.action_view_periods')
                        raise RedirectWarning(
                            message=(_('The Date %s Must Be Within a Fiscal '
                                       'Year Period') % rec.date),
                            action=action.id,
                            button_text=_("Create Period"),
                        )
                    elif period_id.state == 'close':
                        raise UserError(_('The Fiscal year period is already '
                                          'closed'))
                    else:
                        return True
                else:
                    raise UserError(
                        _('First Open the Fiscal Year'))
        else:
            return res
