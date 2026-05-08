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
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class LoanType(models.Model):
    # -------------------------------------------------------------------------
    # Private attributes
    # -------------------------------------------------------------------------
    _name = 'loan.type'
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
    reducing_type = fields.Selection([
        ('fixed_emi', 'Fixed EMI'),
        ('fixed_tenure', 'Fixed Tenure'),
    ], string='Reducing Term Adjust', default='fixed_emi',
        help='How to adjust schedule when extra principal is paid.')
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
    # Accounting accountsOnline
    loan_taken_account_id = fields.Many2one(
        'account.account',
        string='Loan Taken Account',
        domain="[('account_type', 'in', ['liability_non_current', 'liability_current'])]",
        help='Balance sheet account for the loan principal when taking a loan.',
        default=lambda self: self.env.ref('cyllo_loan_management.account_loan_payable',
                                          raise_if_not_found=False),
    )
    loan_given_account_id = fields.Many2one(
        'account.account',
        string='Loan Given Account',
        domain="[('account_type', 'in', ['asset_non_current', 'asset_current'])]",
        help='Balance sheet account for the loan principal when giving a loan.',
        default=lambda self: self.env.ref('cyllo_loan_management.account_loan_receivable',
                                          raise_if_not_found=False),
    )
    interest_income_account_id = fields.Many2one(
        'account.account',
        string='Interest Income Account',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='Account for interest income (loan giving).',
        default=lambda self: self.env.ref('cyllo_loan_management.account_interest_income',
                                          raise_if_not_found=False),
    )
    interest_expense_account_id = fields.Many2one(
        'account.account',
        string='Interest Expense Account',
        domain="[('account_type', '=', 'expense')]",
        help='Account for interest expense (loan taking).',
        default=lambda self: self.env.ref('cyllo_loan_management.account_interest_expense',
                                          raise_if_not_found=False),
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Default Journal',
        domain="[('type', 'in', ['bank', 'cash', 'general'])]",
        default=lambda self: self.env.ref('cyllo_loan_management.loan_journal',
                                          raise_if_not_found=False),
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Html(string='Terms & Conditions')
    penalty_ids = fields.Many2many(
        'loan.penalty',
        string='Penalty Rules',
        help='Penalty rules applied when repayments are overdue.',
    )
    loan_count = fields.Integer(compute='_compute_loan_count', string='Loans')

    # -------------------------------------------------------------------------
    # SQL constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'Loan type code must be unique per company!'),
    ]

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains('penalty_ids')
    def _check_penalty_conflict(self):
        for loan_type in self:
            penalties = loan_type.penalty_ids
            if not penalties:
                continue
            # Build list of (days_from, days_to_effective) tuples
            ranges = []
            for penalty in penalties:
                day_to = penalty.days_to if penalty.days_to != 0 else float('inf')
                ranges.append((penalty.days_from, day_to, penalty.name))
            # Sort by days_from
            ranges.sort(key=lambda range_item: range_item[0])
            # Check for overlaps between consecutive ranges
            for index in range(len(ranges) - 1):
                a_from, a_to, a_name = ranges[index]
                b_from, b_to, b_name = ranges[index + 1]
                if b_from <= a_to:
                    raise ValidationError(_(
                        'Penalty rules "%s" (days %s–%s) and "%s" (days %s–%s) '
                        'have overlapping day ranges. Please resolve the conflict.',
                        a_name,
                        int(a_from),
                        int(a_to) if a_to != float('inf') else '∞',
                        b_name,
                        int(b_from),
                        int(b_to) if b_to != float('inf') else '∞',
                    ))

    # -------------------------------------------------------------------------
    # Compute and search methods
    # -------------------------------------------------------------------------
    def _compute_loan_count(self):
        loan_data = self.env['loan.loan'].read_group(
            [('loan_type_id', 'in', self.ids)],
            ['loan_type_id'],
            ['loan_type_id'],
        )
        mapped_data = {data['loan_type_id'][0]: data['loan_type_id_count'] for data in loan_data}
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
            'res_model': 'loan.loan',
            'view_mode': 'tree,form',
            'domain': [('loan_type_id', '=', self.id)],
            'context': {'default_loan_type_id': self.id},
        }
