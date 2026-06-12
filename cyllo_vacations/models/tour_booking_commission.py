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
from odoo.exceptions import UserError


class TourBookingCommission(models.Model):
    _name = 'tour.booking.commission'
    _description = 'Tour Booking Commission'
    _inherit = ['mail.thread']
    _order = 'booking_id desc'

    booking_id = fields.Many2one('tour.booking', required=True, ondelete='cascade',
        string='Booking')
    agent_id = fields.Many2one('tour.agent', required=True, string='Agent')
    rule_id = fields.Many2one('tour.agent.commission.rule', string='Applied Rule',
        readonly=True)
    currency_id = fields.Many2one('res.currency', related='booking_id.currency_id')

    commission_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
    ], readonly=True)
    commission_rate = fields.Float(string='Rate / %', readonly=True,
        help='Fixed amount or percentage used at the time of calculation.')
    booking_amount = fields.Monetary(string='Booking Total at Confirmation',
        currency_field='currency_id', readonly=True,
        help='Snapshot of booking total when commission was calculated.')
    commission_amount = fields.Monetary(string='Commission Amount',
        currency_field='currency_id', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    notes = fields.Text(string='Notes')
    vendor_bill_id = fields.Many2one('account.move', string='Vendor Bill',
                                     readonly=True, copy=False)
    vendor_bill_state = fields.Selection(related='vendor_bill_id.payment_state',
                                         string='Bill Status', readonly=True)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _compute_commission_amount(self, booking_total):
        """Recalculate based on rule. Called before save, not a stored compute."""
        self.ensure_one()
        if self.commission_type == 'fixed':
            return self.commission_rate
        return round(booking_total * self.commission_rate / 100, 2)

    def action_create_vendor_bill(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed commissions can be billed.'))
        if self.vendor_bill_id:
            raise UserError(
                _('A vendor bill already exists for this commission.'))

        # Commission product — configure once in settings
        product = self.env.ref(
            'cyllo_vacations.product_agent_commission',
            raise_if_not_found=False
        ) or self.env['product.product'].search(
            [('name', 'ilike', 'commission')], limit=1
        )

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',  # vendor bill
            'partner_id': self.agent_id.partner_id.id,
            'invoice_date': fields.Date.today(),
            'ref': _('Commission: %s') % self.booking_id.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id if product else False,
                'name': _(
                    'Commission for booking %(ref)s — %(package)s'
                ) % {
                            'ref': self.booking_id.name,
                            'package': self.booking_id.package_name,
                        },
                'quantity': 1,
                'price_unit': self.commission_amount,
            })],
        })
        self.vendor_bill_id = bill.id
        self.message_post(body=_('Vendor bill created: %s', bill.name))
        # Return the bill form view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
        }
