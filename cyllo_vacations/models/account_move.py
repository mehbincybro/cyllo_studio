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


class AccountMove(models.Model):
    _inherit = 'account.move'

    tour_booking_ids = fields.Many2many('tour.booking',
                                        compute='_compute_tour_bookings',
                                        string='Tour Bookings')
    tour_booking_count = fields.Integer(compute='_compute_tour_booking_count',
                                        string='Tour Bookings')

    def _compute_tour_bookings(self):
        for move in self:
            move.tour_booking_ids = self._get_tour_bookings_for_move(move)

    def _compute_tour_booking_count(self):
        for move in self:
            move.tour_booking_count = len(move.tour_booking_ids)

    def _get_tour_bookings_for_move(self, move):
        """Get tour bookings linked through sale orders or directly"""
        bookings = self.env['tour.booking']

        # Find bookings with direct invoice link
        direct_bookings = self.env['tour.booking'].search([
            ('direct_invoice_ids', 'in', move.id)
        ])
        bookings |= direct_bookings

        # Find bookings through sale orders
        if move.invoice_origin:
            sale_orders = self.env['sale.order'].search([
                ('name', '=', move.invoice_origin)
            ])
            for so in sale_orders:
                bookings |= self.env['tour.booking'].search([
                    ('sale_order_id', '=', so.id)
                ])
        return bookings

    def _get_tour_bookings(self):
        """Get tour bookings linked through sale orders or directly"""
        bookings = self.env['tour.booking']
        for move in self:
            bookings |= self._get_tour_bookings_for_move(move)
        return bookings

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

    def write(self, vals):
        """Override to update booking payment status when invoice payment state changes"""
        res = super().write(vals)
        if 'payment_state' in vals or 'amount_residual' in vals or 'state' in vals:
            bookings = self._get_tour_bookings()
            for booking in bookings.sudo():
                booking.invalidate_recordset(
                    ['amount_paid', 'amount_due', 'payment_status'])
                booking._update_payment_status_from_payments()
        if 'payment_state' in vals and vals['payment_state'] == 'paid':
            # Find all commissions linked to vendor bills in this recordset
            commissions = self.env['tour.booking.commission'].search([
                ('vendor_bill_id', 'in', self.ids),
                ('state', '!=', 'paid'),
            ])
            if commissions:
                commissions.write({'state': 'paid'})
                commissions.message_post(
                    body='Commission automatically marked as paid when vendor bill was settled.'
                )
        return res

    def _post(self, soft=True):
        """Override to update booking when invoice is posted"""
        res = super()._post(soft=soft)
        bookings = self._get_tour_bookings()
        for booking in bookings.sudo():
            booking.invalidate_recordset(
                ['amount_paid', 'amount_due', 'payment_status'])
            booking._update_payment_status_from_payments()
        return res

    def button_cancel(self):
        """Override to update booking when invoice is cancelled"""
        res = super().button_cancel()
        bookings = self._get_tour_bookings()
        for booking in bookings.sudo():
            booking.invalidate_recordset(
                ['amount_paid', 'amount_due', 'payment_status'])
            booking._update_payment_status_from_payments()
        return res
