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


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    tour_inquiry_ids = fields.One2many('tour.inquiry', 'lead_id',
                                       string='Tour Inquiries')
    tour_inquiry_count = fields.Integer(compute='_compute_tour_inquiry_count',
                                        string='Inquiries')
    tour_booking_ids = fields.Many2many('tour.booking',
                                        compute='_compute_tour_booking_ids',
                                        string='Tour Bookings')
    tour_booking_count = fields.Integer(compute='_compute_tour_booking_count',
                                        string='Bookings')

    def _compute_tour_inquiry_count(self):
        for lead in self:
            lead.tour_inquiry_count = len(lead.tour_inquiry_ids)

    def _compute_tour_booking_ids(self):
        for lead in self:
            bookings = self.env['tour.booking']
            for inquiry in lead.tour_inquiry_ids:
                if inquiry.booking_id:
                    bookings |= inquiry.booking_id
            lead.tour_booking_ids = bookings

    def _compute_tour_booking_count(self):
        for lead in self:
            lead.tour_booking_count = len(lead.tour_booking_ids)

    def action_view_tour_inquiries(self):
        """View related tour inquiries"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tour Inquiries'),
            'res_model': 'tour.inquiry',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
            'target': 'current',
        }

    def action_view_tour_bookings(self):
        """View related tour bookings"""
        self.ensure_one()
        booking_ids = self.tour_booking_ids.ids
        if len(booking_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Tour Booking'),
                'res_model': 'tour.booking',
                'res_id': booking_ids[0],
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tour Bookings'),
            'res_model': 'tour.booking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', booking_ids)],
            'target': 'current',
        }
