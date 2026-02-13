from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsuranceClaim(models.Model):
    _name = 'insurance.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread']
    _rec_name = 'claim_no'

    claim_no = fields.Char(required=True, copy=False, readonly=True,
                           default=lambda self: self.env['ir.sequence'].next_by_code('insurance.claim'))
    policy_id = fields.Many2one('insurance.policy', required=True)
    user_id = fields.Many2one(related='policy_id.user_id', store=True)
    incident_date = fields.Date(required=True)
    filing_date = fields.Date(default=fields.Date.today)
    approved_date = fields.Date()
    claimed_amount = fields.Monetary(required=True)
    approved_amount = fields.Monetary()
    deductible_applied = fields.Monetary(compute='_compute_payout', store=True)
    payout_amount = fields.Monetary(compute='_compute_payout', store=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected'),
         ('paid', 'Paid'), ], default='draft', tracking=True)
    description = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment')
    currency_id = fields.Many2one(related='policy_id.currency_id', store=True)

    @api.depends('approved_amount', 'policy_id.deductible')
    def _compute_payout(self):
        for record in self:
            deductible = record.policy_id.deductible or 0
            approved = record.approved_amount or 0

            record.deductible_applied = min(deductible, approved)
            record.payout_amount = max(approved - deductible, 0)

    @api.constrains('incident_date', 'policy_id')
    def _check_policy_validity(self):
        for record in self:
            if record.policy_id:
                if not (record.policy_id.start_date <= record.incident_date <= record.policy_id.end_date):
                    raise ValidationError("Incident date must be within policy validity period.")

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        if self.claimed_amount > self.policy_id.remaining_coverage:
            raise ValidationError("Claim exceeds remaining coverage.")
        self.write({
            'state': 'approved',
            'approved_amount': self.claimed_amount,
            'approved_date': fields.Date.today()
        })

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})
