from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError


class InsurancePolicy(models.Model):
    _name = 'insurance.policy'
    _description = 'Insurance Policy'
    _inherit = ['mail.thread']
    _rec_name = 'policy_no'

    policy_no = fields.Char(required=True, copy=False, readonly=True, default='New')
    plan_id = fields.Many2one('insurance.plan', required=True)
    user_id = fields.Many2one('res.partner', required=True)
    issue_date = fields.Date(default=fields.Date.today)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    premium_amount = fields.Monetary(required=True)
    coverage_limit = fields.Monetary(required=True)
    deductible = fields.Monetary(default=0)
    used_coverage = fields.Monetary(compute='_compute_used_coverage', store=True)
    remaining_coverage = fields.Monetary(compute='_compute_remaining_coverage', store=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('cancelled', 'Cancelled'), ],
        default='draft', tracking=True)
    description = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment')
    claim_ids = fields.One2many('insurance.claim', 'policy_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    coverage_line_ids = fields.One2many('insurance.policy.coverage', 'policy_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Generate Policy Number per Plan
            if vals.get('policy_no', 'New') == 'New' and vals.get('plan_id'):
                plan = self.env['insurance.plan'].browse(vals['plan_id'])

                prefix = plan.code or 'POL'
                sequence_code = f'insurance.policy.{plan.id}'

                sequence = self.env['ir.sequence'].search([
                    ('code', '=', sequence_code)
                ], limit=1)

                # Create sequence if not exists
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

    @api.depends('claim_ids.approved_amount')
    def _compute_used_coverage(self):
        for record in self:
            approved_claims = record.claim_ids.filtered(
                lambda c: c.state in ['approved', 'paid'])
            record.used_coverage = sum(approved_claims.mapped('approved_amount'))

    @api.depends('coverage_limit', 'used_coverage')
    def _compute_remaining_coverage(self):
        for record in self:
            record.remaining_coverage = record.coverage_limit - record.used_coverage

    @api.constrains('premium_amount', 'coverage_limit', 'deductible')
    def _check_amounts(self):
        for rec in self:
            if rec.premium_amount < 0 or rec.coverage_limit < 0 or rec.deductible < 0:
                raise ValidationError("The amount must not be a Negative number.")

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError("End date must be after start date.")

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        """Set policy amounts and copy coverage lines from plan"""
        if not self.plan_id:
            return
        # Set financial values
        self.premium_amount = self.plan_id.default_premium
        self.coverage_limit = self.plan_id.default_coverage_limit
        self.deductible = self.plan_id.default_deductible

        # Clear existing policy coverage lines
        self.coverage_line_ids = [(5, 0, 0)]
        lines = []
        for line in self.plan_id.coverage_line_ids:
            lines.append((0, 0, {
                'coverage_id': line.coverage_id.id,
                'coverage_amount': line.coverage_amount,
                'deductible': line.deductible,
                'coverage_type': line.coverage_type,
            }))

        self.coverage_line_ids = lines

    def action_active(self):
        """ Function for state changing to active"""
        self.state = 'active'

    def action_expired(self):
        """ Function for state changing to expired"""
        self.state = 'expired'

    def action_reset_to_draft(self):
        """ Function for state changing to draft"""
        self.state = 'draft'

    def action_cancel(self):
        self.state='cancel'
