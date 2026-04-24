# -*- coding: utf-8 -*-
#############################################################################
#
#   Cyllo Pvt. Ltd.
#
#   Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#   Author: Cyllo(<https://www.cyllo.com>)
#
#   You can modify it under the terms of the GNU LESSER
#   GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#   You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#   (LGPL v3) along with this program.
#   If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields


class InsurancePlan(models.Model):
    _name = 'insurance.plan'
    _description = 'Insurance Plan'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(required=True, help="Name of the insurance plan.")
    code = fields.Char(required=True, help="Unique code for the plan.")
    policy_type_id = fields.Many2one('insurance.policy.type', required=True,
                                     help="Type of policy this plan belongs to.")
    claim_window_days = fields.Integer(default=30)

    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired')],
                             default='draft', tracking=True)
    default_premium = fields.Monetary(required=True, string="Full Premium",
                                      help="Total premium amount for this plan duration.")
    default_coverage_limit = fields.Monetary(required=True, help="Maximum coverage amount allowed.")
    default_deductible = fields.Monetary(default=0, help="Default deductible amount.")
    coverage_line_ids = fields.One2many('insurance.plan.coverage', 'plan_id')
    description = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(default=True, help="Uncheck to archive this plan.")

    is_recurring = fields.Boolean(string="Recurring Plan")
    activation_policy = fields.Selection([
        ('confirm', 'Confirm (Activate on Validation)'),
        ('invoice', 'Invoice (Activate on Invoice Post)'),
        ('payment', 'Payment (Activate on Full Payment)')
    ], string="Activation Policy", default="confirm", help="Choose when the policy should be activated.")

    duration = fields.Integer(string="Duration", default=1, required=True)
    duration_type = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string="Duration Type", default='months', required=True)

    has_no_claim_bonus = fields.Boolean(string="Enable No Claim Bonus", default=False,
                                        help="Check this to allow NCB accumulation on renewal.")
    ncb_step_percentage = fields.Float(string="NCB Increment per Renewal (%)", default=5.0)
    max_ncb_percentage = fields.Float(string="Maximum NCB (%)", default=50.0)

    def action_active(self):
        """ Function for state changing to active """
        self.state = 'active'

    def action_expired(self):
        """ Function for state changing to expired """
        self.state = 'expired'

    def action_reset_to_draft(self):
        """ Function for state changing to draft """
        self.state = 'draft'