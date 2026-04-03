# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CylloLoan(models.Model):
    # -------------------------------------------------------------------------
    # Private attributes
    # -------------------------------------------------------------------------
    _name = 'cyllo.loan'
    _description = 'Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, name'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    # Fields declaration
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Loan Reference',
        required=True,
        copy=False,
        readonly=True,
        default='/',
        tracking=True,
    )
    loan_direction = fields.Selection([
        ('giving', 'Loan Giving (We Lend)'),
        ('taking', 'Loan Taking (We Borrow)'),
    ], required=True, default='giving', tracking=True,
        help='Giving: we are the lender. Taking: we are the borrower.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('disbursed', 'Disbursed'),
        ('running', 'Running'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)
    loan_type_id = fields.Many2one(
        'cyllo.loan.type',
        required=True,
        tracking=True,
        ondelete='restrict',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Counterpart',
        required=True,
        tracking=True,
        ondelete='restrict',
        help='Borrower when giving a loan; Lender when taking a loan.',
    )
    partner_type_label = fields.Char(compute='_compute_partner_type_label', string='Partner Label')
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    # Loan terms
    principal_amount = fields.Monetary(
        string='Principal Amount',
        required=True,
        tracking=True,
        currency_field='currency_id',
    )
    interest_type = fields.Selection([
        ('flat', 'Flat Rate'),
        ('reducing', 'Reducing Balance'),
    ], required=True, default='reducing', tracking=True)
    interest_rate = fields.Float(
        string='Annual Interest Rate (%)',
        digits=(5, 4),
        required=True,
        tracking=True,
    )
    repayment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('bullet', 'Bullet (End of Term)'),
    ], required=True, default='monthly', tracking=True)
    duration = fields.Integer(
        string='Duration (Months)',
        required=True,
        default=12,
        tracking=True,
    )
    date_start = fields.Date(
        string='Disbursement Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    date_end = fields.Date(
        string='Maturity Date',
        compute='_compute_date_end',
        store=True,
        readonly=False,
        tracking=True,
    )
    # Accounting
    journal_id = fields.Many2one(
        'account.journal',
        string='Disbursement Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash', 'general'])]",
        tracking=True,
    )
    loan_account_id = fields.Many2one(
        'account.account',
        string='Loan Account',
        required=True,
        tracking=True,
        help='Balance-sheet account that tracks the principal outstanding.',
    )
    interest_account_id = fields.Many2one(
        'account.account',
        string='Interest Account',
        required=True,
        tracking=True,
        help='Income account (loan giving) or Expense account (loan taking).',
    )
    disburse_move_id = fields.Many2one(
        'account.move',
        string='Disbursement Entry',
        readonly=True,
        copy=False,
    )
    # Repayment
    repayment_ids = fields.One2many(
        'cyllo.loan.repayment',
        'loan_id',
        string='Repayment Schedule',
        copy=False,
    )
    # Entries relation
    invoice_ids = fields.Many2many(
        'account.move',
        'cyllo_loan_invoice_rel',
        'loan_id',
        'move_id',
        string='Invoices / Bills',
        copy=False,
    )
    # Computed summaries
    total_interest = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
        string='Total Interest',
    )
    total_repayment = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
        string='Total Repayment (P+I)',
    )
    amount_paid = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    amount_remaining = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    installment_count = fields.Integer(compute='_compute_totals', store=True)
    paid_installment_count = fields.Integer(compute='_compute_totals', store=True)
    overdue_installment_count = fields.Integer(compute='_compute_totals', store=True)
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoices')
    move_count = fields.Integer(compute='_compute_move_count', string='Journal Entries')
    notes = fields.Html(string='Internal Notes')

    # -------------------------------------------------------------------------
    # SQL constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        ('principal_positive', 'CHECK(principal_amount > 0)', 'Principal amount must be positive!'),
        ('duration_positive', 'CHECK(duration > 0)', 'Duration must be at least 1 month!'),
        ('interest_rate_positive', 'CHECK(interest_rate >= 0)', 'Interest rate cannot be negative!'),
    ]

    # -------------------------------------------------------------------------
    # Default methods
    # -------------------------------------------------------------------------
    def _default_name(self):
        return self.env['ir.sequence'].next_by_code('cyllo.loan') or '/'

    # -------------------------------------------------------------------------
    # Compute and search methods
    # -------------------------------------------------------------------------
    @api.depends('loan_direction')
    def _compute_partner_type_label(self):
        for record in self:
            record.partner_type_label = _('Borrower') if record.loan_direction == 'giving' else _('Lender')

    @api.depends('date_start', 'duration')
    def _compute_date_end(self):
        for record in self:
            if record.date_start and record.duration:
                record.date_end = record.date_start + relativedelta(months=record.duration)
            else:
                record.date_end = False

    @api.depends(
        'repayment_ids.principal_amount',
        'repayment_ids.interest_amount',
        'repayment_ids.amount_paid',
        'repayment_ids.state',
    )
    def _compute_totals(self):
        for record in self:
            lines = record.repayment_ids
            record.total_interest = sum(lines.mapped('interest_amount'))
            record.total_repayment = sum(lines.mapped('total_amount'))
            record.amount_paid = sum(lines.mapped('amount_paid'))
            record.amount_remaining = record.total_repayment - record.amount_paid
            record.installment_count = len(lines)
            record.paid_installment_count = len(lines.filtered(lambda l: l.state == 'paid'))
            record.overdue_installment_count = len(lines.filtered(lambda l: l.state == 'overdue'))

    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    def _compute_move_count(self):
        for record in self:
            move_ids = record.repayment_ids.mapped('move_id').ids
            if record.disburse_move_id:
                move_ids.append(record.disburse_move_id.id)
            if record.invoice_ids:
                move_ids += record.invoice_ids.ids
            record.move_count = len(move_ids)

    # -------------------------------------------------------------------------
    # Constraints and onchanges
    # -------------------------------------------------------------------------
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start >= record.date_end:
                raise ValidationError(_('Maturity date must be after disbursement date.'))

    @api.onchange('loan_type_id')
    def _onchange_loan_type_id(self):
        if self.loan_type_id:
            loan_type = self.loan_type_id
            if loan_type.default_interest_rate:
                self.interest_rate = loan_type.default_interest_rate
            if loan_type.default_duration:
                self.duration = loan_type.default_duration
            if loan_type.repayment_frequency:
                self.repayment_frequency = loan_type.repayment_frequency
            if loan_type.interest_type:
                self.interest_type = loan_type.interest_type
            if loan_type.journal_id:
                self.journal_id = loan_type.journal_id
            if loan_type.loan_account_id:
                self.loan_account_id = loan_type.loan_account_id
            if self.loan_direction == 'giving' and loan_type.interest_income_account_id:
                self.interest_account_id = loan_type.interest_income_account_id
            elif self.loan_direction == 'taking' and loan_type.interest_expense_account_id:
                self.interest_account_id = loan_type.interest_expense_account_id

    @api.onchange('loan_direction')
    def _onchange_loan_direction(self):
        if self.loan_type_id:
            self._onchange_loan_type_id()

    # -------------------------------------------------------------------------
    # CRUD methods
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('cyllo.loan') or '/'
        return super().create(vals_list)

    def unlink(self):
        for record in self:
            if record.state not in ('draft', 'cancelled'):
                raise UserError(_('Only draft or cancelled loans can be deleted.'))
        return super().unlink()

    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': '/',
            'state': 'draft',
            'disburse_move_id': False,
            'repayment_ids': [],
            'invoice_ids': [(5, 0, 0)],
        })
        return super().copy(default)

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_approve(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft loans can be approved.'))
            record.write({'state': 'approved'})
            record.message_post(body=_('Loan approved.'))

    def action_disburse(self):
        """Open disbursement wizard."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved loans can be disbursed.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Disburse Loan'),
            'res_model': 'cyllo.loan.disburse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_loan_id': self.id},
        }

    def action_cancel(self):
        for record in self:
            if record.state in ('closed', 'cancelled'):
                raise UserError(_('Cannot cancel a closed or already cancelled loan.'))
            if record.disburse_move_id:
                raise UserError(_(
                    'Cannot cancel loan %s: disbursement journal entry exists. '
                    'Please reverse the entry first.', record.name
                ))
            record.write({'state': 'cancelled'})
            record.message_post(body=_('Loan cancelled.'))

    def action_reset_to_draft(self):
        for record in self:
            if record.state != 'cancelled':
                raise UserError(_('Only cancelled loans can be reset to draft.'))
            record.write({'state': 'draft'})
            record.message_post(body=_('Loan reset to draft.'))

    def action_close(self):
        """Open close wizard for early closure or final settlement."""
        self.ensure_one()
        if self.state != 'running':
            raise UserError(_('Only running loans can be closed.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Close Loan'),
            'res_model': 'cyllo.loan.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_loan_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        move_type = 'out_invoice' if self.loan_direction == 'giving' else 'in_invoice'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices / Bills'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {
                'default_move_type': move_type,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_view_moves(self):
        self.ensure_one()
        move_ids = self.repayment_ids.mapped('move_id').ids
        if self.disburse_move_id:
            move_ids.append(self.disburse_move_id.id)
        if self.invoice_ids:
            move_ids += self.invoice_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', list(move_ids))],
        }

    def action_generate_schedule(self):
        """Generate or regenerate the repayment schedule."""
        for record in self:
            if record.state not in ('draft', 'approved'):
                raise UserError(_(
                    'Repayment schedule can only be generated for draft or approved loans.'
                ))
            if record.repayment_ids.filtered(lambda l: l.state != 'draft'):
                raise UserError(_(
                    'Cannot regenerate schedule: some installments are already paid or posted.'
                ))
            record.repayment_ids.unlink()
            record._generate_repayment_schedule()

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------
    def _get_frequency_months(self):
        """Return the number of months between installments."""
        self.ensure_one()
        return {
            'monthly': 1,
            'quarterly': 3,
            'semi_annual': 6,
            'annual': 12,
            'bullet': self.duration,
        }.get(self.repayment_frequency, 1)

    def _generate_repayment_schedule(self):
        """Compute and create repayment schedule lines."""
        self.ensure_one()
        frequency_months = self._get_frequency_months()
        number_of_installments = (
            1 if self.repayment_frequency == 'bullet'
            else self.duration // frequency_months
        )
        if number_of_installments < 1:
            number_of_installments = 1

        lines = []
        if self.interest_type == 'flat':
            lines = self._compute_flat_schedule(number_of_installments, frequency_months)
        else:
            lines = self._compute_reducing_schedule(number_of_installments, frequency_months)

        self.env['cyllo.loan.repayment'].create(lines)

    def _compute_flat_schedule(self, num_installments, freq_months):
        """Flat rate: interest = principal × rate × (duration/12) spread equally."""
        self.ensure_one()
        periodic_rate = (self.interest_rate / 100) * (freq_months / 12)
        total_interest = self.principal_amount * periodic_rate * num_installments
        principal_per = round(self.principal_amount / num_installments, 2)
        interest_per = round(total_interest / num_installments, 2)

        # Adjust last installment for rounding differences
        principal_last = self.principal_amount - principal_per * (num_installments - 1)
        interest_last = total_interest - interest_per * (num_installments - 1)

        lines = []
        for i in range(num_installments):
            due_date = self.date_start + relativedelta(months=freq_months * (i + 1))
            p = principal_last if i == num_installments - 1 else principal_per
            n = interest_last if i == num_installments - 1 else interest_per
            lines.append({
                'loan_id': self.id,
                'sequence': i + 1,
                'due_date': due_date,
                'principal_amount': round(p, 2),
                'interest_amount': round(n, 2),
            })
        return lines

    def _compute_reducing_schedule(self, num_installments, freq_months):
        """Reducing balance (EMI): equal total installment, decreasing interest."""
        self.ensure_one()
        periodic_rate = (self.interest_rate / 100) * (freq_months / 12)
        principal = self.principal_amount

        if periodic_rate == 0:
            emi = principal / num_installments
        else:
            emi = principal * periodic_rate * (1 + periodic_rate) ** num_installments / (
                    (1 + periodic_rate) ** num_installments - 1
            )
        emi = round(emi, 2)

        lines = []
        balance = principal
        for i in range(num_installments):
            due_date = self.date_start + relativedelta(months=freq_months * (i + 1))
            interest = round(balance * periodic_rate, 2)
            principal_part = round(emi - interest, 2)
            # Last installment: close any floating point residual
            if i == num_installments - 1:
                principal_part = round(balance, 2)
                interest = round(emi - principal_part, 2) if emi > principal_part else 0.0
            balance = round(balance - principal_part, 2)
            lines.append({
                'loan_id': self.id,
                'sequence': i + 1,
                'due_date': due_date,
                'principal_amount': principal_part,
                'interest_amount': max(interest, 0.0),
            })
        return lines

    def _create_disbursement_entry(self, journal_id, date):
        """Create the disbursement journal entry and post it."""
        self.ensure_one()
        partner = self.partner_id
        if self.loan_direction == 'giving':
            # Dr Loan Receivable  /  Cr Bank/Cash
            debit_account = self.loan_account_id
            credit_account = journal_id.default_account_id
        else:
            # Dr Bank/Cash  /  Cr Loan Payable
            debit_account = journal_id.default_account_id
            credit_account = self.loan_account_id

        if not debit_account or not credit_account:
            raise UserError(_(
                'Journal "%s" does not have a default account configured. '
                'Please configure it before disbursing.', journal_id.name
            ))

        move_vals = {
            'move_type': 'entry',
            'journal_id': journal_id.id,
            'date': date,
            'ref': _('Loan Disbursement: %s', self.name),
            'line_ids': [
                (0, 0, {
                    'name': _('Loan Disbursement — %s', self.name),
                    'account_id': debit_account.id,
                    'debit': self.principal_amount,
                    'credit': 0.0,
                    'partner_id': partner.id,
                }),
                (0, 0, {
                    'name': _('Loan Disbursement — %s', self.name),
                    'account_id': credit_account.id,
                    'debit': 0.0,
                    'credit': self.principal_amount,
                    'partner_id': partner.id,
                }),
            ],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.disburse_move_id = move
        self.message_post(
            body=_('Loan disbursed. Journal entry: <a href="#">%s</a>', move.name)
        )
        return move

    def _check_running_state(self):
        """Update loan to 'closed' if all installments are paid."""
        self.ensure_one()
        if self.state == 'running':
            unpaid = self.repayment_ids.filtered(lambda l: l.state != 'paid')
            if not unpaid:
                self.write({'state': 'closed'})
                self.message_post(body=_('All installments paid. Loan closed.'))
