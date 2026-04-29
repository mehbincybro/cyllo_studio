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
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class LoanRepayment(models.Model):
    # -------------------------------------------------------------------------
    # Private attributes
    # -------------------------------------------------------------------------
    _name = 'loan.repayment'
    _description = 'Loan Repayment Installment'
    _order = 'loan_id, sequence'

    # -------------------------------------------------------------------------
    # Fields declaration
    # -------------------------------------------------------------------------
    loan_id = fields.Many2one(
        'loan.loan',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=1)
    name = fields.Char(
        compute='_compute_name',
        store=True,
        string='Installment',
    )
    due_date = fields.Date(required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Scheduled'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ], default='draft', required=True, tracking=True, copy=False)
    # Amounts
    principal_amount = fields.Monetary(
        required=True,
    )
    interest_amount = fields.Monetary(required=True)
    penalty_amount = fields.Monetary(
        default=0.0,
        help='Late payment penalty applied to this installment.',
    )
    total_amount = fields.Monetary(
        compute='_compute_total_amount',
        store=True,
        string='Total Due',
    )
    amount_paid = fields.Monetary(
        default=0.0,
        copy=False,
    )
    amount_remaining = fields.Monetary(
        compute='_compute_amount_remaining',
        store=True,
    )
    days_overdue = fields.Integer(compute='_compute_days_overdue', store=False)
    # Accounting links
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice / Bill',
        readonly=True,
        copy=False,
        domain="[('move_type', 'in', ['out_invoice', 'in_invoice'])]",
    )
    payment_date = fields.Date(string='Payment Date', copy=False, tracking=True)
    # Related / convenience
    currency_id = fields.Many2one('res.currency', related='loan_id.currency_id', store=True)
    partner_id = fields.Many2one('res.partner', related='loan_id.partner_id', store=True)
    loan_direction = fields.Selection(related='loan_id.loan_direction', store=True)
    company_id = fields.Many2one('res.company',related='loan_id.company_id', store=True)
    notes = fields.Char(string='Notes')

    # -------------------------------------------------------------------------
    # SQL constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        ('principal_positive', 'CHECK(principal_amount >= 0)',
         'Principal amount cannot be negative!'),
        ('interest_non_negative', 'CHECK(interest_amount >= 0)',
         'Interest amount cannot be negative!'),
        ('amount_paid_non_negative', 'CHECK(amount_paid >= 0)', 'Amount paid cannot be negative!'),
    ]

    # -------------------------------------------------------------------------
    # Compute and search methods
    # -------------------------------------------------------------------------
    @api.depends('loan_id.name', 'sequence')
    def _compute_name(self):
        for record in self:
            record.name = _('Installment #%s — %s', record.sequence, record.loan_id.name)

    @api.depends('principal_amount', 'interest_amount', 'penalty_amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.principal_amount + record.interest_amount + record.penalty_amount

    @api.depends('total_amount', 'amount_paid')
    def _compute_amount_remaining(self):
        for record in self:
            record.amount_remaining = record.total_amount - record.amount_paid

    def _compute_days_overdue(self):
        today = fields.Date.today()
        for record in self:
            if record.state == 'overdue' and record.due_date:
                record.days_overdue = (today - record.due_date).days
            else:
                record.days_overdue = 0

    # -------------------------------------------------------------------------
    # Constraints and onchanges
    # -------------------------------------------------------------------------
    @api.constrains('amount_paid', 'total_amount')
    def _check_amount_paid(self):
        for record in self:
            if record.amount_paid > record.total_amount:
                raise ValidationError(_(
                    'Amount paid (%s) cannot exceed total due (%s) for installment #%s.',
                    record.amount_paid, record.total_amount, record.sequence,
                ))

    # -------------------------------------------------------------------------
    # CRUD methods
    # -------------------------------------------------------------------------
    def unlink(self):
        for record in self:
            if record.state not in ('draft',):
                raise UserError(_(
                    'Cannot delete installment #%s: it is already posted or paid.', record.sequence
                ))
        return super().unlink()

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_post(self):
        """Post the installment — generate invoice/bill and journal entry."""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only scheduled installments can be posted.'))
            if record.loan_id.state not in ('disbursed', 'running'):
                raise UserError(_('Loan must be disbursed before posting installments.'))
            if not record.partner_id.property_account_receivable_id:
                raise UserError(_('Partner must have receivable account.'))
            record._generate_invoice()
            record.write({'state': 'posted'})

    def action_register_payment(self):
        """Open payment register wizard for this installment."""
        self.ensure_one()
        if self.state not in ('posted', 'overdue'):
            raise UserError(_('Only posted or overdue installments can be paid.'))
            
        account_type = 'asset_receivable' if self.loan_direction == 'giving' else 'liability_payable'

        outstanding_lines = self.invoice_id.line_ids.filtered(
            lambda l: l.account_id.account_type == account_type
                and not l.reconciled
                and l.partner_id
                and l.account_id not in [self.loan_id.loan_account_id,
                                         self.loan_id.interest_account_id]
        )

        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move.line',
                'active_ids': outstanding_lines.ids,
                'loan_id': self.loan_id.id,
                'loan_repayment_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_mark_overdue(self):
        """Mark overdue installments (called by scheduled action)."""
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'posted'),
            ('due_date', '<', today),
        ])
        overdue.write({'state': 'overdue'})

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice / Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_view_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------
    def _generate_invoice(self):
        """Generate customer invoice (loan giving) or vendor bill (loan taking)."""
        self.ensure_one()
        loan = self.loan_id
        is_giving = loan.loan_direction == 'giving'

        # Build repayment lines
        lines = []

        total = self.principal_amount + self.interest_amount + self.penalty_amount

        # Debit
        lines.append((0, 0, {
            'name': f"Installment #{self.sequence}",
            'partner_id': loan.partner_id.id,
            'account_id': loan.partner_id.property_account_receivable_id.id if is_giving
            else loan.partner_id.property_account_payable_id.id,
            'debit': total if is_giving else 0.0,
            'credit': 0.0 if is_giving else total,
        }))

        if self.principal_amount:
            lines.append((0, 0, {
                'name': f"Principal #{self.sequence}",
                'account_id': loan.loan_account_id.id,
                'credit': self.principal_amount if is_giving else 0.0,
                'debit': 0.0 if is_giving else self.principal_amount,
            }))

        if self.interest_amount:
            lines.append((0, 0, {
                'name': f"Interest #{self.sequence}",
                'account_id': loan.interest_account_id.id,
                'credit': self.interest_amount if is_giving else 0.0,
                'debit': 0.0 if is_giving else self.interest_amount,
            }))

        if self.penalty_amount:
            lines.append((0, 0, {
                'name': f"Penalty #{self.sequence}",
                'account_id': loan.interest_account_id.id,
                'credit': self.penalty_amount if is_giving else 0.0,
                'debit': 0.0 if is_giving else self.penalty_amount,
            }))

        repayment_vals = {
            'move_type': 'entry',
            'partner_id': loan.partner_id.id,
            'invoice_date': self.due_date,
            'invoice_date_due': self.due_date,
            'ref': _('%s — Installment #%s', loan.name, self.sequence),
            'currency_id': loan.currency_id.id,
            'invoice_line_ids': lines,
        }

        repayment = self.env['account.move'].create(repayment_vals)
        repayment.action_post()

        # Link to loan invoice_ids
        loan.invoice_ids = [(4, repayment.id)]
        self.invoice_id = repayment
        return repayment

    def _post_repayment_entry(self):
        """Post the repayment journal entry when payment is received/made."""
        self.ensure_one()
        loan = self.loan_id
        partner = loan.partner_id
        journal = loan.journal_id

        if not journal.default_account_id:
            raise UserError(_(
                'Journal "%s" does not have a default account. Please configure it.', journal.name
            ))

        if loan.loan_direction == 'giving':
            # Dr Bank/Cash (principal)  Dr Interest Income
            # Cr Loan Receivable (principal)  Cr Bank (interest)
            # Simplified: Dr Bank  /  Cr Loan Receivable + Cr Interest Income
            line_ids = [
                (0, 0, {
                    'name': _('Repayment received — %s #%s', loan.name, self.sequence),
                    'account_id': journal.default_account_id.id,
                    'debit': self.total_amount,
                    'credit': 0.0,
                    'partner_id': partner.id,
                }),
                (0, 0, {
                    'name': _('Principal repayment — %s #%s', loan.name, self.sequence),
                    'account_id': loan.loan_account_id.id,
                    'debit': 0.0,
                    'credit': self.principal_amount,
                    'partner_id': partner.id,
                }),
                (0, 0, {
                    'name': _('Interest income — %s #%s', loan.name, self.sequence),
                    'account_id': loan.interest_account_id.id,
                    'debit': 0.0,
                    'credit': self.interest_amount + self.penalty_amount,
                    'partner_id': partner.id,
                }),
            ]
        else:
            # Loan taking — Dr Loan Payable + Dr Interest Expense  /  Cr Bank
            line_ids = [
                (0, 0, {
                    'name': _('Principal repayment — %s #%s', loan.name, self.sequence),
                    'account_id': loan.loan_account_id.id,
                    'debit': self.principal_amount,
                    'credit': 0.0,
                    'partner_id': partner.id,
                }),
                (0, 0, {
                    'name': _('Interest expense — %s #%s', loan.name, self.sequence),
                    'account_id': loan.interest_account_id.id,
                    'debit': self.interest_amount + self.penalty_amount,
                    'credit': 0.0,
                    'partner_id': partner.id,
                }),
                (0, 0, {
                    'name': _('Repayment paid — %s #%s', loan.name, self.sequence),
                    'account_id': journal.default_account_id.id,
                    'debit': 0.0,
                    'credit': self.total_amount,
                    'partner_id': partner.id,
                }),
            ]

        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': _('%s — Installment #%s repayment', loan.name, self.sequence),
            'line_ids': line_ids,
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.move_id = move
        return move
