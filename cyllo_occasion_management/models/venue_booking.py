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
from markupsafe import Markup

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class VenueBooking(models.Model):
    """Model for managing the Venue Booking"""
    _name = 'venue.booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Venue Reservation'

    name = fields.Char(string="Name", help="Name of the venue type")
    ref = fields.Char(string='Ref', readonly=True,
                      help="Name of the venue that created as sequencing")
    venue_id = fields.Many2one('venue', string='Venue',
                               help="Venue for the Event", required=True)
    venue_type_id = fields.Many2one('venue.type',
                                    string='Venue Type',
                                    related='venue_id.venue_type_id',
                                    readonly=True,
                                    help='Used to choose the type of the '
                                         'particular venue')
    image = fields.Binary(string="Image", attachment=True,
                          related='venue_type_id.image',
                          help="This field holds the image used as "
                               "image for the event, limited to 1080x720px.")
    partner_id = fields.Many2one('res.partner', string="Customer",
                                 required=True,
                                 help='Used to Choose the Booking Person')
    date = fields.Date(string="Date", default=fields.Date.today, required=True,
                       help='Date field for booking the Venue')
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  string='Currency',
                                  default=lambda self:
                                  self.env.user.company_id.currency_id,
                                  help='Currency field for booking Venue')
    start_date = fields.Datetime(string="Start Date",
                                 default=lambda self: fields.datetime.now(),
                                 required=True,
                                 help='Venue Booking Start Date')
    end_date = fields.Datetime(string="End Date", required=True,
                               help='Venue Booking End Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirmed'),
                              ('invoice', 'Invoiced'),
                              ('close', 'Close'), ('cancel', 'Canceled')],
                             string="State", default="draft",
                             help="State of venue booking")
    booking_type = fields.Selection([('day', 'Day'),
                                     ('hour', 'Hours')], string='Booking Type',
                                    default='day',
                                    help='The selection field for Booking Type')
    venue_booking_line_ids = fields.One2many('venue.booking.line',
                                             'venue_booking_id',
                                             string="Venues",
                                             domain=[('is_included', '=', False)],
                                             help='Booking Line for the '
                                                  'given venue')
    note = fields.Text(string='Terms and Conditions',
                       help='The note field for Venue Booking')
    pending_invoice = fields.Boolean(string="Invoice Pending",
                                     compute='_compute_pending_invoice',
                                     help='Find out is there any pending '
                                          'invoice')
    total = fields.Monetary(string="Total Amount", store=True,
                            compute='_compute_total_amount',
                            help='Total amount for the Venue Booking')
    booking_charge_per_day = fields.Float(string="Booking Charge Per Day",
                                          related='venue_id.venue_charge_day',
                                          help='Field for adding Booking '
                                               'Charge Per Day')
    booking_charge_per_hour = fields.Float(string="Booking Charge Per Hour",
                                           related='venue_id.venue_charge_hour',
                                           help='Field for adding Booking '
                                                'Charge Per hour')
    booking_charge = fields.Float(string="Venue Amenities Charge",
                                  compute='_compute_booking_charge',
                                  help='Compute the total Booking cost '
                                       'includes the amenities')
    days_difference = fields.Integer(string='Days Difference',
                                     compute='_compute_days_difference',
                                     help='Number of Days to Booking the venue')
    invoice_count = fields.Integer(string="Invoice Count",
                                   compute='_compute_invoice_count',
                                   help='Total invoice count')
    is_additional_charge = fields.Boolean(string="Add Extra Charge?",
                                          help='Add additional charge '
                                               'for the booking')
    is_extra_check = fields.Boolean(string="Checks Additional Charges",
                                    help='Checks additional charge '
                                         'is enabled on settings',
                                    default=lambda self: self.env[
                                        'ir.config_parameter'].sudo().get_param(
                                        'cyllo_occasion_management.is_extra'))
    amenity_line_ids = fields.One2many('venue.booking.line',
                                       'venue_booking_id',
                                       string="Included Amenities",
                                       domain=[('is_included', '=', True)],
                                       help='Booking Line for the given venue')
    event_id = fields.Many2one('event.event', string="Event", readonly=True,
                               help="Event associated with this venue booking")
    need_catering = fields.Boolean(string="Need Catering", help="Check if catering is needed for this venue booking")
    guest_count = fields.Integer(string="Number of Guests", default=1)
    catering_ids = fields.Many2many('catering.booking', 'venue_catering_rel', 'venue_booking_id', 'catering_id', string="Catering Orders",
                                  domain="[('state', '=', 'confirm'), ('event_id', '=', False), ('venue_booking_id', '=', False)]")
    catering_count = fields.Integer(string="Catering Count", compute='_compute_catering_count')

    @api.depends('catering_ids')
    def _compute_catering_count(self):
        """Compute total catering bookings linked to the venue booking."""
        for record in self:
            created_bookings = self.env['catering.booking'].search_count([('venue_booking_id', '=', record.id)])
            record.catering_count = len(record.catering_ids) + created_bookings

    @api.onchange('catering_ids')
    def _onchange_catering_ids(self):
        """Link selected catering orders to this venue booking"""
        for catering in self.catering_ids:
            if not catering.venue_booking_id:
                catering.venue_booking_id = self.id

    def action_create_catering_booking(self):
        """Open form to create a catering booking linked to the venue booking."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Catering Booking'),
            'res_model': 'catering.booking',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
                'default_venue_booking_id': self.id,
                'default_guest_count': self.guest_count,
            },
            'target': 'new',
        }

    def action_view_catering_booking(self):
        """View all catering bookings linked to the current venue booking."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("cyllo_occasion_management.catering_booking_action")
        linked_ids = self.catering_ids.ids
        created_ids = self.env['catering.booking'].search([('venue_booking_id', '=', self.id)]).ids
        action['domain'] = [('id', 'in', list(set(linked_ids + created_ids)))]
        return action

    @api.constrains('venue_booking_line_ids','amenity_line_ids')
    def _check_venue_booking_line_ids(self):
        """Check if the venue bookings line contains already taken amenities"""
        for rec in self:
            included_amenities = rec.amenity_line_ids.mapped('amenity_id')
            duplicate_names = []
            for line in rec.venue_booking_line_ids:
                if line.amenity_id in included_amenities:
                    duplicate_names.append(line.amenity_id.name)
            if duplicate_names:
                raise ValidationError(_(
                    "These amenities are already included: %s"
                ) % (', '.join(set(duplicate_names))))

    @api.model
    def create(self, values):
        """Create method for sequencing and checking dates while Booking the
        Venues"""
        partner_name = self.env['res.partner'].browse(
            values['partner_id']).name
        if values['start_date'] >= values['end_date']:
            raise UserError(_('Start date must be less than End date'))
        values['name'] = '%s- %s' % (partner_name, values['date'])
        values['ref'] = self.env['ir.sequence'].next_by_code(
            'venue.booking.sequence')
        if 'amenity_line_ids' in values:
            for line in values['amenity_line_ids']:
                if line[0] == 0:
                    line[2]['is_included'] = True
        if 'venue_booking_line_ids' in values:
            for line in values['venue_booking_line_ids']:
                if line[0] == 0:
                    line[2]['is_included'] = False
        res = super().create(values)
        return res

    @api.model
    def write(self, values):
        """Override write to set is_included=True for included amenities and False for additional amenities."""
        if 'amenity_line_ids' in values:
            for line in values['amenity_line_ids']:
                if line[0] == 0:
                    line[2]['is_included'] = True
        if 'venue_booking_line_ids' in values:
            for line in values['venue_booking_line_ids']:
                if line[0] == 0:
                    line[2]['is_included'] = False
        return super().write(values)

    @api.onchange('start_date', 'end_date')
    def _onchange_booking_dates(self):
        """Checking dates while Booking the Venues based on the changes
        of the Dates"""
        if self.venue_id:
            booking = self.env['venue.booking'].search(
                [('start_date', '<', self.end_date),
                 ('end_date', '>', self.start_date),
                 ('venue_id', '=', self.venue_id.id),
                 ('state', 'in', ['confirm', 'invoice'])
                 ])
            if booking:
                raise ValidationError(
                    "Venue is not available for the selected time range.")

    @api.onchange('venue_id')
    def _onchange_venue_id(self):
        """Load included amenities safely without affecting extra amenities"""
        if self.venue_id:
            self.amenity_line_ids = [
                Command.create({
                    'amenity_id': line.amenities_id.id,
                    'quantity': line.quantity,
                    'is_included': True,
                })
                for line in self.venue_id.venue_line_ids
            ]

    @api.depends('start_date', 'end_date')
    def _compute_days_difference(self):
        """Compute the difference between start and end dates for
        Calculating the days"""
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.days_difference = delta.days + 1
            else:
                record.days_difference = 0

    @api.depends('booking_charge', 'venue_id')
    def _compute_booking_charge(self):
        """Calculate the total charge for all amenities in the booking"""
        """Compute booking charge for the given venue with the Amenities"""
        for rec in self:
            rec.booking_charge = rec.venue_id.price_subtotal if rec.venue_id else 0.0

    @api.depends('venue_booking_line_ids', 'venue_booking_line_ids.state')
    def _compute_pending_invoice(self):
        """Compute function for finding the pending Invoices"""
        for pending in self:
            pending.pending_invoice = any(
                not line.is_invoiced and line.state == "done" for line in
                pending.venue_booking_line_ids)

    @api.depends('venue_booking_line_ids.sub_total', 'booking_charge_per_hour',
                 'booking_charge_per_day')
    def _compute_total_amount(self):
        """Calculate the grand total including venue charges and amenities"""
        """Compute total amount of bookings with the Charge of the Particular
        venue"""
        total = sum(item.sub_total for item in self.venue_booking_line_ids)
        for rec in self:
            if rec.booking_type == 'day':
                total += (rec.booking_charge_per_day * rec.days_difference)
                if rec.venue_id.additional_charge_day != 0.0:
                    total += rec.venue_id.additional_charge_day
            elif rec.booking_type == 'hour':
                total += (rec.booking_charge_per_hour * rec.days_difference)
                if rec.venue_id.additional_charge_hour != 0.0:
                    total += rec.venue_id.additional_charge_hour
            rec.total = total + rec.booking_charge

    @api.constrains('start_date', 'end_date', 'venue_id')
    def check_date_overlap(self):
        """Check the date overlap between the start and end dates"""
        for booking in self:
            overlapping_bookings = self.env['venue.booking'].search([
                ('venue_id', '=', booking.venue_id.id),
                ('start_date', '<', booking.end_date),
                ('end_date', '>', booking.start_date),
                ('state', 'in', ['confirm', 'invoice']),
                ('id', '!=', booking.id),  # Exclude the current record itself
            ])
            if overlapping_bookings:
                raise ValidationError(
                    "Booking dates overlap with existing bookings.")

    def action_booking_confirm(self):
        """Button action to confirm"""
        for booking in self:
            bookings = self.env['venue.booking'].search([
                ('venue_id', '=', booking.venue_id.id),
                ('start_date', '<', booking.end_date),
                ('end_date', '>', booking.start_date),
                ('state', 'in', ['confirm', 'invoice']),
                ('id', '!=', booking.id),  # Exclude the current record itself
            ])
            if bookings:
                raise ValidationError(
                    "Booking dates overlap with existing bookings.")
            draft_bookings = self.env['venue.booking'].search([
                ('venue_id', '=', booking.venue_id.id),
                ('start_date', '<', booking.end_date),
                ('end_date', '>', booking.start_date),
                ('state', '=', 'draft'),
                ('id', '!=', booking.id),  # Exclude the current record itself
            ])
            if draft_bookings:
                for draft in draft_bookings:
                    draft.action_booking_cancel()
            self.state = "confirm"
            if not self.event_id:
                self._create_event()

    def _create_event(self):
        """Create an event record based on the venue booking"""
        for record in self:
            event_vals = {
                'name': record.name or f"Event for {record.venue_id.name}",
                'date_begin': record.start_date,
                'date_end': record.end_date,
                'organizer_id': record.partner_id.id,
                'venue_id': record.venue_id.id,
                'need_venue': True,
                'venue_booking_id': record.id,
                'stage_id': self.env.ref('event.event_stage_new').id if self.env.ref('event.event_stage_new', raise_if_not_found=False) else False,
            }
            event = self.env['event.event'].create(event_vals)
            record.event_id = event.id

    def action_confirm_reservation(self):
        """Confirm the reservation and lock the dates"""
        """Action for smart button to view linked event"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Event'),
            'res_model': 'event.event',
            'view_mode': 'form',
            'res_id': self.event_id.id,
            'target': 'current',
        }

    def action_reset_to_draft(self):
        """Button action to reset"""
        self.state = "draft"

    def action_send_confirmation_mail(self):
        """Button action to send confirmation mail"""
        template = self.env.ref(
            'cyllo_occasion_management.mail_template_notify_venue_booking').sudo()
        template.send_mail(self._origin.id, force_send=True,
                           email_values={
                               'email_to': self.partner_id.email})
        for rec in self:
            body = Markup(
                "<p>%(greeting)s<br/><br/>%(content)s<br/><br/>%(conclude)s<p>") % {
                       'greeting': _("Dear %s", rec.partner_id.name),
                       'content': _(
                           "We have received a booking for the venue %s.Please proceed with necessary actions.",
                           rec.venue_id.name),
                       'conclude': _('Thank You'),
                   }
            rec.message_post(body=body)

    def action_booking_invoice_create(self):
        """Generate a draft customer invoice for this booking"""
        """Button action to create related invoice"""
        invoice_id = self.env['account.move'].search(
            [('invoice_origin', '=', self.ref), ('state', '=', 'draft')])
        amenity_lists = []

        def add_charge(name, price_unit, quantity=1):
            amenity_lists.append({
                'name': name,
                'price_unit': price_unit,
                'quantity': quantity,
            })

        if self.booking_type == 'day':
            total = self.booking_charge_per_day + self.venue_id.additional_charge_day
        elif self.booking_type == 'hour':
            total = self.booking_charge_per_hour + self.venue_id.additional_charge_hour
        else:
            total = 0
        add_charge('Amenities charge', self.booking_charge)
        add_charge('Booking Charges', total)
        for rec in self.venue_booking_line_ids:
            add_charge(rec.amenity_id.name, rec.amount, rec.quantity)

        # Add Catering charges
        linked_ids = self.catering_ids.ids
        created_ids = self.env['catering.booking'].search([('venue_booking_id', '=', self.id)]).ids
        all_catering = self.env['catering.booking'].browse(list(set(linked_ids + created_ids)))
        for catering in all_catering:
            add_charge(_('Catering charge with %s') % catering.platter_type_id.name, catering.total_amount)
        if self.is_additional_charge:
            is_extra = self.env['ir.config_parameter'].sudo(). \
                get_param('cyllo_occasion_management.is_extra')
            if is_extra:
                amount = self.env['ir.config_parameter'].sudo(). \
                    get_param('cyllo_occasion_management.extra_amount')
                amenity_lists.append({
                    'name': 'Extra charges',
                    'price_unit': amount,
                    'quantity': '1',
                })
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.ref,
            'invoice_line_ids': [(0, 0, line) for line in amenity_lists],
        }
        if not invoice_id:
            invoice = self.env['account.move'].create([invoice_vals])
            self.state = "invoice"
            return {
                'name': 'Invoice',
                'view_mode': 'form',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
            }
        else:
            # Unlink existing lines
            invoice_id.invoice_line_ids.unlink()
            invoice_id.write(
                {'invoice_line_ids': [(0, 0, line) for line in amenity_lists]})
            self.state = "invoice"
            return {
                'name': 'Invoice',
                'view_mode': 'form',
                'res_id': invoice_id.id,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
            }

    def action_view_invoice(self):
        """Smart button to view the Corresponding Invoices for the
        Venue Booking"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'target': 'current',
            'domain': [('invoice_origin', '=', self.ref)],
            'context': {"create": False},
        }

    def _compute_invoice_count(self):
        """Function to count invoice"""
        for record in self:
            record.invoice_count = self.env['account.move']. \
                search_count([('invoice_origin', '=', self.ref)])

    def action_booking_cancel(self):
        """Button action to move the cancel state and send email"""
        template = self.env.ref(
            'cyllo_occasion_management.mail_template_cancel_venue_booking').sudo()
        template.send_mail(self._origin.id, force_send=True,
                           email_values={
                               'email_to': self.partner_id.email})
        for rec in self:
            body = Markup(
                "<p>%(greeting)s<br/><br/>%(content)s<br/><br/>%(conclude)s<p>") % {
                       'greeting': _("Dear %s", rec.partner_id.name),
                       'content': _(
                           "Your booking for the venue %s has been cancelled. Please log in to "
                           "your portal for further details.",
                           rec.venue_id.name),
                       'conclude': _('Thank You'),
                   }
            rec.message_post(body=body)
        self.state = "cancel"

    def action_booking_close(self):
        """Button action to close the records"""
        if any(not line.is_invoiced for line in self.venue_booking_line_ids):
            raise ValidationError(_('You can close The Booking only when all '
                                    'Procedure is Done and Invoiced'))
        else:
            self.state = "close"

    @api.model
    def get_total_booking(self):
        """Function to get total booking, distance and invoice amount details"""
        total_booking = self.env['venue.booking'].search_count([])
        booking_ids = self.env['venue.booking'].search(
            [('state', 'not in', ['draft', 'cancel', 'close'])])
        invoice_ids = self.env['venue.booking']. \
            search([('state', '=', 'invoice')]).mapped('total')
        venue_ids = self.env['venue'].search_count([])
        return {'total_booking': total_booking,
                'total_invoice': sum(invoice_ids),
                'total_amount': sum(booking_ids.mapped('total')),
                'total_venue': venue_ids}

    @api.model
    def get_top_venue(self):
        """Function to return top venue and customer details query to js"""
        self.env.cr.execute('''select fv.name,count(tb.name) from venue_booking as tb
                            inner join venue as fv on fv.id = tb.venue_id
                            group by fv.name order by count(tb.name) desc limit 10''')
        venue = self.env.cr.dictfetchall()
        self.env.cr.execute('''select pr.name,count(tb.name) from venue_booking as tb
                                   inner join res_partner as pr on pr.id = tb.partner_id
                                   group by pr.name order by count(tb.name) desc limit 10''')
        customer = self.env.cr.dictfetchall()
        self.env.cr.execute('''select tb.ref, pr.name, tb.date from 
                                    venue_booking as tb
                                    inner join res_partner as pr on pr.id = tb.partner_id
                                    where tb.date >= '%s' and tb.state = 'invoice'
                                    order by tb.date''' % fields.date.today())
        upcoming = self.env.cr.dictfetchall()
        return {'venue': venue, 'customer': customer, 'upcoming': upcoming}

    @api.model
    def get_booking_analysis(self):
        """Function to return customer details to js for graph view"""
        self.env.cr.execute('''select pr.name,sum(tb.total) from venue_booking as tb
                                    inner join res_partner as pr on pr.id = tb.partner_id
                                    group by pr.name order by sum(tb.total)''')
        booking = self.env.cr.dictfetchall()
        count = []
        customer = []
        for record in booking:
            customer.append(record.get('name'))
            count.append(record.get('sum'))
        value = {'name': customer, 'count': count}
        return value

    @api.model
    def get_venue_analysis(self):
        """Function to return truck details to js for graph view"""
        self.env.cr.execute('''select fv.name,sum(tb.total) from venue_booking as tb
                            inner join venue as fv on fv.id = tb.venue_id
                            group by fv.name order by sum(tb.total)''')
        booking = self.env.cr.dictfetchall()
        count = []
        customer = []
        for record in booking:
            customer.append(record.get('name'))
            count.append(record.get('sum'))
        return {'name': customer, 'count': count}

    @api.model
    def get_select_filter(self, option):
        """Function to filter data on the bases of the year"""
        if option == 'year':
            create_date = '''create_date between (now() - interval '1 year') and now()'''
        elif option == 'month':
            create_date = '''create_date between (now() - interval '1 months') and now()'''
        elif option == 'week':
            create_date = '''create_date between (now() - interval '7 day') and now()'''
        elif option == 'day':
            create_date = '''create_date between (now() - interval '1 day') and now()'''
        self.env.cr.execute('''select count(*) from venue_booking 
                                    where %s''' % create_date)
        booking = self.env.cr.dictfetchall()
        self.env.cr.execute('''select sum(total) from venue_booking 
                                    where %s''' % create_date)
        amount = self.env.cr.dictfetchall()
        self.env.cr.execute('''select sum(total) from venue_booking
                                        where state = 'invoice' and %s''' % create_date)
        invoice = self.env.cr.dictfetchall()
        self.env.cr.execute('''select count(*) from venue 
                                    where %s''' % create_date)
        venue_count = self.env.cr.dictfetchall()
        self.env.cr.execute('''SELECT fv.name, COUNT(tb.name) AS name_count
                FROM venue_booking AS tb
                INNER JOIN venue AS fv ON fv.id = tb.venue_id
                where tb.%s
                GROUP BY fv.name
                ORDER BY name_count DESC
                LIMIT 10''' % create_date)
        venue = self.env.cr.dictfetchall()
        self.env.cr.execute('''SELECT pr.name, COUNT(tb.name) AS name_count
                FROM venue_booking AS tb
                INNER JOIN res_partner AS pr ON pr.id = tb.partner_id
                where tb.%s
                GROUP BY pr.name
                ORDER BY name_count DESC
                LIMIT 10''' % create_date)
        customer = self.env.cr.dictfetchall()
        self.env.cr.execute('''SELECT pr.name, COUNT(pr.name) AS count, SUM(tb.total) AS total_sum
                FROM venue_booking AS tb
                INNER JOIN res_partner AS pr ON pr.id = tb.partner_id
                WHERE tb.%s
                GROUP BY pr.name
                ''' % create_date)
        cust_invoice = self.env.cr.dictfetchall()
        cust_invoice_name = []
        cust_invoice_sum = []
        cust_invoice_count = []
        for record in cust_invoice:
            cust_invoice_name.append(record.get('name'))
            cust_invoice_count.append(record.get('count'))
            cust_invoice_sum.append(record.get('sum'))
        self.env.cr.execute('''SELECT fv.name, SUM(tb.total) AS total_sum
                FROM venue_booking AS tb
                INNER JOIN venue AS fv ON fv.id = tb.venue_id
                where tb.%s
                GROUP BY fv.name;
                ''' % create_date)
        truck_invoice = self.env.cr.dictfetchall()
        truck_invoice_name = []
        truck_invoice_sum = []
        for record in truck_invoice:
            truck_invoice_name.append(record.get('name'))
            truck_invoice_sum.append(record.get('total_sum'))
        return {'booking': booking, 'amount': amount,
                'invoice': invoice, 'venue': venue, 'venue_count': venue_count,
                'customer': customer,
                'cust_invoice_name': cust_invoice_name,
                'cust_invoice_count': cust_invoice_count, 'cust_invoice_sum':
                    cust_invoice_sum, 'truck_invoice_name': truck_invoice_name,
                'truck_invoice_sum': truck_invoice_sum,
                }
