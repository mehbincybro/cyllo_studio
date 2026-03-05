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
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountReturn(models.Model):
    """
    Account Return Model
    This model represents a tax return for a specific period.
    It computes tax amounts from posted journal items
    (account.move.line with tax_line_id)
    and creates a settlement journal entry.
    """

    _name = 'account.return'
    _description = 'Tax Return'
    _order = 'date_from desc'

    name = fields.Char(string="Reference", required=True, copy=False, default="New",
                       help="Unique reference for this tax return.")
    periodicity = fields.Selection([('monthly', 'Monthly'), ('bi_monthly', 'Every 2 months'),
                                    ('quarterly', 'Quarterly'), ('four_months', 'Every 4 months'),
                                    ('semi_annually', 'Semi-annually'), ('annually', 'Annually'),
                                    ('fiscal_year', 'Fiscal Year'), ], required=True,
                                   help="Defines how often the tax return is filed.")
    date_from = fields.Date(required=True, help="Start date of the tax return period.")
    date_to = fields.Date(required=True, help="End date of the tax return period.")
    journal_id = fields.Many2one('account.journal', string="Settlement Journal",
                                 domain="[('type','=','general')]", required=True,
                                 help="Journal used to create the tax settlement entry.")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True,
                                 help="Company for which this tax return is generated.")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True,
                                  help="Currency used for tax computation.")
    is_tax_return = fields.Boolean(default=True, help="Technical flag to identify tax return records.")
    output_tax = fields.Monetary(string="Output Tax", currency_field='currency_id', readonly=True,
                                 help="Total sales tax collected during the selected period.")
    input_tax = fields.Monetary(string="Input Tax", currency_field='currency_id', readonly=True,
                                help="Total purchase tax paid during the selected period.")
    net_tax = fields.Monetary(string="Net Tax", currency_field='currency_id', readonly=True,
                              help="Difference between Output Tax and Input Tax. If positive, tax is payable. "
                                   "If negative, tax is refundable.")
    move_id = fields.Many2one('account.move', string="Settlement Entry", readonly=True,
                              help="Journal entry created to settle this tax return.")
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')],
                             default='draft',help="Status of the tax return.")
    check_ids = fields.One2many('account.return.validation', 'return_id',
                                string="Validation Checks")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Ensure date range is valid."""
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from > rec.date_to:
                    raise UserError(_("Start date must be before end date."))

    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_overlap(self):
        """
        Prevent overlapping tax returns for the same company.
        """
        for rec in self:
            if not rec.date_from or not rec.date_to:
                continue
            domain = [('id', '!=', rec.id), ('company_id', '=', rec.company_id.id), ('state', '!=', 'cancel'),
                      ('date_from', '<=', rec.date_to), ('date_to', '>=', rec.date_from), ]
            overlapping = self.search(domain)
            if overlapping:
                raise UserError(_("Another tax return already exists for this period (%s - %s).") % (
                overlapping[0].date_from, overlapping[0].date_to))

    def action_compute(self):
        """
        Compute tax amounts from posted journal items.
        Only tax lines (tax_line_id) are considered.
        """

        self.ensure_one()

        lines = self.env['account.move.line'].search([('tax_line_id', '!=', False), ('move_id.state', '=', 'posted'),
                                                      ('date', '>=', self.date_from), ('date', '<=', self.date_to),
                                                      ('company_id', '=', self.company_id.id), ])

        output_tax = 0.0
        input_tax = 0.0

        for line in lines:

            tax_amount = line.credit - line.debit

            if line.tax_line_id.type_tax_use == 'sale':
                output_tax += tax_amount

            elif line.tax_line_id.type_tax_use == 'purchase':
                input_tax += tax_amount

        # Store positive values for display
        self.output_tax = abs(output_tax)
        self.input_tax = abs(input_tax)

        # Net = Output - Input (this matches Odoo)
        self.net_tax = self.output_tax - self.input_tax

    def action_validate_checks(self):
        """
        Run all related validation checks.
        """
        self.ensure_one()
        for check in self.check_ids:
            check.action_run_validation()

        failed_mandatory = self.check_ids.filtered(lambda c: c.state == 'failed' and c.is_mandatory)
        failed_optional = self.check_ids.filtered(lambda c: c.state == 'failed' and not c.is_mandatory)

        if failed_mandatory or failed_optional:
            messages = []
            if failed_mandatory:
                messages.append(_("Mandatory failures:\n%s") % "\n".join(
                    [f"- {c.name}: {c.result_message}" for c in failed_mandatory]))
            if failed_optional:
                messages.append(_("Optional warnings:\n%s") % "\n".join(
                    [f"- {c.name}: {c.result_message}" for c in failed_optional]))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Validation Results'),
                    'message': "\n\n".join(messages),
                    'sticky': True,
                    'type': 'danger' if failed_mandatory else 'warning',
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Validation Passed'),
                'message': _('All validation checks passed.'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_post(self):
        """
        Create and post settlement journal entry
        using Tax Group accounts (Payable / Receivable).
        """

        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_("Only draft returns can be posted."))

        # Validate checks before posting
        self.action_validate_checks()
        if any(check.state == 'failed' and check.is_mandatory for check in self.check_ids):
            raise UserError(
                _("Cannot post tax return because some mandatory validation checks failed. Please review the 'Validation Checks' tab."))

        # if not self.net_tax:
        #     raise UserError(_("Nothing to settle."))

        # Get first tax group (you can refine later per country/company)
        tax_group = self.env['account.tax.group'].search([], limit=1)

        if not tax_group:
            raise UserError(_("No Tax Group configured."))

        if not tax_group.tax_payable_account_id or not tax_group.tax_receivable_account_id:
            raise UserError(_("Please configure Payable and Receivable accounts in Tax Group."))

        amount = abs(self.net_tax)

        move_lines = []

        # CASE 1 → TAX PAYABLE
        if self.net_tax > 0:

            payable_account = tax_group.tax_payable_account_id

            move_lines = [
                # Credit Tax Payable
                (0, 0, {
                    'name': 'Tax Payable',
                    'account_id': payable_account.id,
                    'credit': amount,
                    'debit': 0.0,
                }),
                # Debit Settlement / Clearing (use journal default or same payable)
                (0, 0, {
                    'name': 'Tax Settlement',
                    'account_id': payable_account.id,
                    'debit': amount,
                    'credit': 0.0,
                }),
            ]
        # CASE 2 → TAX REFUND
        else:

            receivable_account = tax_group.tax_receivable_account_id

            move_lines = [
                # Debit Tax Receivable
                (0, 0, {
                    'name': 'Tax Refund Receivable',
                    'account_id': receivable_account.id,
                    'debit': amount,
                    'credit': 0.0,
                }),
                # Credit Settlement
                (0, 0, {
                    'name': 'Tax Settlement',
                    'account_id': receivable_account.id,
                    'credit': amount,
                    'debit': 0.0,
                }),
            ]

        move = self.env['account.move'].create({
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'company_id': self.company_id.id,
            'line_ids': move_lines,
        })

        move.action_post()

        self.move_id = move.id
        self.state = 'posted'

    def action_cancel(self):
        """
        Cancel the tax return and reverse settlement entry.
        """
        self.ensure_one()

        if self.move_id:
            self.move_id.button_draft()
            self.move_id.button_cancel()

        self.state = 'cancel'

    def action_open_tax_return_wizard(self):
        """
        Open the Tax Return Wizard from a button.
        """
        return {
            'name': _('Tax Return Generation Wizard'),
            'type': 'ir.actions.act_window',
            'res_model': 'tax.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def unlink(self):
        """
        Prevent deletion of posted returns.
        """
        for rec in self:
            if rec.state == 'posted':
                raise UserError(_("You cannot delete a posted tax return."))
        return super().unlink()
