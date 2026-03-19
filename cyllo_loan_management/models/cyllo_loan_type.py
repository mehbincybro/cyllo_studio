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
from odoo import fields, models


class CylloLoanType(models.Model):
    # -------------------------------------------------------------------------
    # Private attributes
    # -------------------------------------------------------------------------
    _name = 'cyllo.loan.type'
    _description = 'Loan Type'
    _order = 'sequence, name'

    # -------------------------------------------------------------------------
    # Fields declaration
    # -------------------------------------------------------------------------
    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    loan_direction = fields.Selection([
        ('both', 'Both (Giving & Taking)'),
        ('giving', 'Loan Giving (Lending)'),
        ('taking', 'Loan Taking (Borrowing)'),
    ], required=True, default='both')
    interest_type = fields.Selection([
        ('flat', 'Flat Rate'),
        ('reducing', 'Reducing Balance'),
    ], required=True, default='reducing', string='Default Interest Type')
    default_interest_rate = fields.Float(
        string='Default Interest Rate (%)',
        digits=(5, 4),
        default=0.0,
    )
    default_duration = fields.Integer(string='Default Duration (Months)', default=12)
    repayment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('bullet', 'Bullet (End of Term)'),
    ], required=True, default='monthly', string='Default Repayment Frequency')
    # Accounting accounts
    loan_account_id = fields.Many2one(
        'account.account',
        string='Loan Account',
        domain="[('account_type', 'in', ['asset_non_current', 'asset_current', 'liability_non_current', 'liability_current'])]",
        help='Balance sheet account for the loan principal.',
    )
    interest_income_account_id = fields.Many2one(
        'account.account',
        string='Interest Income Account',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='Account for interest income (loan giving).',
    )
    interest_expense_account_id = fields.Many2one(
        'account.account',
        string='Interest Expense Account',
        domain="[('account_type', '=', 'expense')]",
        help='Account for interest expense (loan taking).',
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Default Journal',
        domain="[('type', 'in', ['bank', 'cash', 'general'])]",
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Html(string='Terms & Conditions')
    loan_count = fields.Integer(compute='_compute_loan_count', string='Loans')

    # -------------------------------------------------------------------------
    # SQL constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'Loan type code must be unique per company!'),
    ]

    # -------------------------------------------------------------------------
    # Compute and search methods
    # -------------------------------------------------------------------------
    def _compute_loan_count(self):
        loan_data = self.env['cyllo.loan'].read_group(
            [('loan_type_id', 'in', self.ids)],
            ['loan_type_id'],
            ['loan_type_id'],
        )
        mapped_data = {d['loan_type_id'][0]: d['loan_type_id_count'] for d in loan_data}
        for record in self:
            record.loan_count = mapped_data.get(record.id, 0)

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_view_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Loans — {self.name}',
            'res_model': 'cyllo.loan',
            'view_mode': 'tree,form',
            'domain': [('loan_type_id', '=', self.id)],
            'context': {'default_loan_type_id': self.id},
        }
