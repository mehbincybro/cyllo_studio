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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tour_booking_id = fields.Many2one('tour.booking', string='Tour Booking',
                                      compute='_compute_tour_booking_id',
                                      store=True)
    tour_booking_count = fields.Integer(compute='_compute_tour_booking_count',
                                        string='Tour Bookings')

    @api.depends('name')
    def _compute_tour_booking_id(self):
        for order in self:
            booking = self.env['tour.booking'].search(
                [('sale_order_id', '=', order.id)], limit=1)
            order.tour_booking_id = booking.id if booking else False

    def _compute_tour_booking_count(self):
        for order in self:
            order.tour_booking_count = self.env['tour.booking'].search_count([
                ('sale_order_id', '=', order.id)
            ])

    def action_view_tour_booking(self):
        """View related tour booking"""
        self.ensure_one()
        bookings = self.env['tour.booking'].search(
            [('sale_order_id', '=', self.id)])
        if len(bookings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Tour Booking'),
                'res_model': 'tour.booking',
                'res_id': bookings.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tour Bookings'),
            'res_model': 'tour.booking',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'target': 'current',
        }

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Override to update tour booking when invoice is created"""
        invoices = super()._create_invoices(grouped=grouped, final=final,
                                            date=date)
        # Update linked tour bookings
        for order in self:
            bookings = self.env['tour.booking'].search(
                [('sale_order_id', '=', order.id)])
            for booking in bookings:
                booking.sudo()._update_payment_status_from_payments()
        return invoices
