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

class AccountMove(models.Model):
    _inherit = 'account.move'

    insurance_policy_id = fields.Many2one('insurance.policy', string='Insurance Policy', readonly=True)

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if 'state' in vals:
            for move in self:
                policy = move.insurance_policy_id
                # Recurring plans with 'invoice' activation policy activate on posting
                if move.state == 'posted' and policy and policy.plan_id.is_recurring and policy.plan_id.activation_policy == 'invoice':
                    if policy.state != 'active':
                        policy.state = 'active'

        if 'payment_state' in vals:
            for move in self:
                policy = move.insurance_policy_id
                if policy and move.payment_state in ('paid', 'in_payment'):
                    # Non-recurring: always activate on payment
                    if not policy.plan_id.is_recurring:
                        if policy.state != 'active':
                            policy.state = 'active'
                    # Recurring: only activate on payment if activation_policy == 'payment'
                    elif policy.plan_id.activation_policy == 'payment':
                        if policy.state != 'active':
                            policy.state = 'active'
        return res
