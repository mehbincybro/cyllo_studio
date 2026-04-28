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
from odoo import fields, models, _
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
    )
    notes = fields.Text(string='Closure Notes')

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_close_loan(self):
        self.ensure_one()
        loan = self.loan_id
        unpaid = loan.repayment_ids.filtered(lambda l: l.state not in ('paid', 'posted'))
        remaining_principal_amount = sum(unpaid.mapped('principal_amount'))
        penalty_amount = sum(unpaid.mapped('penalty_amount'))

        if self.waive_remaining:
            unpaid.write({
                'state': 'paid',
                'amount_paid': unpaid.mapped('total_amount')[0] if len(unpaid) == 1 else 0
            })
            for line in unpaid:
                line.write({'amount_paid': line.total_amount})
        else:
            loan.repayment_ids.create({
                'sequence': unpaid[0].sequence,
                'due_date': fields.date.today(),
                'principal_amount': round(remaining_principal_amount, 2),
                'interest_amount': round(
                    loan.amount_remaining - remaining_principal_amount, 2
                ) if not self.is_interest_needed else 0,
                'penalty_amount': penalty_amount if not self.is_penalty_needed else 0,
            })

            unpaid.unlink()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loan.loan',
            'res_id': loan.id,
            'view_mode': 'form',
        }
