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


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    tour_booking_id = fields.Many2one('tour.booking', string='Tour Booking',
                                      compute='_compute_tour_booking_id',
                                      store=True)

    @api.depends('name')
    def _compute_tour_booking_id(self):
        for event in self:
            booking = self.env['tour.booking'].search(
                [('calendar_event_id', '=', event.id)], limit=1)
            event.tour_booking_id = booking.id if booking else False

    def action_view_tour_booking(self):
        """View related tour booking"""
        self.ensure_one()
        if self.tour_booking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Tour Booking'),
                'res_model': 'tour.booking',
                'res_id': self.tour_booking_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False