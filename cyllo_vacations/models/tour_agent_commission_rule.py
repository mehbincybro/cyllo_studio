# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TourAgentCommissionRule(models.Model):
    _name = 'tour.agent.commission.rule'
    _description = 'Tour Agent Commission Rule'
    _order = 'sequence, id'

    agent_id = fields.Many2one('tour.agent', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)
    # Scope: leave package_id empty to apply to all packages
    package_id = fields.Many2one('tour.package', string='Package',
        help='Leave empty to apply to all packages.')
    commission_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Booking Total'),
    ], string='Commission Type', required=True, default='percentage')
    fixed_amount = fields.Monetary(string='Fixed Amount',
        currency_field='currency_id')
    percentage = fields.Float(string='Percentage (%)',
        digits=(5, 2), help='e.g. 10.00 means 10%')
    currency_id = fields.Many2one('res.currency',
        related='agent_id.currency_id', readonly=True)
    # Optional: only apply if booking total is within a range
    min_booking_amount = fields.Monetary(string='Min Booking Amount',
        currency_field='currency_id')
    max_booking_amount = fields.Monetary(string='Max Booking Amount',
        currency_field='currency_id',
        help='Leave 0 for no upper limit.')

    @api.constrains('commission_type', 'fixed_amount', 'percentage')
    def _check_commission_value(self):
        for rule in self:
            if rule.commission_type == 'fixed' and rule.fixed_amount <= 0:
                raise ValidationError(_('Fixed commission amount must be greater than zero.'))
            if rule.commission_type == 'percentage' and not (0 < rule.percentage <= 100):
                raise ValidationError(_('Commission percentage must be between 0 and 100.'))

    @api.model
    def _find_rule_for_booking(self, agent, booking):
        rules = self.search([
            ('agent_id', '=', agent.id),
            ('active', '=', True),
            '|', ('package_id', '=', booking.package_id.id),
            ('package_id', '=', False),
        ], order='package_id desc, sequence asc')
        for rule in rules:
            min_ok = not rule.min_booking_amount or booking.price_total >= rule.min_booking_amount
            max_ok = not rule.max_booking_amount or booking.price_total <= rule.max_booking_amount
            if min_ok and max_ok:
                return rule
        return self.browse()
