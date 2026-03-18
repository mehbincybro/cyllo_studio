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
from odoo import api, fields, models

class CylloLoanDisburseWizard(models.TransientModel):
    # -------------------------------------------------------------------------
    # Private attributes
    # -------------------------------------------------------------------------
    _name = 'cyllo.loan.disburse.wizard'
    _description = 'Loan Disbursement Wizard'

    # -------------------------------------------------------------------------
    # Fields declaration
    # -------------------------------------------------------------------------
    loan_id = fields.Many2one('cyllo.loan', required=True, ondelete='cascade')
    loan_name = fields.Char(related='loan_id.name', readonly=True)
    partner_id = fields.Many2one(related='loan_id.partner_id', readonly=True)
    principal_amount = fields.Monetary(
        related='loan_id.principal_amount',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(related='loan_id.currency_id', readonly=True)
    disbursement_date = fields.Date(required=True, default=fields.Date.today)
    journal_id = fields.Many2one(
        'account.journal',
        string='Disbursement Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash', 'general'])]",
    )
    generate_schedule = fields.Boolean(
        string='Generate Repayment Schedule',
        default=True,
        help='Automatically generate the repayment schedule upon disbursement.',
    )
    notes = fields.Text(string='Remarks')

    # -------------------------------------------------------------------------
    # Onchanges
    # -------------------------------------------------------------------------
    @api.onchange('loan_id')
    def _onchange_loan_id(self):
        if self.loan_id and self.loan_id.journal_id:
            self.journal_id = self.loan_id.journal_id

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_disburse(self):
        self.ensure_one()
        loan = self.loan_id

        # Create disbursement accounting entry
        loan._create_disbursement_entry(self.journal_id, self.disbursement_date)

        # Update loan journal to the one used
        loan.journal_id = self.journal_id
        loan.date_start = self.disbursement_date

        # Generate repayment schedule if requested
        if self.generate_schedule:
            if loan.repayment_ids:
                loan.repayment_ids.filtered(lambda l: l.state == 'draft').unlink()
            loan._generate_repayment_schedule()

        loan.write({'state': 'disbursed'})
        # Transition immediately to running if schedule generated
        if loan.repayment_ids:
            loan.write({'state': 'running'})

        if self.notes:
            loan.message_post(body=self.notes)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cyllo.loan',
            'res_id': loan.id,
            'view_mode': 'form',
        }
