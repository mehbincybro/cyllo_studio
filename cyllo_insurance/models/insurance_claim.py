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


class InsuranceClaim(models.Model):
    _name = 'insurance.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread']
    _rec_name = 'claim_no'

    claim_no = fields.Char(required=True, copy=False, readonly=True,
                           default=lambda self: self.env['ir.sequence'].next_by_code('insurance.claim'))
    policy_id = fields.Many2one('insurance.policy', required=True,
                                help="Policy under which this claim is submitted.")
    user_id = fields.Many2one(related='policy_id.user_id', store=True, help="Policy holder who owns this claim.")
    incident_date = fields.Date(help="Date when the incident happened.", required=True)
    filing_date = fields.Date(default=fields.Date.today, help="Date when the claim was filed.")
    approved_date = fields.Date(help="Date when the claim was approved.")
    claimed_amount = fields.Monetary(required=True, help="Amount requested by the policy holder.")
    approved_amount = fields.Monetary(help="Amount approved by the company.")
    deductible_applied = fields.Monetary(compute='_compute_payout', store=True,
                                         help="Deductible amount applied from the approved amount.")
    payout_amount = fields.Monetary(compute='_compute_payout', store=True, help="Final amount paid after deducting deductible.")
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected'),
         ('paid', 'Paid'), ], default='draft', tracking=True)
    description = fields.Text(string="Description", help="Additional details about the claim.")
    attachment_ids = fields.Many2many('ir.attachment')
    currency_id = fields.Many2one(related='policy_id.currency_id', store=True)

    incident_type_id = fields.Many2one(
        'insurance.incident.type',
        string="Incident Type",
        required=True
    )

    @api.depends('approved_amount', 'policy_id.deductible')
    def _compute_payout(self):
        """Compute deductible applied and final payout amount."""
        for record in self:
            deductible = record.policy_id.deductible or 0
            approved = record.approved_amount or 0

            record.deductible_applied = min(deductible, approved)
            record.payout_amount = max(approved - deductible, 0)

    @api.constrains('incident_date', 'policy_id')
    def _check_policy_validity(self):
        """Ensure incident date is within policy validity period."""
        for record in self:
            if record.policy_id:
                if not (record.policy_id.start_date <= record.incident_date <= record.policy_id.end_date):
                    raise ValidationError("Incident date must be within policy validity period.")

    def action_submit(self):
        """Submit claim for approval."""
        for rec in self:
            if rec.policy_id.state != 'active':
                raise ValidationError("You cannot submit a claim. The policy must be active.")
            if rec.policy_id.invoice_id and rec.policy_id.invoice_id.payment_state not in ('paid', 'in_payment'):
                raise ValidationError("The policy invoice must be paid before submitting claims.")
            rec.write({'state': 'submitted'})

    def action_approve(self):
        """Approve claim if within remaining coverage."""
        if self.incident_type_id in self.policy_id.excluded_incident_ids:
            raise ValidationError(
                "This incident type is excluded under the policy."
            )

        if self.claimed_amount > self.policy_id.remaining_coverage:
            raise ValidationError("Claim exceeds remaining coverage.")
        self.write({
            'state': 'approved',
            'approved_amount': self.claimed_amount,
            'approved_date': fields.Date.today()
        })

    def action_reject(self):
        """Reject the claim."""
        self.write({'state': 'rejected'})

    def action_mark_paid(self):
        """Mark claim as paid."""
        self.write({'state': 'paid'})

    @api.constrains('incident_date', 'filing_date')
    def _check_incident_and_filing_dates(self):
        """Validate incident and filing dates."""
        for rec in self:
            if rec.incident_date and rec.incident_date > fields.Date.today():
                raise ValidationError("Incident date cannot be in the future.")
            # Filing date cannot be before incident date
            if rec.incident_date and rec.filing_date:
                if rec.filing_date < rec.incident_date:
                    raise ValidationError("Filing date cannot be before incident date.")
                elif (rec.filing_date - rec.incident_date).days > rec.policy_id.plan_id.claim_window_days or 0:
                    raise ValidationError("Claim must be filed within %s days of Incident." % rec.policy_id.plan_id.claim_window_days or 0)
