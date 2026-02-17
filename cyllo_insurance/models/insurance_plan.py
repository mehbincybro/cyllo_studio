from odoo import models, fields, api


class InsurancePlan(models.Model):
    _name = 'insurance.plan'
    _description = 'Insurance Plan'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(required=True,help="Name of the insurance plan.")
    code = fields.Char(required=True,help="Unique code for the plan.")
    policy_type_id = fields.Many2one('insurance.policy.type', required=True,help="Type of policy this plan belongs to.")
    valid_from = fields.Date(help="Start date of plan validity.")
    valid_to = fields.Date(help="End date of plan validity.")
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired')],
                             default='draft', tracking=True)
    default_premium = fields.Monetary(required=True, help="Base premium amount for this plan.")
    default_coverage_limit = fields.Monetary(required=True,help="Maximum coverage amount allowed.")
    default_deductible = fields.Monetary(default=0,help="Default deductible amount.")
    coverage_line_ids = fields.One2many('insurance.plan.coverage', 'plan_id')
    description = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(default=True,help="Uncheck to archive this plan.")
    # total_coverage_amount = fields.Monetary(compute="_compute_total_coverage_amount", store=True)

    def action_active(self):
        """ Function for state changing to active"""
        self.state = 'active'

    def action_expired(self):
        """ Function for state changing to expired"""
        self.state = 'expired'

    def action_reset_to_draft(self):
        """ Function for state changing to draft"""
        self.state = 'draft'

    # @api.depends('coverage_line_ids.coverage_amount',
    #              'coverage_line_ids.coverage_type')
    # def _compute_total_coverage_amount(self):
    #     for record in self:
    #         record.total_coverage_amount = sum(
    #             record.coverage_line_ids
    #             .filtered(lambda l: l.coverage_type == 'covered')
    #             .mapped('coverage_amount')
    #         )

