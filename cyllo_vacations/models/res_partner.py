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
from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tour_booking_ids = fields.One2many('tour.booking', 'partner_id',
                                       string='Tour Bookings')
    tour_booking_count = fields.Integer(compute='_compute_tour_booking_count',
                                        string='Tour Bookings')
    tour_inquiry_ids = fields.One2many('tour.inquiry', 'partner_id',
                                       string='Tour Inquiries')
    tour_inquiry_count = fields.Integer(compute='_compute_tour_inquiry_count',
                                        string='Tour Inquiries')
    total_tour_revenue = fields.Monetary(compute='_compute_tour_revenue',
                                         string='Tour Revenue',
                                         currency_field='currency_id')

    def _compute_tour_booking_count(self):
        for partner in self:
            partner.tour_booking_count = len(partner.tour_booking_ids)

    def _compute_tour_inquiry_count(self):
        for partner in self:
            partner.tour_inquiry_count = len(partner.tour_inquiry_ids)

    def _compute_tour_revenue(self):
        for partner in self:
            partner.total_tour_revenue = sum(
                partner.tour_booking_ids.filtered(
                    lambda b: b.state not in ['cancel', 'draft']
                ).mapped('price_total')
            )

    def action_view_tour_bookings(self):
        """View partner's tour bookings"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tour Bookings'),
            'res_model': 'tour.booking',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'target': 'current',
        }

    def action_view_tour_inquiries(self):
        """View partner's tour inquiries"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tour Inquiries'),
            'res_model': 'tour.inquiry',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'target': 'current',
        }
