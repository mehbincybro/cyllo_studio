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

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsuranceUnderwritingRule(models.Model):
    """
    Defines an underwriting rule used to assess risk for insurance policies.

    Each rule represents a single risk parameter that, when triggered,
    routes the policy to 'under_review' for manual admin approval instead
    of auto-approving it.
    """
    _name = 'cyllo.insurance.underwriting.rule'
    _description = 'Underwriting Rule'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'sequence, id'

    name = fields.Char(
        required=True,
        tracking=True,
        help="Descriptive name for this underwriting rule.",
    )
    sequence = fields.Integer(
        default=10,
        help="Determines the order in which rules are evaluated.",
    )
    active = fields.Boolean(
        default=True,
        help="Inactive rules are skipped during risk assessment.",
    )
    description = fields.Text(
        help="Detailed description of this rule and its intent.",
    )

    # ── Plan scoping ────────────────────────────────────────────────────────
    plan_ids = fields.Many2many(
        'insurance.plan',
        string="Applicable Plans",
        help="Leave empty to apply this rule to ALL plans. "
             "Set plans to restrict the rule to specific plans only.",
    )

    # ── Rule type ────────────────────────────────────────────────────────────
    rule_type = fields.Selection(
        selection=[
            ('max_age', 'Maximum Applicant Age'),
            ('max_coverage', 'Maximum Coverage Limit'),
            ('min_premium', 'Minimum Premium Amount'),
            ('severe_accident_history', 'Severe Accident / Claim History'),
            ('claim_frequency', 'High Claim Frequency'),
            ('high_risk_incident', 'High-Risk Incident Type'),
        ],
        required=True,
        default='max_age',
        tracking=True,
        help="The type of risk criterion this rule checks.",
    )

    # ── Threshold values (only one will be active depending on rule_type) ───
    max_age = fields.Integer(
        string="Maximum Age (years)",
        default=65,
        help="Trigger review if the insured person's age exceeds this value. "
             "Used when rule_type = 'max_age'.",
    )
    max_coverage_amount = fields.Monetary(
        string="Maximum Coverage Limit",
        currency_field='currency_id',
        help="Trigger review if the requested coverage limit exceeds this value. "
             "Used when rule_type = 'max_coverage'.",
    )
    min_premium_amount = fields.Monetary(
        string="Minimum Premium Amount",
        currency_field='currency_id',
        help="Trigger review if the policy premium is below this threshold. "
             "Used when rule_type = 'min_premium'.",
    )
    max_approved_claims = fields.Integer(
        string="Max Approved/Paid Claims",
        default=3,
        help="Trigger review if the insured has more than this many approved or paid "
             "claims across all policies. Used when rule_type = 'severe_accident_history'.",
    )
    max_claims_in_period = fields.Integer(
        string="Max Claims in Period",
        default=2,
        help="Trigger review if the insured filed more than this many claims "
             "within the lookback period. Used when rule_type = 'claim_frequency'.",
    )
    claim_period_months = fields.Integer(
        string="Lookback Period (months)",
        default=12,
        help="Number of months to look back when checking claim frequency.",
    )
    high_risk_incident_ids = fields.Many2many(
        'insurance.incident.type',
        string="High-Risk Incident Types",
        help="Trigger review if any of these incident types appear in the insured's "
             "claim history. Used when rule_type = 'high_risk_incident'.",
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ── Constraints ──────────────────────────────────────────────────────────

    @api.constrains('max_age')
    def _check_max_age(self):
        for rec in self:
            if rec.rule_type == 'max_age' and rec.max_age <= 0:
                raise ValidationError("Maximum age must be a positive integer.")

    @api.constrains('max_coverage_amount')
    def _check_max_coverage(self):
        for rec in self:
            if rec.rule_type == 'max_coverage' and rec.max_coverage_amount <= 0:
                raise ValidationError("Maximum coverage amount must be greater than zero.")

    @api.constrains('min_premium_amount')
    def _check_min_premium(self):
        for rec in self:
            if rec.rule_type == 'min_premium' and rec.min_premium_amount <= 0:
                raise ValidationError("Minimum premium amount must be greater than zero.")

    @api.constrains('max_approved_claims')
    def _check_max_approved_claims(self):
        for rec in self:
            if rec.rule_type == 'severe_accident_history' and rec.max_approved_claims < 0:
                raise ValidationError("Max approved claims cannot be negative.")

    @api.constrains('max_claims_in_period', 'claim_period_months')
    def _check_claim_frequency(self):
        for rec in self:
            if rec.rule_type == 'claim_frequency':
                if rec.max_claims_in_period < 0:
                    raise ValidationError("Max claims in period cannot be negative.")
                if rec.claim_period_months <= 0:
                    raise ValidationError("Lookback period must be at least 1 month.")

    # ── Business logic ───────────────────────────────────────────────────────

    def evaluate(self, policy):
        """
        Evaluate this rule against the given policy record.

        Returns:
            (bool, str): A tuple of (is_triggered, reason_message).
                         is_triggered = True  → policy should go to under_review.
                         is_triggered = False → this rule is satisfied / not applicable.
        """
        self.ensure_one()

        # If the rule is scoped to specific plans, skip for other plans.
        if self.plan_ids and policy.plan_id not in self.plan_ids:
            return False, ''

        if self.rule_type == 'max_age':
            return self._evaluate_max_age(policy)
        elif self.rule_type == 'max_coverage':
            return self._evaluate_max_coverage(policy)
        elif self.rule_type == 'min_premium':
            return self._evaluate_min_premium(policy)
        elif self.rule_type == 'severe_accident_history':
            return self._evaluate_severe_accident_history(policy)
        elif self.rule_type == 'claim_frequency':
            return self._evaluate_claim_frequency(policy)
        elif self.rule_type == 'high_risk_incident':
            return self._evaluate_high_risk_incident(policy)

        return False, ''

    def _evaluate_max_age(self, policy):
        """Flag if partner has no date-of-birth or exceeds max_age."""
        partner = policy.user_id
        if not partner.birthday:
            # Cannot verify age — route to review for manual check.
            return True, (
                "Rule '%s': Customer '%s' has no date of birth on file. "
                "Age cannot be verified." % (self.name, partner.name)
            )
        from dateutil.relativedelta import relativedelta
        today = fields.Date.today()
        age = relativedelta(today, partner.birthday).years
        if age > self.max_age:
            return True, (
                "Rule '%s': Customer '%s' is %d years old, which exceeds "
                "the maximum allowed age of %d years." % (
                    self.name, partner.name, age, self.max_age
                )
            )
        return False, ''

    def _evaluate_max_coverage(self, policy):
        if policy.coverage_limit > self.max_coverage_amount:
            return True, (
                "Rule '%s': Requested coverage limit %s exceeds the maximum "
                "allowed limit of %s." % (
                    self.name,
                    policy.coverage_limit,
                    self.max_coverage_amount,
                )
            )
        return False, ''

    def _evaluate_min_premium(self, policy):
        if policy.premium_amount < self.min_premium_amount:
            return True, (
                "Rule '%s': Policy premium %s is below the minimum required "
                "premium of %s." % (
                    self.name,
                    policy.premium_amount,
                    self.min_premium_amount,
                )
            )
        return False, ''

    def _evaluate_severe_accident_history(self, policy):
        """Count approved/paid claims for this customer across all policies."""
        all_claims = self.env['insurance.claim'].search([
            ('user_id', '=', policy.user_id.id),
            ('state', 'in', ['approved', 'paid']),
            ('policy_id', '!=', policy.id),
        ])
        count = len(all_claims)
        if count > self.max_approved_claims:
            return True, (
                "Rule '%s': Customer '%s' has %d approved/paid claims "
                "(threshold: %d). Severe accident history detected." % (
                    self.name, policy.user_id.name, count, self.max_approved_claims
                )
            )
        return False, ''

    def _evaluate_claim_frequency(self, policy):
        """Count claims filed by this customer within the lookback window."""
        from dateutil.relativedelta import relativedelta
        cutoff = fields.Date.today() - relativedelta(months=self.claim_period_months)
        claims = self.env['insurance.claim'].search([
            ('user_id', '=', policy.user_id.id),
            ('filing_date', '>=', cutoff),
            ('policy_id', '!=', policy.id),
        ])
        count = len(claims)
        if count > self.max_claims_in_period:
            return True, (
                "Rule '%s': Customer '%s' filed %d claims in the last %d months "
                "(threshold: %d)." % (
                    self.name,
                    policy.user_id.name,
                    count,
                    self.claim_period_months,
                    self.max_claims_in_period,
                )
            )
        return False, ''

    def _evaluate_high_risk_incident(self, policy):
        """Flag if any past claim involves a high-risk incident type."""
        if not self.high_risk_incident_ids:
            return False, ''
        risky_claims = self.env['insurance.claim'].search([
            ('user_id', '=', policy.user_id.id),
            ('incident_type_id', 'in', self.high_risk_incident_ids.ids),
            ('state', 'in', ['approved', 'paid']),
            ('policy_id', '!=', policy.id),
        ])
        if risky_claims:
            incident_names = ', '.join(
                risky_claims.mapped('incident_type_id.name')
            )
            return True, (
                "Rule '%s': Customer '%s' has past approved/paid claims "
                "involving high-risk incident type(s): %s." % (
                    self.name, policy.user_id.name, incident_names
                )
            )
        return False, ''
