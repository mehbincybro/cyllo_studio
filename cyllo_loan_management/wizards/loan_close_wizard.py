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
from odoo import Command, fields, models, _
from odoo.exceptions import UserError


class LoanCloseWizard(models.TransientModel):
    # -------------------------------------------------------------------------
    # Private attributes
    # -------------------------------------------------------------------------
    _name = 'loan.close.wizard'
    _description = 'Loan Close / Settlement Wizard'

    # -------------------------------------------------------------------------
    # Fields declaration
    # -------------------------------------------------------------------------
    loan_id = fields.Many2one('loan.loan', required=True, ondelete='cascade')
    loan_name = fields.Char(related='loan_id.name', readonly=True)
    amount_remaining = fields.Monetary(
        related='loan_id.amount_remaining',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(related='loan_id.currency_id', readonly=True)
    close_date = fields.Date(required=True, default=fields.Date.today)
    waive_remaining = fields.Boolean(
        string='Waive Remaining Amount',
        default=False,
        help='Cancel remaining unpaid installments without creating accounting entries.',
    )
    is_interest_needed = fields.Boolean(
        string='Pay Interest Amount',
        default=True,
        help='If enabled, pending interest should be paid while closing loan.',
    )
    is_penalty_needed = fields.Boolean(
        string='Pay Penalty Amount',
        default=True,
        help='If enabled, penalty should be paid while closing loan.',
    )
    account_id = fields.Many2one(
        'account.account',
        string='Loss account',
        help='Loss account to record pending amount in principle amount.'
    )
    notes = fields.Text(string='Closure Notes')

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_close_loan(self):
        self.ensure_one()
        loan = self.loan_id
        if loan.repayment_ids.filtered(
                lambda l: l.state in ('posted') and l.invoice_id.state in ('posted')):
            raise UserError(_('You have unpaid posted repayments, either reset'
                              ' those entries or complete the payments to close'))
        loan.repayment_ids.filtered(lambda l: l.state in ('posted')).write({
            'state': 'draft',
        })
        unpaid = loan.repayment_ids.filtered(lambda l: l.state not in ('paid'))
        remaining_principal_amount = sum(unpaid.mapped('principal_amount'))
        penalty_amount = sum(unpaid.mapped('penalty_amount'))
        is_giving = loan.loan_direction == 'giving'
        success_message = 'No pending payments.'

        if self.waive_remaining and unpaid:
            loss_entry_lines = [Command.create({
                                    'name': f"Writing Off #{loan.name}",
                                    'partner_id': loan.partner_id.id,
                                    'account_id': loan.loan_account_id.id,
                                    'debit': 0.0 if is_giving else remaining_principal_amount,
                                    'credit': remaining_principal_amount if is_giving else 0.0,
                                }), Command.create({
                                    'name': f"Loss entry of #{loan.name}",
                                    'account_id': self.account_id.id,
                                    'debit': remaining_principal_amount if is_giving else 0.0,
                                    'credit': 0.0 if is_giving else remaining_principal_amount,
                                })]

            loss_entry_vals = {
                'move_type': 'entry',
                'partner_id': loan.partner_id.id,
                'date': fields.Date.today(),
                'ref': _('%s — Waiving off pending amount as loss', loan.name),
                'currency_id': loan.currency_id.id,
                'journal_id': loan.journal_id.id,
                'invoice_line_ids': loss_entry_lines,
            }

            repayment = self.env['account.move'].create(loss_entry_vals)
            repayment.action_post()

            # Link to loan invoice_ids
            loan.waive_off_move_id = repayment
            unpaid.unlink()
            loan.state = 'closed'
            success_message = 'Loan closed with pending amount written off.'

        elif unpaid:
            loan.repayment_ids.create({
                'sequence': unpaid[0].sequence,
                'due_date': fields.Date.today(),
                'principal_amount': round(remaining_principal_amount, 2),
                'interest_amount': round(
                    loan.amount_remaining - remaining_principal_amount, 2
                ) if self.is_interest_needed else 0,
                'penalty_amount': penalty_amount if self.is_penalty_needed else 0,
            })

            unpaid.unlink()
            success_message = 'Pending amount is available in repayments to close at once.'
        loan.message_post(body=f'Loan closing procedure completed. {success_message}')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _(f'Loan {loan.name}'),
                'message': _(success_message),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window_close',
                }
            }
        }
