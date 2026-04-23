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
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class InsurancePolicy(models.Model):
    _name = 'insurance.policy'
    _description = 'Insurance Policy'
    _inherit = ['mail.thread']
    _rec_name = 'policy_no'

    policy_no = fields.Char(required=True, copy=False, readonly=True, default='New')
    plan_id = fields.Many2one('insurance.plan', required=True, help="Insurance plan selected for this policy.")
    user_id = fields.Many2one('res.partner', required=True, help="Customer who owns this policy.")
    issue_date = fields.Date(default=fields.Date.today, string="Issue Date")
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)

    premium_amount = fields.Monetary(compute="_compute_premium", store=True, help="Total premium including addons.")
    coverage_limit = fields.Monetary(required=True, help="Maximum amount that can be claimed.")
    deductible = fields.Monetary(default=0, help="Amount deducted from each approved claim.")
    used_coverage = fields.Monetary(compute='_compute_used_coverage', store=True,
                                    help="Total approved claim amount used.")
    remaining_coverage = fields.Monetary(compute='_compute_remaining_coverage', store=True,
                                         help="Remaining coverage amount available.")

    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('active', 'Active'), ('expired', 'Expired'), ('cancel', 'Cancelled')],
        default='draft', tracking=True)

    description = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment')
    claim_ids = fields.One2many('insurance.claim', 'policy_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    coverage_line_ids = fields.One2many('insurance.policy.coverage', 'policy_id')

    is_recurring = fields.Boolean(related='plan_id.is_recurring', store=True)

    parent_policy_id = fields.Many2one('insurance.policy')
    child_policy_ids = fields.One2many('insurance.policy', 'parent_policy_id')
    renewal_history_ids = fields.Many2many('insurance.policy', compute='_compute_renewal_history',
                                           string="Renewal History")

    excluded_incident_ids = fields.Many2many(
        'insurance.incident.type',
        string="Excluded Incidents")

    @api.model_create_multi
    def create(self, vals_list):
        """Generate unique policy number when creating a policy."""
        for vals in vals_list:
            if vals.get('policy_no', 'New') == 'New' and vals.get('plan_id'):
                plan = self.env['insurance.plan'].browse(vals['plan_id'])
                prefix = plan.code or 'POL'
                sequence_code = f'insurance.policy.{plan.id}'

                sequence = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)

                if not sequence:
                    sequence = self.env['ir.sequence'].create({
                        'name': f'Policy {plan.name}',
                        'code': sequence_code,
                        'prefix': f'{prefix}/',
                        'padding': 4,
                        'company_id': self.env.company.id,
                    })
                vals['policy_no'] = self.env['ir.sequence'].next_by_code(sequence_code)
        return super().create(vals_list)

    @api.depends('coverage_line_ids.coverage_amount', 'coverage_line_ids.coverage_type',
                 'coverage_line_ids.addon_added')
    def _compute_premium(self):
        """Calculate premium including approved addons."""
        for rec in self:
            addon_total = sum(
                rec.coverage_line_ids.filtered(
                    lambda l: l.coverage_type == 'addons' and l.addon_added
                ).mapped('coverage_amount')
            )
            rec.premium_amount = (rec.plan_id.default_premium if rec.plan_id else 0) + addon_total

    @api.depends('claim_ids.approved_amount', 'claim_ids.state')
    def _compute_used_coverage(self):
        """Calculate total approved claim amount used."""
        for record in self:
            approved_claims = record.claim_ids.filtered(lambda c: c.state in ['approved', 'paid'])
            record.used_coverage = sum(approved_claims.mapped('approved_amount'))

    @api.depends('coverage_limit', 'used_coverage')
    def _compute_remaining_coverage(self):
        """Calculate remaining coverage amount."""
        for record in self:
            record.remaining_coverage = record.coverage_limit - record.used_coverage

    @api.constrains('premium_amount', 'coverage_limit', 'deductible')
    def _check_amounts(self):
        """Ensure financial values are not negative."""
        for rec in self:
            if rec.premium_amount < 0 or rec.coverage_limit < 0 or rec.deductible < 0:
                raise ValidationError("The amount must not be a Negative number.")

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Ensure end date is after start date."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError("End date must be after start date.")

    @api.constrains('start_date', 'issue_date')
    def _check_start_issue_dates(self):
        """Ensure start date is not before issue date."""
        for rec in self:
            if rec.start_date and rec.issue_date and rec.start_date < rec.issue_date:
                raise ValidationError("Start date cannot be earlier than the issue date.")

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        """Set default values and copy coverage lines when selecting a plan."""
        if not self.plan_id:
            return
        self.coverage_limit = self.plan_id.default_coverage_limit
        self.deductible = self.plan_id.default_deductible

        self.coverage_line_ids = [(5, 0, 0)]
        lines = []
        for line in self.plan_id.coverage_line_ids:
            lines.append((0, 0, {
                'coverage_id': line.coverage_id.id,
                'coverage_amount': line.coverage_amount,
                'coverage_type': line.coverage_type,
            }))
        self.coverage_line_ids = lines

    def action_confirm(self):
        """Moves policy to confirmed state awaiting invoice."""
        self.state = 'confirmed'

    def action_create_invoice(self):
        """Simulates creating an invoice and pushes policy to active."""
        self.state = 'active'

    def action_expired(self):
        self.state = 'expired'

    def action_reset_to_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    def _compute_renewal_history(self):
        for rec in self:
            history = self.env['insurance.policy']
            current = rec.parent_policy_id
            while current:
                history |= current
                current = current.parent_policy_id
            rec.renewal_history_ids = history

    # --- THE CORE RECURRING LOGIC ---

    @api.onchange('start_date', 'plan_id')
    def _onchange_start_date(self):
        """Automatically calculates End Date based on Plan Duration"""
        if self.start_date and self.plan_id and self.plan_id.duration:
            kwargs = {f"{self.plan_id.duration_type}": self.plan_id.duration}
            self.end_date = self.start_date + relativedelta(**kwargs) - relativedelta(days=1)
            
        if self.start_date and self.issue_date and self.start_date < self.issue_date:
            self.start_date = False
            return {
                'warning': {
                    'title': 'Invalid Start Date',
                    'message': 'Start date cannot be earlier than the Issue Date.'
                }
            }

    @api.onchange('end_date', 'plan_id')
    def _onchange_end_date(self):
        """Automatically calculates Start Date based on Plan Duration"""
        if self.end_date and self.plan_id and self.plan_id.duration:
            kwargs = {f"{self.plan_id.duration_type}": self.plan_id.duration}
            new_start = self.end_date - relativedelta(**kwargs) + relativedelta(days=1)
            self.start_date = new_start
            
            if new_start and self.issue_date and new_start < self.issue_date:
                self.start_date = False
                self.end_date = False
                return {
                    'warning': {
                        'title': 'Invalid End Date',
                        'message': 'Calculated Start date cannot be earlier than the Issue Date.'
                    }
                }

    def action_auto_renew_policies(self):
        """Cron Job: Triggers on the End Date for policy auto-renewal."""
        today = fields.Date.today()

        policies = self.search([
            ('is_recurring', '=', True),
            ('end_date', '<=', today),
            ('state', '=', 'active')
        ])

        for policy in policies:
            existing_renewal = self.search([
                ('parent_policy_id', '=', policy.id)
            ], limit=1)

            if existing_renewal:
                policy.state = 'expired'
                continue

            new_start = policy.end_date + relativedelta(days=1)
            kwargs = {f"{policy.plan_id.duration_type}": policy.plan_id.duration}
            new_end = new_start + relativedelta(**kwargs) - relativedelta(days=1)

            coverage_lines = []
            for line in policy.coverage_line_ids:
                coverage_lines.append((0, 0, {
                    'coverage_id': line.coverage_id.id,
                    'coverage_amount': line.coverage_amount,
                    'coverage_type': line.coverage_type,
                }))

            self.create({
                'plan_id': policy.plan_id.id,
                'user_id': policy.user_id.id,
                'start_date': new_start,
                'end_date': new_end,
                'parent_policy_id': policy.id,
                'coverage_limit': policy.coverage_limit,
                'deductible': policy.deductible,
                'premium_amount': policy.premium_amount,
                'coverage_line_ids': coverage_lines,
                'state': 'active',  # Ensure new policy is instantly active
            })

            policy.state = 'expired'
