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
from odoo import api, fields, models, _

class EventEvent(models.Model):
    """Extend event model to include venue and catering management."""
    _inherit = 'event.event'

    need_venue = fields.Boolean(string="Need Venue", help="Check if venue is needed for this event")
    venue_id = fields.Many2one('venue', string="Venue", help="Select venue for the event")
    venue_booking_id = fields.Many2one('venue.booking', string="Venue Booking", readonly=True)
    need_catering = fields.Boolean(string="Need Catering", help="Check if catering is needed for this event")
    catering_ids = fields.Many2many('catering.booking', 'event_catering_rel', 'event_id', 'catering_id', string="Catering Orders",
                                  domain="[('state', '=', 'confirm'), ('event_id', '=', False), ('venue_booking_id', '=', False)]")
    catering_count = fields.Integer(string="Catering Count", compute='_compute_catering_count')

    @api.depends('catering_ids')
    def _compute_catering_count(self):
        """Compute total catering bookings linked to the event."""
        for record in self:
            created_bookings = self.env['catering.booking'].search_count([('event_id', '=', record.id)])
            record.catering_count = len(record.catering_ids) + created_bookings

    @api.onchange('catering_ids')
    def _onchange_catering_ids(self):
        """Link selected catering orders to this event"""
        for catering in self.catering_ids:
            if not catering.event_id:
                catering.event_id = self.id

    def action_create_catering_booking(self):
        """Open form to create a catering booking linked to the event."""
        self.ensure_one()
        if not self.catering_booking_id and not self.catering_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Create Catering Booking'),
                'res_model': 'catering.booking',
                'view_mode': 'form',
                'context': {
                    'default_partner_id': self.organizer_id.id,
                    'default_start_date': self.date_begin,
                    'default_end_date': self.date_end,
                    'default_event_id': self.id,
                },
                'target': 'new',
            }

    def action_view_catering_booking(self):
        """View all catering bookings linked to the current event."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("cyllo_occasion_management.catering_booking_action")
        # Find all catering orders linked directly or via many2many
        linked_ids = self.catering_ids.ids
        created_ids = self.env['catering.booking'].search([('event_id', '=', self.id)]).ids
        action['domain'] = [('id', 'in', list(set(linked_ids + created_ids)))]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate venue booking when required."""
        records = super().create(vals_list)
        for record in records:
            if record.need_venue and record.venue_id and not record.venue_booking_id:
                record._create_venue_booking()
        return records

    def write(self, vals):
        """Override write to ensure venue booking is created when conditions are met."""
        res = super().write(vals)
        for record in self:
            if record.need_venue and record.venue_id and not record.venue_booking_id:
                record._create_venue_booking()
        return res

    def _create_venue_booking(self):
        """Create a venue booking record for the event"""
        self.ensure_one()
        amenity_lines = []
        if self.venue_id:
            for line in self.venue_id.venue_line_ids:
                amenity_lines.append((0, 0, {
                    'amenity_id': line.amenities_id.id,
                    'quantity': line.quantity,
                    'is_included': True,
                }))
        booking_vals = {
            'venue_id': self.venue_id.id,
            'partner_id': self.organizer_id.id or self.env.user.partner_id.id,
            'date': fields.Date.today(),
            'start_date': self.date_begin,
            'end_date': self.date_end,
            'state': 'draft',
            'amenity_line_ids': amenity_lines,
        }
        booking = self.env['venue.booking'].create(booking_vals)
        self.venue_booking_id = booking.id

    def action_view_venue_booking(self):
        """Action for smart button to view linked venue booking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Venue Booking'),
            'res_model': 'venue.booking',
            'view_mode': 'form',
            'res_id': self.venue_booking_id.id,
            'target': 'current',
        }
