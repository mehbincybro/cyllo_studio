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

class VenueBooking(models.Model):
    """Inherit venue.booking to integrate transport logistics"""
    _inherit = 'venue.booking'

    need_transport = fields.Boolean(string="Need Transport", help="Check if transport is needed")
    transport_ids = fields.Many2many('transport.booking', string="Transport Bookings")
    transport_count = fields.Integer(string="Transport Count", compute='_compute_transport_count')
    transport_warning = fields.Char(compute='_compute_transport_warning')

    @api.depends('transport_ids', 'guest_count')
    def _compute_transport_count(self):
        """Calculate total transport records (linked + created)"""
        for record in self:
            created_ids = self.env['transport.booking'].search_count([('venue_booking_id', '=', record.id)])
            record.transport_count = len(record.transport_ids) + created_ids

    @api.depends('transport_ids', 'guest_count')
    def _compute_transport_warning(self):
        """Determine if booked transport capacity matches guest count requirements"""
        for record in self:
            linked_ids = record.transport_ids.ids
            created_ids = self.env['transport.booking'].search([('venue_booking_id', '=', record.id)]).ids
            all_transports = self.env['transport.booking'].browse(list(set(linked_ids + created_ids)))
            total_booked = sum(all_transports.mapped('booked_capacity'))
            
            if total_booked > record.guest_count:
                record.transport_warning = _("Warning: The booked transport count (%s) is greater than the total guest count (%s).") % (total_booked, record.guest_count)
            elif total_booked < record.guest_count:
                record.transport_warning = _("Warning: Need more transport bookings. (Booked: %s, Guests: %s)") % (total_booked, record.guest_count)
            else:
                record.transport_warning = False

    def action_create_transport_booking(self):
        """Open form to create a transport booking linked to venue booking."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Transport Booking'),
            'res_model': 'transport.booking',
            'view_mode': 'form',
            'context': {
                'default_venue_booking_id': self.id,
                'default_booked_capacity': self.guest_count,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
            },
            'target': 'new',
        }

    def action_booking_invoice_create(self):
        """Override to add transport charges to the invoice"""
        res = super().action_booking_invoice_create()
        invoice_id = self.env['account.move'].search(
            [('invoice_origin', '=', self.ref), ('state', '=', 'draft')], limit=1)
        if invoice_id:
            linked_ids = self.transport_ids.ids
            created_ids = self.env['transport.booking'].search([('venue_booking_id', '=', self.id)]).ids
            all_transports = self.env['transport.booking'].browse(list(set(linked_ids + created_ids)))
            
            invoice_lines = []
            for transport in all_transports:
                invoice_lines.append((0, 0, {
                    'name': _('Transport charge with %s') % transport.vehicle_id.name,
                    'price_unit': transport.total_amount,
                    'quantity': 1,
                }))
            if invoice_lines:
                invoice_id.write({'invoice_line_ids': invoice_lines})
        return res

    def action_view_transport_booking(self):
        """View all transport bookings linked to the current venue booking."""
        self.ensure_one()
        linked_ids = self.transport_ids.ids
        created_ids = self.env['transport.booking'].search([('venue_booking_id', '=', self.id)]).ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transport Bookings'),
            'res_model': 'transport.booking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', list(set(linked_ids + created_ids)))],
            'target': 'current',
        }

class EventEvent(models.Model):
    """Inherit event.event to integrate transport logistics"""
    _inherit = 'event.event'

    need_transport = fields.Boolean(string="Need Transport", help="Check if transport is needed")
    transport_ids = fields.Many2many('transport.booking', string="Transport Bookings")
    transport_count = fields.Integer(string="Transport Count", compute='_compute_transport_count')

    @api.depends('transport_ids')
    def _compute_transport_count(self):
        """Count transport records associated with the event"""
        for record in self:
            created_ids = self.env['transport.booking'].search_count([('event_id', '=', record.id)])
            record.transport_count = len(record.transport_ids) + created_ids

    def action_create_transport_booking(self):
        """Open form to create a transport booking linked to event."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Transport Booking'),
            'res_model': 'transport.booking',
            'view_mode': 'form',
            'context': {
                'default_event_id': self.id,
                'default_start_date': self.date_begin,
                'default_end_date': self.date_end,
            },
            'target': 'new',
        }

    def action_view_transport_booking(self):
        """View all transport bookings linked to the current event."""
        self.ensure_one()
        linked_ids = self.transport_ids.ids
        created_ids = self.env['transport.booking'].search([('event_id', '=', self.id)]).ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transport Bookings'),
            'res_model': 'transport.booking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', list(set(linked_ids + created_ids)))],
            'target': 'current',
        }
