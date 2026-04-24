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
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('invoiced', 'Invoiced'),
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('cancel', 'Cancelled'),
        ],
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

    # ── Underwriting / Risk Assessment fields ──────────────────────────────
    risk_assessment_notes = fields.Text(
        string="Risk Assessment Notes",
        readonly=True,
        copy=False,
        help="Auto-generated notes from the underwriting risk assessment.",
    )
    risk_triggered = fields.Boolean(
        string="Risk Triggered",
        default=False,
        readonly=True,
        copy=False,
        help="True if any underwriting rule was triggered during assessment.",
    )

    invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True, copy=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count', string="Invoice Count")

    ncb_percentage = fields.Float(string="NCB (%)", compute="_compute_ncb_percentage", store=True, readonly=False,
                                  help="Current No Claim Bonus percentage.")
    ncb_discount_amount = fields.Monetary(compute="_compute_premium", string="NCB Discount", store=True)

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0

    def action_view_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

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

    @api.depends('parent_policy_id', 'plan_id')
    def _compute_ncb_percentage(self):
        """Centralized NCB Logic: Triggers automatically for manual and cron jobs."""
        today = fields.Date.today()

        for rec in self:
            if rec.state == 'draft' and rec.parent_policy_id and rec.plan_id and rec.plan_id.has_no_claim_bonus:
                claims_made = rec.parent_policy_id.claim_ids.filtered(lambda c: c.state in ['approved', 'paid'])

                if claims_made:
                    # 1. Claim was made: NCB drops to 0%
                    rec.ncb_percentage = 0.0

                elif rec.parent_policy_id.end_date and rec.parent_policy_id.end_date > today:
                    # 2. Early Renewal: Risk period is NOT over.
                    # Carry over their current discount, but DO NOT grant the step increment.
                    rec.ncb_percentage = rec.parent_policy_id.ncb_percentage

                else:
                    # 3. Matured Policy: Risk period is over with zero claims. Grant the increment!
                    rec.ncb_percentage = min(
                        rec.parent_policy_id.ncb_percentage + rec.plan_id.ncb_step_percentage,
                        rec.plan_id.max_ncb_percentage
                    )
            elif not rec.parent_policy_id:
                # Default to 0 for brand new policies without a parent
                rec.ncb_percentage = 0.0

    @api.depends('coverage_line_ids.coverage_amount', 'coverage_line_ids.coverage_type',
                 'coverage_line_ids.addon_added', 'ncb_percentage')
    def _compute_premium(self):
        """Calculate premium including approved addons and NCB discount."""
        for rec in self:
            addon_total = sum(
                rec.coverage_line_ids.filtered(
                    lambda l: l.coverage_type == 'addons' and l.addon_added
                ).mapped('coverage_amount')
            )
            base_premium = (rec.plan_id.default_premium if rec.plan_id else 0) + addon_total

            # Calculate NCB Discount
            if rec.ncb_percentage > 0:
                rec.ncb_discount_amount = base_premium * (rec.ncb_percentage / 100.0)
            else:
                rec.ncb_discount_amount = 0.0

            # Final premium is Base Premium - NCB Discount
            rec.premium_amount = base_premium - rec.ncb_discount_amount

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

    @api.constrains('user_id', 'plan_id', 'start_date', 'end_date')
    def _check_policy_overlap(self):
        """Prevent overlapping policies for the same user and plan."""
        for rec in self:
            if not (rec.user_id and rec.plan_id and rec.start_date and rec.end_date):
                continue
            overlap = self.search([
                ('id', '!=', rec.id),
                ('user_id', '=', rec.user_id.id),
                ('plan_id', '=', rec.plan_id.id),
                ('state', 'not in', ['cancel', 'expired']),
                ('start_date', '<=', rec.end_date),
                ('end_date', '>=', rec.start_date),
            ], limit=1)
            if overlap:
                raise ValidationError(
                    "A policy already exists for customer '%s' under plan '%s' "
                    "that overlaps with the dates %s \u2192 %s (Policy: %s)." % (
                        rec.user_id.name,
                        rec.plan_id.name,
                        rec.start_date,
                        rec.end_date,
                        overlap.policy_no,
                    )
                )

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

    @api.onchange('parent_policy_id')
    def _onchange_parent_policy_id(self):
        """When manually renewing, auto-fill data from the parent."""
        if not self.parent_policy_id:
            return

        self.plan_id = self.parent_policy_id.plan_id
        self.user_id = self.parent_policy_id.user_id
        self.coverage_limit = self.parent_policy_id.coverage_limit
        self.deductible = self.parent_policy_id.deductible

        lines = []
        for line in self.parent_policy_id.coverage_line_ids:
            lines.append((0, 0, {
                'coverage_id': line.coverage_id.id,
                'coverage_amount': line.coverage_amount,
                'coverage_type': line.coverage_type,
            }))
        self.coverage_line_ids = [(5, 0, 0)] + lines

    @api.onchange('user_id', 'plan_id')
    def _onchange_user_plan_auto_parent(self):
        """Auto-select the latest valid parent policy to prevent skipping history."""
        if self.user_id and self.plan_id:
            # Search for the most recent policy for this exact user and plan
            latest_policy = self.env['insurance.policy'].search([
                ('user_id', '=', self.user_id.id),
                ('plan_id', '=', self.plan_id.id),
                # If we are editing an existing record, don't find itself
                ('id', '!=', self._origin.id if self._origin else False)
            ], order='end_date desc', limit=1)

            # If a policy was found AND it hasn't been renewed yet (no children)
            if latest_policy and not latest_policy.child_policy_ids:
                self.parent_policy_id = latest_policy.id
            else:
                self.parent_policy_id = False

    def action_confirm(self):
        """Moves policy to confirmed state or active directly based on activation policy."""
        for rec in self:
            if rec.plan_id.is_recurring and rec.plan_id.activation_policy == 'confirm':
                rec.state = 'active'
            else:
                rec.state = 'confirmed'

    def action_assess_risk(self):
        """
        Underwriting Risk Assessment Engine.

        Evaluates all active underwriting rules (optionally scoped to the
        policy's plan) against this policy.  If any rule is triggered, the
        policy moves to **under_review** and requires manual admin approval.
        If no rules are triggered the policy moves to **approved** and can
        proceed directly to invoicing.

        This method can be called:
        - Manually by the user from the 'Confirmed' state via the button.
        - Programmatically (e.g., from action_confirm) if desired.
        """
        self.ensure_one()

        if self.state != 'confirmed':
            raise ValidationError(
                "Risk assessment can only be run on a Confirmed policy."
            )

        # Fetch all active rules, ordered by sequence
        rules = self.env['cyllo.insurance.underwriting.rule'].search(
            [('active', '=', True)],
            order='sequence, id',
        )

        triggered_messages = []
        for rule in rules:
            is_triggered, reason = rule.evaluate(self)
            if is_triggered:
                triggered_messages.append(reason)

        if triggered_messages:
            # One or more rules fired → send to manual review
            notes = ("⚠️ The following underwriting rules were triggered:\n\n"
                     + '\n'.join('• ' + m for m in triggered_messages))
            self.write({
                'state': 'under_review',
                'risk_triggered': True,
                'risk_assessment_notes': notes,
            })
            # Post a chatter message so the admin is alerted
            self.message_post(
                body=notes,
                subtype_xmlid='mail.mt_note',
                author_id=self.env.user.partner_id.id,
            )
        else:
            # All rules passed → auto-approve
            notes = "✅ All underwriting rules passed. Policy auto-approved."
            self.write({
                'state': 'approved',
                'risk_triggered': False,
                'risk_assessment_notes': notes,
            })
            self.message_post(
                body=notes,
                subtype_xmlid='mail.mt_note',
                author_id=self.env.user.partner_id.id,
            )

        return True

    def action_approve_policy(self):
        """
        Admin action: Manually approve a policy that is 'under_review'.
        Moves the policy to the 'approved' state so it can be invoiced.
        """
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(
                    "Only policies in 'Under Review' state can be approved here."
                )
            rec.write({'state': 'approved'})
            rec.message_post(
                body="✅ Policy manually approved by %s after underwriting review." % self.env.user.name,
                subtype_xmlid='mail.mt_note',
                author_id=self.env.user.partner_id.id,
            )

    def action_reject_underwriting(self):
        """
        Admin action: Reject a policy that is 'under_review'.
        Moves the policy to 'cancel' with a chatter note.
        """
        for rec in self:
            if rec.state != 'under_review':
                raise ValidationError(
                    "Only policies in 'Under Review' state can be rejected here."
                )
            rec.write({'state': 'cancel'})
            rec.message_post(
                body="❌ Policy rejected after underwriting review by %s." % self.env.user.name,
                subtype_xmlid='mail.mt_note',
                author_id=self.env.user.partner_id.id,
            )

    def action_create_invoice(self):
        """Simulates creating an invoice and pushes policy to active."""
        for rec in self:
            if rec.state not in ('confirmed', 'approved'):
                raise ValidationError(
                    "Policy must be in Confirmed or Approved state to create an invoice."
                )
            if rec.invoice_id:
                raise ValidationError("An invoice has already been created for this policy.")

            journal = rec.env['account.journal'].search([
                ('company_id', '=', rec.env.company.id),
                ('code', '=', 'INS')
            ], limit=1)

            if not journal:
                # Self-healing lazy initialization if the hook didn't run properly
                from ..hooks import _setup_insurance_accounting
                _setup_insurance_accounting(rec.env, rec.env.company)

                journal = rec.env['account.journal'].search([
                    ('company_id', '=', rec.env.company.id),
                    ('code', '=', 'INS')
                ], limit=1)

                if not journal:
                    raise ValidationError(
                        "Insurance Sales Journal could not be created automatically. Please set it up manually.")

            product = rec.env.ref('cyllo_insurance.product_product_insurance_premium', raise_if_not_found=False)
            if not product:
                raise ValidationError("Insurance Premium product not found.")

            invoice = rec.env['account.move'].create({
                'move_type': 'out_invoice',
                'journal_id': journal.id,
                'partner_id': rec.user_id.id,
                'insurance_policy_id': rec.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': rec.premium_amount,
                    'account_id': journal.default_account_id.id,
                })],
            })

            rec.invoice_id = invoice.id
            rec.state = 'invoiced'

            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_id.id,
                'target': 'current',
            }

    def action_expired(self):
        self.state = 'expired'

    def action_reset_to_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    def action_renew_policy(self):
        """1-Click manual renewal from the UI."""
        self.ensure_one()  # Ensures this is only clicked from a single record view

        # 1. Validation Checks
        if self.child_policy_ids:
            raise ValidationError("This policy has already been renewed. Please check the Renewal History.")
        if self.state not in ['active', 'expired']:
            raise ValidationError("Only active or expired policies can be renewed.")

        # 2. Calculate the next billing cycle dates
        new_start = self.end_date + relativedelta(days=1)
        kwargs = {f"{self.plan_id.duration_type}": self.plan_id.duration}
        new_end = new_start + relativedelta(**kwargs) - relativedelta(days=1)

        # 3. Copy over the exact coverage lines
        coverage_lines = []
        for line in self.coverage_line_ids:
            coverage_lines.append((0, 0, {
                'coverage_id': line.coverage_id.id,
                'coverage_amount': line.coverage_amount,
                'coverage_type': line.coverage_type,
            }))

        # 4. Create the new drafted policy
        # Setting 'parent_policy_id' automatically triggers the NCB discount calculation!
        new_policy = self.create({
            'plan_id': self.plan_id.id,
            'user_id': self.user_id.id,
            'start_date': new_start,
            'end_date': new_end,
            'parent_policy_id': self.id,
            'coverage_limit': self.coverage_limit,
            'deductible': self.deductible,
            'coverage_line_ids': coverage_lines,
            'state': 'draft',
        })

        # 5. Redirect the user's screen to the newly created policy
        return {
            'name': 'Renewed Policy',
            'type': 'ir.actions.act_window',
            'res_model': 'insurance.policy',
            'view_mode': 'form',
            'res_id': new_policy.id,
            'target': 'current',
        }

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

            new_policy = self.create({
                'plan_id': policy.plan_id.id,
                'user_id': policy.user_id.id,
                'start_date': new_start,
                'end_date': new_end,
                'parent_policy_id': policy.id,
                'coverage_limit': policy.coverage_limit,
                'deductible': policy.deductible,
                'coverage_line_ids': coverage_lines,
                'state': 'draft',
            })

            # Step 2: Confirm new policy
            new_policy.action_confirm()

            # Step 3: Create invoice (state moves to invoiced if active rule isn't confirm)
            new_policy.action_create_invoice()

            # Step 4: Post invoice (potentially triggering 'invoice' activation rule)
            if new_policy.invoice_id:
                new_policy.invoice_id.action_post()

            policy.state = 'expired'
