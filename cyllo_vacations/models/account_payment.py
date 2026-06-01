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


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    tour_booking_id = fields.Many2one('tour.booking', string='Tour Booking')

    def action_post(self):
        """Override to update booking when payment is posted"""
        res = super().action_post()
        # Update linked tour bookings
        for payment in self:
            if payment.tour_booking_id:
                booking = payment.tour_booking_id.sudo()
                # Force update payment amounts by invalidating cache and recomputing
                booking.invalidate_recordset(
                    ['amount_paid', 'amount_due', 'payment_status'])
                booking._update_payment_status_from_payments()
        return res

    def action_cancel(self):
        """Override to update booking when payment is cancelled"""
        res = super().action_cancel()
        for payment in self:
            if payment.tour_booking_id:
                booking = payment.tour_booking_id.sudo()
                booking.invalidate_recordset(
                    ['amount_paid', 'amount_due', 'payment_status'])
                booking._update_payment_status_from_payments()
        return res

    def action_draft(self):
        """Override to update booking when payment is set to draft"""
        res = super().action_draft()
        for payment in self:
            if payment.tour_booking_id:
                booking = payment.tour_booking_id.sudo()
                booking.invalidate_recordset(
                    ['amount_paid', 'amount_due', 'payment_status'])
                booking._update_payment_status_from_payments()
        return res
