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
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class TourBooking(models.Model):
    _name = 'tour.booking'
    _description = 'Tour Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', ]
    _order = 'booking_date desc, id desc'
    
    name = fields.Char(string='Booking Reference', required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('New'))
    # Customer Information
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, 
                                  tracking=True, index=True)
    customer_name = fields.Char(related='partner_id.name', string='Customer Name', readonly=True)
    customer_email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    customer_phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
    # Package Details
    package_id = fields.Many2one('tour.package', string='Tour Package', required=True,
                                  tracking=True, ondelete='restrict')
    package_name = fields.Char(related='package_id.name', string='Package', readonly=True)
    # Booking Dates
    booking_date = fields.Datetime(string='Booking Date', default=fields.Datetime.now,
                                    required=True, tracking=True)
    travel_start_date = fields.Date(string='Travel Start Date', required=True, tracking=True)
    travel_end_date = fields.Date(string='Travel End Date', compute='_compute_travel_end_date',
                                   store=True, tracking=True)
    # Passengers
    num_adults = fields.Integer(string='Adults', default=1, required=True)
    num_children = fields.Integer(string='Children', default=0)
    num_infants = fields.Integer(string='Infants', default=0)
    total_persons = fields.Integer(compute='_compute_total_persons', string='Total Persons',
                                    store=True)
    passenger_ids = fields.One2many('tour.passenger', 'booking_id', string='Passengers')
    passenger_count = fields.Integer(compute='_compute_passenger_count', string='Passenger Count')
    # Pricing
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_amounts',
                                      store=True, currency_field='currency_id')
    price_tax = fields.Monetary(string='Tax', compute='_compute_amounts',
                                 store=True, currency_field='currency_id')
    price_total = fields.Monetary(string='Total', compute='_compute_amounts',
                                   store=True, currency_field='currency_id')
    adult_price = fields.Monetary(string='Adult Price', currency_field='currency_id')
    child_price = fields.Monetary(string='Child Price', currency_field='currency_id')
    infant_price = fields.Monetary(string='Infant Price', currency_field='currency_id')
    discount_amount = fields.Monetary(string='Discount', currency_field='currency_id')
    discount_percentage = fields.Float(string='Discount %')
    applied_rules_desc = fields.Text(string='Applied Pricing Rules', readonly=True)
    extra_charges = fields.Monetary(string='Extra Charges', currency_field='currency_id')
    extra_charges_note = fields.Text(string='Extra Charges Note')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id,
                                   required=True)
    # Payment - These fields are computed but can also be written directly when payments are made
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('refunded', 'Refunded'),
    ], string='Payment Status', default='unpaid', compute='_compute_payment_status',
        store=True, tracking=True, readonly=False)
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id',
                                   compute='_compute_payment_amounts', store=True, readonly=False)
    amount_due = fields.Monetary(string='Amount Due', currency_field='currency_id',
                                  compute='_compute_payment_amounts', store=True, readonly=False)
    payment_ids = fields.One2many('account.payment', 'tour_booking_id', string='Payments')
    payment_count = fields.Integer(compute='_compute_payment_count', string='Payments')
    # Sales Order Integration
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True, copy=False)
    # Invoice Integration
    direct_invoice_ids = fields.Many2many('account.move', 'tour_booking_invoice_rel', 
                                           'booking_id', 'invoice_id',
                                           string='Direct Invoices', copy=False)
    invoice_ids = fields.Many2many('account.move', compute='_compute_invoice_ids',
                                    string='Invoices', copy=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoices')
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)
    # Cancellation Policy
    cancellation_date = fields.Date(string='Cancellation Date', readonly=True,
                                    copy=False,
                                    tracking=True)
    cancellation_fee = fields.Monetary(string='Cancellation Fee',
                                       currency_field='currency_id',
                                       readonly=True, copy=False, tracking=True,
                                       help='Fee charged on cancellation, computed from the '
                                            'company cancellation policy.')
    cancellation_fee_percent = fields.Float(string='Cancellation Fee %',
                                            readonly=True,
                                            copy=False,
                                            help='Percentage used to compute the cancellation fee.')
    # Additional Services
    hotel_ids = fields.Many2many('tour.hotel', string='Hotels')
    transportation_ids = fields.Many2many('tour.transportation', string='Transportation')
    meal_ids = fields.Many2many('tour.meal', string='Meals')
    attraction_ids = fields.Many2many('tour.attraction', string='Attractions')
    # Expenses
    expense_ids = fields.One2many('tour.expense', 'booking_id', string='Expenses')
    total_expenses = fields.Monetary(compute='_compute_total_expenses', string='Total Expenses',
                                      currency_field='currency_id')
    # Notes and Requirements
    customer_notes = fields.Text(string='Customer Notes')
    special_requirements = fields.Text(string='Special Requirements')
    internal_notes = fields.Text(string='Internal Notes')
    # Inquiry Reference
    inquiry_id = fields.Many2one('tour.inquiry', string='Related Inquiry', readonly=True)
    # Assignment
    user_id = fields.Many2one('res.users', string='Responsible', tracking=True,
                              default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', string='Sales Team', tracking=True)
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company, required=True)
    # Source
    source = fields.Selection([
        ('website', 'Website'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('walk_in', 'Walk-in'),
        ('referral', 'Referral'),
        ('agent', 'Travel Agent'),
        ('other', 'Other'),
    ], string='Source')
    # Calendar Event
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event')
    # Portal Access
    access_token = fields.Char(string='Access Token', copy=False)
    
    @api.depends('package_id', 'travel_start_date')
    def _compute_travel_end_date(self):
        for record in self:
            if record.travel_start_date and record.package_id:
                days = record.package_id.duration_days - 1
                record.travel_end_date = record.travel_start_date + timedelta(days=days)
            else:
                record.travel_end_date = False
    
    @api.depends('num_adults', 'num_children', 'num_infants')
    def _compute_total_persons(self):
        for record in self:
            record.total_persons = record.num_adults + record.num_children + record.num_infants
    
    @api.depends('passenger_ids')
    def _compute_passenger_count(self):
        for record in self:
            record.passenger_count = len(record.passenger_ids)
    
    @api.depends('num_adults', 'num_children', 'num_infants', 'adult_price', 'child_price',
                 'infant_price', 'discount_amount', 'discount_percentage', 'extra_charges')
    def _compute_amounts(self):
        for record in self:
            subtotal = 0
            if record.package_id.price_type == 'per_person':
                subtotal += record.num_adults * record.adult_price
                subtotal += record.num_children * record.child_price
                subtotal += record.num_infants * record.infant_price
            else:
                subtotal = record.adult_price
            # Apply discount
            if record.discount_percentage:
                subtotal -= subtotal * (record.discount_percentage / 100)
            else:
                subtotal -= record.discount_amount
            # Add extra charges
            subtotal += record.extra_charges
            record.price_subtotal = subtotal
            # Simplified tax calculation - can be enhanced
            record.price_tax = 0
            record.price_total = subtotal
    
    @api.depends('payment_ids', 'payment_ids.state', 'price_total', 'invoice_ids', 'invoice_ids.payment_state', 'amount_paid')
    def _compute_payment_status(self):
        for record in self:
            if not record.price_total:
                record.payment_status = 'unpaid'
            elif record.amount_paid >= record.price_total:
                record.payment_status = 'paid'
            elif record.amount_paid > 0:
                record.payment_status = 'partially_paid'
            else:
                record.payment_status = 'unpaid'
    
    @api.depends('payment_ids', 'payment_ids.amount', 'payment_ids.state', 'price_total', 
                 'invoice_ids', 'invoice_ids.amount_residual', 'invoice_ids.state')
    def _compute_payment_amounts(self):
        for record in self:
            # Calculate from direct payments
            direct_paid = sum(record.payment_ids.filtered(
                lambda p: p.state == 'posted').mapped('amount'))
            # Calculate from invoice payments (for sale order integration)
            invoice_paid = 0
            if record.invoice_ids:
                for invoice in record.invoice_ids.filtered(lambda i: i.state == 'posted'):
                    invoice_paid += invoice.amount_total - invoice.amount_residual
            record.amount_paid = direct_paid + invoice_paid
            record.amount_due = max(0, record.price_total - record.amount_paid)
    
    def _update_payment_status_from_payments(self):
        """Force update payment amounts and status - called after payment changes"""
        for record in self:
            # Store old values to detect changes
            old_amount_paid = record.amount_paid
            old_payment_status = record.payment_status
            # Calculate from direct payments to this booking
            direct_paid = 0.0
            for payment in record.payment_ids.filtered(lambda p: p.state == 'posted'):
                # Handle currency conversion if needed
                if payment.currency_id == record.currency_id:
                    direct_paid += payment.amount
                else:
                    direct_paid += payment.currency_id._convert(
                        payment.amount,
                        record.currency_id,
                        record.company_id,
                        payment.date or fields.Date.today()
                    )
            # Calculate from invoice payments (for sale order integration)
            invoice_paid = 0.0
            # Get all related invoices (direct and from sale order)
            invoices = record.direct_invoice_ids
            if record.sale_order_id:
                invoices |= record.sale_order_id.invoice_ids
            for invoice in invoices.filtered(lambda i: i.state == 'posted'):
                # Amount paid on invoice = total - residual
                paid_on_invoice = invoice.amount_total - invoice.amount_residual
                # Handle currency conversion if needed
                if invoice.currency_id == record.currency_id:
                    invoice_paid += paid_on_invoice
                else:
                    invoice_paid += invoice.currency_id._convert(
                        paid_on_invoice,
                        record.currency_id,
                        record.company_id,
                        invoice.invoice_date or fields.Date.today()
                    )
            total_paid = direct_paid + invoice_paid
            amount_due = max(0.0, record.price_total - total_paid)
            # Determine payment status
            if not record.price_total or record.price_total <= 0:
                payment_status = 'unpaid'
            elif total_paid >= record.price_total:
                payment_status = 'paid'
            elif total_paid > 0:
                payment_status = 'partially_paid'
            else:
                payment_status = 'unpaid'
            # Only update if values changed
            if (abs(total_paid - old_amount_paid) > 0.01 or 
                payment_status != old_payment_status):
                # Write directly to update stored fields
                record.with_context(skip_payment_update=True).write({
                    'amount_paid': total_paid,
                    'amount_due': amount_due,
                    'payment_status': payment_status,
                })
                currency_symbol = record.currency_id.symbol or ''
                record.message_post(
                    body=_('Payment status updated:<br/>'
                           '• Amount Paid: %s %s<br/>'
                           '• Amount Due: %s %s<br/>'
                           '• Status: %s') % (
                        currency_symbol, 
                        '{:,.2f}'.format(total_paid),
                        currency_symbol,
                        '{:,.2f}'.format(amount_due),
                        payment_status.replace('_', ' ').title()
                    )
                )
                # Auto-confirm if configured and payment meets minimum requirement
                if record.state == 'draft' and record.company_id.tour_auto_confirm_booking:
                    min_percent = record.company_id.tour_minimum_payment_percent or 0
                    if min_percent > 0:
                        required_amount = record.price_total * min_percent / 100
                        if total_paid >= required_amount:
                            record.action_confirm()
                    elif payment_status == 'paid':
                        record.action_confirm()
    
    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for record in self:
            record.payment_count = len(record.payment_ids)
    
    @api.depends('sale_order_id', 'sale_order_id.invoice_ids', 'direct_invoice_ids')
    def _compute_invoice_ids(self):
        for record in self:
            invoices = record.direct_invoice_ids
            if record.sale_order_id:
                invoices |= record.sale_order_id.invoice_ids
            record.invoice_ids = invoices
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)
    
    @api.depends('expense_ids', 'expense_ids.amount')
    def _compute_total_expenses(self):
        for record in self:
            record.total_expenses = sum(record.expense_ids.mapped('amount'))
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tour.booking') or _('New')
            # Set prices and services from package
            if vals.get('package_id'):
                package = self.env['tour.package'].browse(vals['package_id'])
                if not vals.get('adult_price'):
                    vals['adult_price'] = package.adult_price or package.base_price
                    vals['child_price'] = package.child_price or 0
                    vals['infant_price'] = package.infant_price or 0
                if 'hotel_ids' not in vals:
                    vals['hotel_ids'] = [(6, 0, package.hotel_ids.ids)]
                if 'transportation_ids' not in vals:
                    vals['transportation_ids'] = [(6, 0, package.transportation_ids.ids)]
                if 'meal_ids' not in vals:
                    vals['meal_ids'] = [(6, 0, package.meal_ids.ids)]
                if 'attraction_ids' not in vals:
                    vals['attraction_ids'] = [(6, 0, package.attraction_ids.ids)]
        bookings = super().create(vals_list)
        for booking in bookings:
            # Generate access token for portal
            booking._portal_ensure_token()
            # Send confirmation email
            if booking.state == 'confirmed':
                booking._send_booking_confirmation()
            # Create calendar event
            if booking.company_id.tour_create_calendar_event:
                booking._create_calendar_event()
        
        return bookings
    
    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            for booking in self:
                if vals['state'] == 'confirmed':
                    booking._send_booking_confirmation()
        return res
    
    def _send_booking_confirmation(self):
        """Send booking confirmation email"""
        self.ensure_one()
        template = self.env.ref('cyllo_vacations.email_template_booking_confirmation',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _create_calendar_event(self):
        """Create calendar event for the tour"""
        self.ensure_one()
        if not self.calendar_event_id:
            event_vals = {
                'name': f"Tour: {self.package_name} - {self.customer_name}",
                'start': datetime.combine(self.travel_start_date, datetime.min.time()),
                'stop': datetime.combine(self.travel_end_date, datetime.max.time()),
                'allday': True,
                'description': f"Booking: {self.name}\nCustomer: {self.customer_name}\nPackage: {self.package_name}\nPersons: {self.total_persons}",
                'user_id': self.user_id.id,
                'partner_ids': [(4, self.partner_id.id)],
            }
            event = self.env['calendar.event'].create(event_vals)
            self.calendar_event_id = event.id
    
    def action_confirm(self):
        """Confirm booking and related documents"""
        self.write({'state': 'confirmed'})
        for booking in self:
            # Create and confirm sale order if configured
            if booking.company_id.tour_create_sale_order:
                booking._create_sale_order()
                # Confirm the sale order
                if booking.sale_order_id and booking.sale_order_id.state == 'draft':
                    booking.sale_order_id.action_confirm()
            # Create calendar event if configured
            if booking.company_id.tour_create_calendar_event and not booking.calendar_event_id:
                booking._create_calendar_event()
            # Update CRM lead if linked through inquiry
            if booking.inquiry_id and booking.inquiry_id.lead_id:
                lead = booking.inquiry_id.lead_id
                if lead.stage_id:
                    # Try to move to won stage
                    won_stage = self.env['crm.stage'].search([
                        ('is_won', '=', True),
                        '|', ('team_id', '=', lead.team_id.id), ('team_id', '=', False)
                    ], limit=1)
                    if won_stage:
                        lead.write({
                            'stage_id': won_stage.id,
                            'expected_revenue': booking.price_total,
                        })

    def action_start(self):
        """Start tour and update related documents"""
        self.write({'state': 'in_progress'})
        for booking in self:
            # Update calendar event
            if booking.calendar_event_id:
                booking.calendar_event_id.write({
                    'name': f"[IN PROGRESS] Tour: {booking.package_name} - {booking.customer_name}",
                })

            # Send tour start notification
            booking._send_tour_start_notification()
    
    def action_complete(self):
        """Complete tour and finalize related documents"""
        self.write({'state': 'completed'})
        for booking in self:
            # Create invoice if sale order exists and not yet invoiced
            if booking.sale_order_id and not booking.invoice_ids:
                booking._create_invoice_from_sale_order()
            # Update calendar event
            if booking.calendar_event_id:
                booking.calendar_event_id.write({
                    'name': f"[COMPLETED] Tour: {booking.package_name} - {booking.customer_name}",
                })
            
            # Send completion notification
            booking._send_tour_completion_notification()

    def _compute_cancellation_fee(self):
        """Return (days_notice, fee_amount, fee_percent, is_late) for this booking.

        Days notice  = today − travel_start_date (negative means travel is in the future).
        The fee is only applicable when travel_start_date is known and the booking has a
        non-zero price_total.  When the company's tour_cancellation_days == 0 the policy
        is disabled and fee is always 0.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        company = self.company_id
        if not self.travel_start_date or not self.price_total:
            return 0, 0.0, 0.0, False
        days_notice = (self.travel_start_date - today).days  # positive = future
        cancellation_days = company.tour_cancellation_days or 0
        fee_percent = company.tour_cancellation_fee_percent or 0.0
        # Policy disabled when cancellation_days == 0
        if cancellation_days == 0:
            return days_notice, 0.0, 0.0, False
        # Late cancellation = customer gave fewer days notice than required
        is_late = days_notice < cancellation_days
        if is_late and fee_percent > 0:
            fee_amount = round(self.price_total * fee_percent / 100.0, 2)
        else:
            fee_amount = 0.0

        return days_notice, fee_amount, fee_percent, is_late

    def action_cancel(self):
        """Cancel booking, enforce cancellation policy, and update related documents."""
        for booking in self:
            days_notice, fee_amount, fee_percent, is_late = booking._compute_cancellation_fee()
            company = booking.company_id
            cancellation_days = company.tour_cancellation_days or 0
            today = fields.Date.context_today(booking)
            # ------------------------------------------------------------------
            # 1. Cancellation notice-period warning (non-blocking for staff)
            # ------------------------------------------------------------------
            if cancellation_days > 0 and booking.travel_start_date:
                if is_late:
                    booking.message_post(body=Markup(_(
                        "<b>Late Cancellation:</b> This booking was cancelled with only "
                        "<b>%(days)d day(s)</b> notice. The policy requires at least "
                        "<b>%(required)d day(s)</b> notice before the travel date "
                        "(%(travel)s)."
                    )) % {
                                                  'days': days_notice if days_notice >= 0 else 0,
                                                  'required': cancellation_days,
                                                  'travel': booking.travel_start_date,
                                              })
                else:
                    booking.message_post(body=Markup(_(
                        "<b>Cancellation notice:</b> %(days)d day(s) given — "
                        "within the required %(required)d-day notice period."
                    )) % {
                                                  'days': days_notice,
                                                  'required': cancellation_days,
                                              })
            # ------------------------------------------------------------------
            # 2. Cancellation fee — record on the booking and post to chatter
            # ------------------------------------------------------------------
            fee_vals = {}
            if fee_amount > 0:
                fee_vals['cancellation_fee'] = fee_amount
                fee_vals['cancellation_fee_percent'] = fee_percent
                booking.message_post(body=Markup(_(
                    "<b>Cancellation Fee Applied:</b> %(sym)s %(fee).2f "
                    "(%(pct).1f%% of total %(sym)s %(total).2f). "
                    "Create a credit note or refund for the net refundable amount."
                )) % {
                                              'sym': booking.currency_id.symbol or '',
                                              'fee': fee_amount,
                                              'pct': fee_percent,
                                              'total': booking.price_total,
                                          })
            else:
                fee_vals['cancellation_fee'] = 0.0
                fee_vals['cancellation_fee_percent'] = 0.0
                if cancellation_days > 0 and booking.amount_paid > 0:
                    booking.message_post(body=_(
                        "No cancellation fee applies. Full refund of paid amount is due."
                    ))

            fee_vals['cancellation_date'] = today
            booking.write(fee_vals)
            # ------------------------------------------------------------------
            # 3. Cancel related Sale Order
            # ------------------------------------------------------------------
            if booking.sale_order_id and booking.sale_order_id.state not in [
                'done', 'cancel']:
                booking.sale_order_id.action_cancel()
            # ------------------------------------------------------------------
            # 4. Cancel related Calendar Event
            # ------------------------------------------------------------------
            if booking.calendar_event_id:
                booking.calendar_event_id.unlink()
                booking.calendar_event_id = False
            # ------------------------------------------------------------------
            # 5. Cancel related draft Invoices
            # ------------------------------------------------------------------
            for invoice in booking.invoice_ids.filtered(
                    lambda i: i.state == 'draft'):
                invoice.button_cancel()
            # ------------------------------------------------------------------
            # 6. Update linked CRM Lead
            # ------------------------------------------------------------------
            if booking.inquiry_id and booking.inquiry_id.lead_id:
                lead = booking.inquiry_id.lead_id
                lead.message_post(
                    body=_('Related tour booking %s was cancelled.',
                           booking.name))
            # ------------------------------------------------------------------
            # 7. Send cancellation email to customer
            # ------------------------------------------------------------------
            booking._send_booking_cancellation()

        self.write({'state': 'cancel'})

    def _send_booking_cancellation(self):
        """Send cancellation notification email to the customer."""
        self.ensure_one()
        template = self.env.ref(
            'cyllo_vacations.email_template_booking_cancellation',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=False)
    
    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
    
    def _create_invoice_from_sale_order(self):
        """Create invoice from sale order"""
        self.ensure_one()
        if self.sale_order_id and self.sale_order_id.state == 'sale':
            # Create invoice
            invoice = self.sale_order_id._create_invoices()
            if invoice:
                self.message_post(body=_('Invoice created from Sale Order: %s', invoice.name))
    
    def _send_tour_start_notification(self):
        """Send tour start notification"""
        self.ensure_one()
        template = self.env.ref('cyllo_vacations.email_template_tour_start',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _send_tour_completion_notification(self):
        """Send tour completion notification"""
        self.ensure_one()
        template = self.env.ref('cyllo_vacations.email_template_tour_completion',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _create_sale_order(self):
        """Create sale order from booking with comprehensive data"""
        self.ensure_one()
        if not self.sale_order_id:
            # Create sale order lines
            order_lines = []
            # Get product - use package product or default
            product = self.package_id.product_id
            if not product:
                product = self.env.ref('cyllo_vacations.product_tour_booking', raise_if_not_found=False)
            if product:
                # Build detailed description
                description_lines = [
                    f"Tour Package: {self.package_name}",
                    f"Destination: {self.package_id.destination}",
                    f"Duration: {self.package_id.duration_days} Days / {self.package_id.duration_nights} Nights",
                    f"Travel Date: {self.travel_start_date} to {self.travel_end_date}",
                ]
                # Add passenger details
                passenger_names = ', '.join(self.passenger_ids.mapped('name')) if self.passenger_ids else ''
                if passenger_names:
                    description_lines.append(f"Passengers: {passenger_names}")
                base_description = '\n'.join(description_lines)
                # Main tour package lines
                if self.package_id.price_type == 'per_person':
                    # Add separate lines for adults, children, infants
                    if self.num_adults:
                        order_lines.append((0, 0, {
                            'product_id': product.id,
                            'name': f"{self.package_name} - Adult x{self.num_adults}\n{base_description}",
                            'product_uom_qty': self.num_adults,
                            'price_unit': self.adult_price,
                        }))
                    if self.num_children and self.child_price:
                        order_lines.append((0, 0, {
                            'product_id': product.id,
                            'name': f"{self.package_name} - Child x{self.num_children}",
                            'product_uom_qty': self.num_children,
                            'price_unit': self.child_price,
                        }))
                    if self.num_infants and self.infant_price:
                        order_lines.append((0, 0, {
                            'product_id': product.id,
                            'name': f"{self.package_name} - Infant x{self.num_infants}",
                            'product_uom_qty': self.num_infants,
                            'price_unit': self.infant_price,
                        }))
                else:
                    # Per package pricing
                    order_lines.append((0, 0, {
                        'product_id': product.id,
                        'name': f"{self.package_name}\n{base_description}",
                        'product_uom_qty': 1,
                        'price_unit': self.price_subtotal,
                    }))
                # Add hotel services as note lines (details only)
                if self.hotel_ids:
                    hotel_details = []
                    for hotel in self.hotel_ids:
                        stars = '⭐' * (hotel.star_rating or 0) if hasattr(hotel, 'star_rating') else ''
                        hotel_details.append(f"• {hotel.name} {stars}")
                        if hotel.address:
                            hotel_details.append(f"  Address: {hotel.address}")
                    order_lines.append((0, 0, {
                        'display_type': 'line_note',
                        'name': f"ACCOMMODATIONS:\n" + '\n'.join(hotel_details),
                    }))
                # Add transportation services as note lines
                if self.transportation_ids:
                    transport_details = []
                    for transport in self.transportation_ids:
                        transport_details.append(f"• {transport.name} ({transport.transport_type or 'N/A'})")
                    order_lines.append((0, 0, {
                        'display_type': 'line_note',
                        'name': f"TRANSPORTATION:\n" + '\n'.join(transport_details),
                    }))
                # Add meals as note lines
                if self.meal_ids:
                    meal_details = []
                    for meal in self.meal_ids:
                        meal_type = meal.meal_type.title() if hasattr(meal, 'meal_type') and meal.meal_type else 'N/A'
                        meal_details.append(f"• {meal.name} ({meal_type})")
                    order_lines.append((0, 0, {
                        'display_type': 'line_note',
                        'name': f"MEALS INCLUDED:\n" + '\n'.join(meal_details),
                    }))
                # Add attractions as note lines
                if self.attraction_ids:
                    attraction_details = []
                    for attraction in self.attraction_ids:
                        attraction_details.append(f"• {attraction.name}")
                        if hasattr(attraction, 'location') and attraction.location:
                            attraction_details.append(f"  Location: {attraction.location}")
                    order_lines.append((0, 0, {
                        'display_type': 'line_note',
                        'name': f"ATTRACTIONS & ACTIVITIES:\n" + '\n'.join(attraction_details),
                    }))
                # Extra charges line
                if self.extra_charges:
                    order_lines.append((0, 0, {
                        'product_id': product.id,
                        'name': f"Extra Charges: {self.extra_charges_note or 'Additional Services'}",
                        'product_uom_qty': 1,
                        'price_unit': self.extra_charges,
                    }))
                # Discount line (as negative)
                if self.discount_amount and self.discount_amount > 0:
                    order_lines.append((0, 0, {
                        'product_id': product.id,
                        'name': f"Discount ({self.discount_percentage}%)" if self.discount_percentage else _('Discount'),
                        'product_uom_qty': 1,
                        'price_unit': -self.discount_amount,
                    }))
            # Build comprehensive note
            note_parts = [
                f"TOUR BOOKING DETAILS",
                f"Booking Reference: {self.name}",
                f"Package: {self.package_name}",
                f"Destination: {self.package_id.destination}",
                f"Travel Period: {self.travel_start_date} to {self.travel_end_date}",
                f"Duration: {self.package_id.duration_days} Days / {self.package_id.duration_nights} Nights",
                f"",
                f"TRAVELERS:",
                f"Adults: {self.num_adults}",
                f"Children: {self.num_children}",
                f"Infants: {self.num_infants}",
                f"Total: {self.total_persons} persons",
            ]
            # Add passenger details if available
            if self.passenger_ids:
                note_parts.append(f"\nPASSENGER LIST:")
                for idx, passenger in enumerate(self.passenger_ids, 1):
                    note_parts.append(f"  {idx}. {passenger.name} ({passenger.passenger_type}) - {passenger.gender or 'N/A'}")
            # Add special requirements
            if self.special_requirements:
                note_parts.append(f"\nSPECIAL REQUIREMENTS:\n{self.special_requirements}")
            if self.customer_notes:
                note_parts.append(f"\nCUSTOMER NOTES:\n{self.customer_notes}")
            order_vals = {
                'partner_id': self.partner_id.id,
                'partner_invoice_id': self.partner_id.id,
                'partner_shipping_id': self.partner_id.id,
                'date_order': self.booking_date,
                'validity_date': self.travel_start_date,
                'user_id': self.user_id.id,
                'team_id': self.team_id.id if self.team_id else False,
                'order_line': order_lines,
                'client_order_ref': self.name,
                'note': '\n'.join(note_parts),
                'currency_id': self.currency_id.id,
            }
            sale_order = self.env['sale.order'].create(order_vals)
            self.sale_order_id = sale_order.id
            self.message_post(body=_('Sale Order created: %s', sale_order.name))
    
    def action_view_sale_order(self):
        """View related sale order"""
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_sale_order(self):
        """Manually create sale order from booking"""
        self.ensure_one()
        if self.sale_order_id:
            raise UserError(_('A Sale Order already exists for this booking.'))
        self._create_sale_order()
        if self.sale_order_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Sale Order'),
                'res_model': 'sale.order',
                'res_id': self.sale_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return True
    
    def action_view_invoices(self):
        """View related invoices"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'default_move_type': 'out_invoice'},
        }
    
    def action_view_payments(self):
        """View related payments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments'),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('tour_booking_id', '=', self.id)],
            'context': {
                'default_tour_booking_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_payment_type': 'inbound',
            },
        }
    
    def action_view_passengers(self):
        """View passengers"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Passengers'),
            'res_model': 'tour.passenger',
            'view_mode': 'list,form',
            'domain': [('booking_id', '=', self.id)],
            'context': {'default_booking_id': self.id},
        }
    
    def action_register_payment(self):
        """Register payment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Payment'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_type': 'inbound',
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_due,
                'default_tour_booking_id': self.id,
                'default_ref': self.name,
            },
        }
    
    def action_refresh_payment_status(self):
        """Manually refresh payment status from all linked payments and invoices"""
        for record in self:
            record._update_payment_status_from_payments()
        return True
    
    def action_create_invoice(self):
        """Create invoice directly from booking with comprehensive data"""
        self.ensure_one()
        if self.invoice_ids:
            raise UserError(_('Invoice already exists for this booking.'))
        # Create invoice lines
        invoice_lines = []
        # Main booking line
        product = self.package_id.product_id
        if not product:
            # Use a default service product if no product linked
            product = self.env.ref('cyllo_vacations.product_tour_booking', raise_if_not_found=False)
            if not product:
                raise UserError(_('Please configure a product for the tour package or create a default tour booking product.'))
        # Build detailed description
        description_lines = [
            f"Tour Package: {self.package_name}",
            f"Booking Reference: {self.name}",
            f"Destination: {self.package_id.destination}",
            f"Duration: {self.package_id.duration_days} Days / {self.package_id.duration_nights} Nights",
            f"Travel Date: {self.travel_start_date} to {self.travel_end_date}",
        ]
        # Add passenger names
        if self.passenger_ids:
            passenger_names = ', '.join(self.passenger_ids.mapped('name'))
            description_lines.append(f"Passengers: {passenger_names}")
        base_description = '\n'.join(description_lines)
        # Main tour package lines based on pricing type
        if self.package_id.price_type == 'per_person':
            # Add separate lines for adults, children, infants
            if self.num_adults:
                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f"{self.package_name} - Adult\n{base_description}",
                    'quantity': self.num_adults,
                    'price_unit': self.adult_price,
                }))
            if self.num_children and self.child_price:
                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f"{self.package_name} - Child",
                    'quantity': self.num_children,
                    'price_unit': self.child_price,
                }))
            if self.num_infants and self.infant_price:
                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f"{self.package_name} - Infant",
                    'quantity': self.num_infants,
                    'price_unit': self.infant_price,
                }))
        else:
            # Per package pricing
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': f"{self.package_name}\n{base_description}",
                'quantity': 1,
                'price_unit': self.price_subtotal,
            }))
        
        # Add hotel information as note
        if self.hotel_ids:
            hotel_names = ', '.join(self.hotel_ids.mapped('name'))
            invoice_lines.append((0, 0, {
                'display_type': 'line_note',
                'name': f"Hotels: {hotel_names}",
            }))
        # Add transportation information as note
        if self.transportation_ids:
            transport_names = ', '.join(self.transportation_ids.mapped('name'))
            invoice_lines.append((0, 0, {
                'display_type': 'line_note',
                'name': f"Transportation: {transport_names}",
            }))
        # Add meals information as note
        if self.meal_ids:
            meal_names = ', '.join(self.meal_ids.mapped('name'))
            invoice_lines.append((0, 0, {
                'display_type': 'line_note',
                'name': f"Meals: {meal_names}",
            }))
        # Add attractions information as note
        if self.attraction_ids:
            attraction_names = ', '.join(self.attraction_ids.mapped('name'))
            invoice_lines.append((0, 0, {
                'display_type': 'line_note',
                'name': f"Attractions: {attraction_names}",
            }))
        # Extra charges line if any
        if self.extra_charges:
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': f"Extra Charges: {self.extra_charges_note or 'Additional Services'}",
                'quantity': 1,
                'price_unit': self.extra_charges,
            }))
        # Discount line (as negative)
        if self.discount_amount and self.discount_amount > 0:
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': f"Discount ({self.discount_percentage}%)" if self.discount_percentage else _('Discount'),
                'quantity': 1,
                'price_unit': -self.discount_amount,
            }))
        # Build comprehensive narration
        narration_parts = [
            f"═══════════════════════════════════════",
            f"TOUR BOOKING INVOICE",
            f"═══════════════════════════════════════",
            f"Booking Reference: {self.name}",
            f"Package: {self.package_name}",
            f"Destination: {self.package_id.destination}",
            f"Travel Period: {self.travel_start_date} to {self.travel_end_date}",
            f"Duration: {self.package_id.duration_days} Days / {self.package_id.duration_nights} Nights",
            f"",
            f"TRAVELERS: {self.num_adults} Adults, {self.num_children} Children, {self.num_infants} Infants",
            f"Total Persons: {self.total_persons}",
        ]
        if self.passenger_ids:
            narration_parts.append(f"\nPASSENGER LIST:")
            for idx, passenger in enumerate(self.passenger_ids, 1):
                narration_parts.append(f"  {idx}. {passenger.name} ({passenger.passenger_type})")
        if self.special_requirements:
            narration_parts.append(f"\nSPECIAL REQUIREMENTS:\n{self.special_requirements}")
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': self.travel_start_date,
            'invoice_line_ids': invoice_lines,
            'invoice_origin': self.name,
            'ref': self.name,
            'narration': '\n'.join(narration_parts),
            'currency_id': self.currency_id.id,
        }
        invoice = self.env['account.move'].create(invoice_vals)
        # Link invoice to booking
        self.direct_invoice_ids = [(4, invoice.id)]
        self.message_post(body=_('Invoice created: %s', invoice.name))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _compute_access_url(self):
        """Compute portal access URL"""
        super()._compute_access_url()
        for booking in self:
            booking.access_url = f'/my/bookings/{booking.id}'
    
    @api.constrains('num_adults', 'num_children', 'num_infants', 'package_id', 'travel_start_date', 'state')
    def _check_persons(self):
        for record in self:
            if record.state == 'cancel':
                continue
            if record.total_persons < 1:
                raise ValidationError(_('At least one person is required for booking.'))
            if record.package_id.min_persons and record.total_persons < record.package_id.min_persons:
                raise ValidationError(_('Minimum %s persons required for this package.', 
                                       record.package_id.min_persons))
            if record.package_id.max_persons:
                domain = [
                    ('package_id', '=', record.package_id.id),
                    ('travel_start_date', '=', record.travel_start_date),
                    ('state', '!=', 'cancel'),
                ]
                booked_total = sum(self.env['tour.booking'].search(domain).mapped('total_persons'))
                if booked_total > record.package_id.max_persons:
                    raise ValidationError(_(
                        'The maximum capacity for this package is %(max)s persons. '
                        'Currently, %(booked)s persons are booked for %(date)s (including this booking).', 
                        max=record.package_id.max_persons,
                        booked=booked_total,
                        date=record.travel_start_date
                    ))
    
    @api.constrains('travel_start_date', 'package_id')
    def _check_availability(self):
        for record in self:
            if record.travel_start_date and record.package_id:
                if record.package_id.available_from and record.travel_start_date < record.package_id.available_from:
                    raise ValidationError(_('Package not available for selected date. Available from: %s',
                                           record.package_id.available_from))
                if record.package_id.available_to and record.travel_start_date > record.package_id.available_to:
                    raise ValidationError(_('Package not available for selected date. Available until: %s',
                                           record.package_id.available_to))
    
    @api.onchange('package_id')
    def _onchange_package_id(self):
        if self.package_id:
            self.adult_price = self.package_id.adult_price or self.package_id.base_price
            self.child_price = self.package_id.child_price or 0
            self.infant_price = self.package_id.infant_price or 0
            self.hotel_ids = self.package_id.hotel_ids
            self.transportation_ids = self.package_id.transportation_ids
            self.meal_ids = self.package_id.meal_ids
            self.attraction_ids = self.package_id.attraction_ids
    
    def action_sync_to_sale_order(self):
        """Sync booking data to sale order"""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No Sale Order linked to this booking.'))
        # Update sale order fields
        self.sale_order_id.write({
            'client_order_ref': self.name,
        })
        
        self.message_post(body=_('Sale Order %s synchronized.', self.sale_order_id.name))
        return True
    
    def action_apply_payment_to_invoice(self):
        """Apply booking payment to related invoice"""
        self.ensure_one()
        # Get unpaid invoices
        unpaid_invoices = self.invoice_ids.filtered(
            lambda inv: inv.payment_state not in ['paid', 'reversed'] and inv.state == 'posted'
        )
        if not unpaid_invoices:
            raise UserError(_('No unpaid posted invoices found.'))
        # Get unapplied payments
        unapplied_payments = self.payment_ids.filtered(
            lambda p: p.state == 'posted' and not p.reconciled_invoices_count
        )
        if not unapplied_payments:
            raise UserError(_('No unapplied payments found.'))
        # Apply payments to invoices (reconciliation)
        for payment in unapplied_payments:
            for invoice in unpaid_invoices:
                if invoice.amount_residual > 0:
                    # Find matching lines for reconciliation
                    payment_lines = payment.line_ids.filtered(
                        lambda l: l.account_type in ['asset_receivable', 'liability_payable'] and not l.reconciled
                    )
                    invoice_lines = invoice.line_ids.filtered(
                        lambda l: l.account_type in ['asset_receivable', 'liability_payable'] and not l.reconciled
                    )
                    
                    if payment_lines and invoice_lines:
                        (payment_lines + invoice_lines).reconcile()
        
        self.message_post(body=_('Payments applied to invoices.'))
        return True
    
    def action_view_calendar_event(self):
        """View related calendar event"""
        self.ensure_one()
        if self.calendar_event_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Calendar Event'),
                'res_model': 'calendar.event',
                'res_id': self.calendar_event_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False
    
    def action_view_lead(self):
        """View related CRM lead"""
        self.ensure_one()
        if self.inquiry_id and self.inquiry_id.lead_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('CRM Lead'),
                'res_model': 'crm.lead',
                'res_id': self.inquiry_id.lead_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def apply_pricing_rules(self):
        self.ensure_one()
        # 1. Reset to base package prices
        package = self.package_id
        adult_price = package.adult_price or package.base_price
        child_price = package.child_price or 0.0
        infant_price = package.infant_price or 0.0
        
        # Keep track of original values for chatter log comparison
        orig_adult = adult_price
        orig_child = child_price
        orig_infant = infant_price
        
        # Calculate initial subtotal
        if package.price_type == 'per_person':
            initial_subtotal = (self.num_adults * adult_price + 
                                self.num_children * child_price + 
                                self.num_infants * infant_price)
        else:
            initial_subtotal = adult_price
            
        applied_rules_log = []
        
        # Get active rules sorted by sequence
        rules = package.pricing_rule_ids.filtered(lambda r: r.active).sorted(key=lambda r: (r.sequence, r.id))
        
        today = fields.Date.context_today(self)
        booking_date = self.booking_date.date() if self.booking_date else today
        
        # 2. First pass: Apply seasonal price multipliers (modifies the unit prices)
        seasonal_rules = rules.filtered(lambda r: r.rule_type == 'seasonal')
        for rule in seasonal_rules:
            is_valid = True
            if rule.valid_from and today < rule.valid_from:
                is_valid = False
            if rule.valid_to and today > rule.valid_to:
                is_valid = False
                
            if is_valid:
                old_adult = adult_price
                adult_price = round(adult_price * rule.factor, 2)
                child_price = round(child_price * rule.factor, 2)
                infant_price = round(infant_price * rule.factor, 2)
                applied_rules_log.append({
                    'name': rule.name,
                    'type': 'Seasonal Multiplier',
                    'detail': _('Multiplier Factor: %s') % rule.factor,
                    'impact': _('Adult price: %s -> %s') % (old_adult, adult_price)
                })

        # Calculate base subtotal after seasonal adjustments
        if package.price_type == 'per_person':
            seasonal_subtotal = (self.num_adults * adult_price + 
                                 self.num_children * child_price + 
                                 self.num_infants * infant_price)
        else:
            seasonal_subtotal = adult_price
        # 3. Second pass: Collect all matching discount rules (group size & early bird)
        matched_discount_rules = []
        discount_rules = rules.filtered(lambda r: r.rule_type in ['group_size', 'early_bird'])
        for rule in discount_rules:
            apply_discount = False
            detail_str = ""

            if rule.rule_type == 'group_size':
                total_people = self.total_persons or (self.num_adults + self.num_children + self.num_infants)
                if rule.min_group <= total_people <= rule.max_group:
                    apply_discount = True
                    detail_str = _('Group size: %d (Range: %d-%d)') % (total_people, rule.min_group, rule.max_group)

            elif rule.rule_type == 'early_bird' and self.travel_start_date:
                days_diff = (self.travel_start_date - booking_date).days
                if days_diff >= rule.days_before:
                    apply_discount = True
                    detail_str = _('Booked %d days before travel (Min: %d days)') % (days_diff, rule.days_before)

            if apply_discount:
                if rule.discount_type == 'percentage':
                    rule_discount = round(seasonal_subtotal * (rule.discount_value / 100.0), 2)
                    effective_pct = rule.discount_value
                    impact_str = _('-%s%% (- %s)') % (rule.discount_value, rule_discount)
                else:
                    rule_discount = round(rule.discount_value, 2)
                    # Compute effective percentage for comparison
                    effective_pct = round((rule_discount / seasonal_subtotal) * 100.0, 4) if seasonal_subtotal else 0.0
                    impact_str = _('-%s (Fixed)') % rule_discount
                matched_discount_rules.append({
                    'name': rule.name,
                    'type': rule.rule_type == 'group_size' and 'Group Size Discount' or 'Early Bird Discount',
                    'detail': detail_str,
                    'impact': impact_str,
                    'discount_amount': rule_discount,
                    'effective_pct': effective_pct,
                    'selected': False,
                })
        # Pick the rule with the highest effective discount percentage
        discount_amount = 0.0
        if matched_discount_rules:
            best = max(matched_discount_rules, key=lambda r: r['effective_pct'])
            best['selected'] = True
            discount_amount = best['discount_amount']
            # Build log entries — all matched rules listed, winner flagged
            for entry in matched_discount_rules:
                suffix = _(' Applied (highest discount)') if entry['selected'] else _(' Skipped (lower discount)')
                applied_rules_log.append({
                    'name': entry['name'],
                    'type': entry['type'],
                    'detail': entry['detail'],
                    'impact': entry['impact'] + suffix,
                })
        # Calculate final pricing
        final_total = max(0.0, seasonal_subtotal - discount_amount)
        applied_rules_desc = ""
        if applied_rules_log:
            lines = []
            for log in applied_rules_log:
                lines.append(f"• {log['name']} ({log['type']}): {log['detail']} -> {log['impact']}")
            applied_rules_desc = "\n".join(lines)
        # Update booking fields
        discount_pct = round((discount_amount / seasonal_subtotal) * 100.0, 2) if seasonal_subtotal else 0.0
        self.write({
            'adult_price': adult_price,
            'child_price': child_price,
            'infant_price': infant_price,
            'discount_percentage': discount_pct,
            'discount_amount': 0.0,
            'applied_rules_desc': applied_rules_desc,
        })
        # 4. Chatter Log - Post detailed summary
        if applied_rules_log:
            # Build an elegant HTML table for Odoo chatter
            currency_symbol = self.currency_id.symbol or '$'
            rows = Markup('')
            for log in applied_rules_log:
                rows += Markup(
                    "<tr>"
                    "<td><b>{name}</b></td>"
                    "<td>{rtype}</td>"
                    "<td>{detail}</td>"
                    "<td><span class='badge bg-info text-white' style='padding:4px 8px;'>{impact}</span></td>"
                    "</tr>"
                ).format(
                    name=log['name'],
                    rtype=log['type'],
                    detail=log['detail'],
                    impact=log['impact'],
                )
            summary_rows = Markup(
                "<tr><td>Original Base Total:</td><td>{sym} {total}</td></tr>"
            ).format(sym=currency_symbol, total='{:,.2f}'.format(initial_subtotal))

            if seasonal_subtotal != initial_subtotal:
                summary_rows += Markup(
                    "<tr><td>After Seasonal Factor:</td><td>{sym} {stotal}</td></tr>"
                ).format(sym=currency_symbol, stotal='{:,.2f}'.format(seasonal_subtotal))
            summary_rows += Markup(
                "<tr><td>Total Discounts:</td><td>- {sym} {disc}</td></tr>"
                "<tr style='font-weight:bold; background-color:#e6f7ff;'><td>Final Price:</td><td>{sym} {final}</td></tr>"
            ).format(
                sym=currency_symbol,
                disc='{:,.2f}'.format(discount_amount),
                final='{:,.2f}'.format(final_total),
            )
            log_body = Markup(
                "<h3>Pricing Rules Applied</h3>"
                "<table class='table table-sm table-bordered' style='width:100%; border-collapse:collapse;'>"
                "<thead style='background-color:#f2f2f2;'>"
                "<tr><th>Rule Name</th><th>Type</th><th>Condition/Detail</th><th>Price Impact</th></tr>"
                "</thead><tbody>{rows}</tbody></table><br/>"
                "<b>Price Summary:</b><br/>"
                "<table class='table table-sm table-bordered' style='width:50%; border-collapse:collapse;'>"
                "{summary_rows}</table>"
            ).format(rows=rows, summary_rows=summary_rows)
            self.message_post(body=log_body)
        else:
            self.write({
                'discount_percentage': 0.0,
                'discount_amount': 0.0,
                'applied_rules_desc': False,
            })
            self.message_post(body=Markup(_("Pricing rules evaluated. No active rules met the conditions. Prices reset to base package pricing.")))

    def action_apply_pricing_rules(self):
        self.ensure_one()
        if self.state not in ['draft', 'confirmed']:
            raise UserError(_('You can only apply pricing rules on draft or confirmed bookings.'))
        self.apply_pricing_rules()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Apply Pricing Rules'),
                'message': _('Pricing rules evaluated and applied successfully.'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_generate_estimated_expenses(self):
        """Generate draft expenses based on standard cost of services configured on the booking"""
        self.ensure_one()
        expense_model = self.env['tour.expense']
        # Clean existing draft expenses to prevent duplicates
        existing_drafts = self.expense_ids.filtered(lambda e: e.state == 'draft')
        if existing_drafts:
            existing_drafts.unlink()
        # 1. Hotels Cost
        nights = max(1, self.package_id.duration_days - 1)
        for hotel in self.hotel_ids:
            amount = hotel.price_per_night * nights
            expense_model.create({
                'name': f"Estimated Hotel Cost: {hotel.name} ({nights} night(s))",
                'booking_id': self.id,
                'package_id': self.package_id.id,
                'expense_type': 'hotel',
                'amount': amount,
                'state': 'draft',
                'notes': f"Generated automatically based on standard hotel rate of {hotel.price_per_night}/night.",
            })
        # 2. Transportation Cost
        days = max(1, self.package_id.duration_days)
        for transport in self.transportation_ids:
            amount = transport.cost_per_unit or (transport.price_per_day * days)
            expense_model.create({
                'name': f"Estimated Transportation Cost: {transport.name}",
                'booking_id': self.id,
                'package_id': self.package_id.id,
                'expense_type': 'transportation',
                'amount': amount,
                'state': 'draft',
                'notes': f"Generated automatically based on standard transport pricing.",
            })
            
        # 3. Meals Cost
        persons = self.total_persons or 1
        for meal in self.meal_ids:
            amount = meal.cost_per_person * persons
            expense_model.create({
                'name': f"Estimated Meal Cost: {meal.name} for {persons} person(s)",
                'booking_id': self.id,
                'package_id': self.package_id.id,
                'expense_type': 'meal',
                'amount': amount,
                'state': 'draft',
                'notes': f"Generated automatically based on meal cost per person of {meal.cost_per_person}.",
            })
            
        # 4. Attraction Cost
        for attraction in self.attraction_ids:
            amount = attraction.entry_fee * persons
            expense_model.create({
                'name': f"Estimated Entry Cost: {attraction.name} for {persons} person(s)",
                'booking_id': self.id,
                'package_id': self.package_id.id,
                'expense_type': 'attraction',
                'amount': amount,
                'state': 'draft',
                'notes': f"Generated automatically based on entry fee of {attraction.entry_fee} per person.",
            })
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generate Estimated Expenses'),
                'message': _('Estimated expenses have been successfully generated as Draft.'),
                'sticky': False,
                'type': 'success',
            }
        }
