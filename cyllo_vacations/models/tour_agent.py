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


class TourAgent(models.Model):
    _name = 'tour.agent'
    _description = 'Tour Agent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Agent Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', required=True,
        help='The partner record used for invoicing commission payouts.')
    active = fields.Boolean(default=True)
    code = fields.Char(string='Agent Code', copy=False, readonly=True, index=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    commission_rule_ids = fields.One2many('tour.agent.commission.rule', 'agent_id',
        string='Commission Rules')
    # Stats
    booking_ids = fields.One2many('tour.booking', 'agent_id', string='Bookings')
    booking_count = fields.Integer(compute='_compute_booking_count')
    commission_count = fields.Integer(compute='_compute_commission_count')
    total_commission = fields.Monetary(compute='_compute_total_commission',
        currency_field='currency_id', string='Total Commission Earned')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('tour.agent') or _('New')
        return super().create(vals_list)

    def _compute_booking_count(self):
        for agent in self:
            agent.booking_count = len(agent.booking_ids.filtered(
                lambda b: b.state != 'cancel'))

    def _compute_commission_count(self):
        for agent in self:
            agent.commission_count = self.env['tour.booking.commission'].search_count([('agent_id', '=', agent.id)])

    def _compute_total_commission(self):
        for agent in self:
            agent.total_commission = sum(
                agent.booking_ids.mapped('commission_ids')
                .filtered(lambda c: c.state == 'confirmed')
                .mapped('commission_amount')
            )
