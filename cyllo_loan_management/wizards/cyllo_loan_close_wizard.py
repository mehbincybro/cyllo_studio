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


class CylloLoanCloseWizard(models.TransientModel):
    # -------------------------------------------------------------------------
    # Private attributes
    # -------------------------------------------------------------------------
    _name = 'cyllo.loan.close.wizard'
    _description = 'Loan Close / Settlement Wizard'

    # -------------------------------------------------------------------------
    # Fields declaration
    # -------------------------------------------------------------------------
    loan_id = fields.Many2one('cyllo.loan', required=True, ondelete='cascade')
    loan_name = fields.Char(related='loan_id.name', readonly=True)
    amount_remaining = fields.Monetary(
        related='loan_id.amount_remaining',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(related='loan_id.currency_id', readonly=True)
    close_date = fields.Date(required=True, default=fields.Date.today)
    close_type = fields.Selection([
        ('full_settlement', 'Full Settlement (All dues paid)'),
        ('early_closure', 'Early Closure (Prepayment)'),
        ('write_off', 'Write-Off (Bad Debt)'),
    ], required=True, default='full_settlement')
    waive_remaining = fields.Boolean(
        string='Waive Remaining Amount',
        default=False,
        help='Cancel remaining unpaid installments without creating accounting entries.',
    )
    journal_id = fields.Many2one(
        'account.journal',
        domain="[('type', 'in', ['bank', 'cash', 'general'])]",
    )
    notes = fields.Text(string='Closure Notes')

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_close_loan(self):
        self.ensure_one()
        loan = self.loan_id
        unpaid = loan.repayment_ids.filtered(lambda l: l.state not in ('paid',))

        if self.close_type == 'full_settlement':
            if unpaid:
                raise UserError(_(
                    'There are still %d unpaid installments. '
                    'Use "Early Closure" or waive the remaining amount.', len(unpaid)
                ))
        elif self.close_type in ('early_closure', 'write_off'):
            if self.waive_remaining:
                unpaid.write({'state': 'paid', 'amount_paid': unpaid.mapped('total_amount')[0] if len(unpaid) == 1 else 0})
                for line in unpaid:
                    line.write({'amount_paid': line.total_amount})
            else:
                unpaid.unlink()

        loan.write({'state': 'closed'})
        loan.message_post(
            body=_(
                'Loan closed — Type: %s. %s',
                dict(self._fields['close_type'].selection).get(self.close_type),
                self.notes or '',
            )
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cyllo.loan',
            'res_id': loan.id,
            'view_mode': 'form',
        }
