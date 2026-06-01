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
from odoo.exceptions import ValidationError


class TourInquiry(models.Model):
    _name = 'tour.inquiry'
    _description = 'Tour Package Inquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(string='Inquiry Reference', required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('New'))
    # Customer Information
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    customer_name = fields.Char(string='Name', required=True, tracking=True)
    customer_email = fields.Char(string='Email', required=True, tracking=True)
    customer_phone = fields.Char(string='Phone', tracking=True)
    customer_mobile = fields.Char(string='Mobile')
    customer_address = fields.Text(string='Address')
    # Package Details
    package_id = fields.Many2one('tour.package', string='Tour Package', required=True, 
                                  tracking=True, ondelete='restrict')
    package_name = fields.Char(related='package_id.name', string='Package', readonly=True)
    # Inquiry Details
    inquiry_date = fields.Datetime(string='Inquiry Date', default=fields.Datetime.now, 
                                    required=True, tracking=True)
    preferred_date = fields.Date(string='Preferred Travel Date', tracking=True)
    # Passenger Details
    num_adults = fields.Integer(string='Number of Adults', default=1)
    num_children = fields.Integer(string='Number of Children', default=0)
    num_infants = fields.Integer(string='Number of Infants', default=0)
    total_persons = fields.Integer(compute='_compute_total_persons', string='Total Persons', store=True)
    # Inquiry Content
    subject = fields.Char(string='Subject')
    message = fields.Text(string='Message/Requirements', required=True)
    special_requirements = fields.Text(string='Special Requirements')
    # Price Estimate
    estimated_price = fields.Monetary(
        string='Estimated Price',
        currency_field='currency_id',
        compute='_compute_estimated_price',
        store=True,
        readonly=False,
        help="Auto-calculated from the package pricing and number of passengers. Can be manually adjusted."
    )
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    # Status and Assignment
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('quoted', 'Quoted'),
        ('converted', 'Converted to Booking'),
        ('rejected', 'Rejected'),
    ], string='Status', default='new', required=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Assigned To', tracking=True,
                              default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', string='Sales Team', tracking=True)
    # CRM Integration
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity', tracking=True)
    # Booking Conversion
    booking_id = fields.Many2one('tour.booking', string='Converted Booking', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Quotation', readonly=True, copy=False)
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Quotation Count')

    def _compute_sale_order_count(self):
        for inquiry in self:
            inquiry.sale_order_count = 1 if inquiry.sale_order_id else 0
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    # Source
    source = fields.Selection([
        ('website', 'Website'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('walk_in', 'Walk-in'),
        ('referral', 'Referral'),
        ('other', 'Other'),
    ], string='Source')
    # Notes
    notes = fields.Text(string='Internal Notes')
    # Priority
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], string='Priority', default='1')
    
    @api.depends('num_adults', 'num_children', 'num_infants')
    def _compute_total_persons(self):
        for record in self:
            record.total_persons = record.num_adults + record.num_children + record.num_infants
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tour.inquiry') or _('New')
            # Create partner if doesn't exist
            if not vals.get('partner_id') and vals.get('customer_email'):
                partner = self.env['res.partner'].search([
                    ('email', '=', vals['customer_email'])
                ], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': vals.get('customer_name'),
                        'email': vals.get('customer_email'),
                        'phone': vals.get('customer_phone'),
                        'mobile': vals.get('customer_mobile'),
                    })
                vals['partner_id'] = partner.id
            # Explicitly calculate estimated price if creating from website
            if 'estimated_price' not in vals and vals.get('package_id'):
                package = self.env['tour.package'].browse(vals['package_id'])
                if package.exists():
                    adults = vals.get('num_adults', 1)
                    children = vals.get('num_children', 0)
                    infants = vals.get('num_infants', 0)
                    if package.price_type == 'per_person':
                        vals['estimated_price'] = (adults * (package.adult_price or package.base_price)) + \
                                                  (children * (package.child_price or 0)) + \
                                                  (infants * (package.infant_price or 0))
                    else:
                        vals['estimated_price'] = package.base_price
        inquiries = super().create(vals_list)
        # Send auto-reply email
        for inquiry in inquiries:
            inquiry._send_acknowledgment_email()
            # Create CRM lead if configured
            if inquiry.company_id.tour_auto_create_lead:
                inquiry._create_crm_lead()
        return inquiries
    
    def write(self, vals):
        # Track state changes
        if 'state' in vals:
            for inquiry in self:
                if vals['state'] == 'quoted' and inquiry.state != 'quoted':
                    inquiry._send_quotation_email()
        return super().write(vals)
    
    def _send_acknowledgment_email(self):
        """Send acknowledgment email to customer"""
        self.ensure_one()
        template = self.env.ref('cyllo_vacations.email_template_inquiry_acknowledgment', 
                                raise_if_not_found=False)
        if template:
            template.sudo().send_mail(self.id, force_send=True)
    
    def _send_quotation_email(self):
        """Send quotation email to customer"""
        self.ensure_one()
        template = self.env.ref('cyllo_vacations.email_template_inquiry_quotation',
                                raise_if_not_found=False)
        if template:
            template.sudo().send_mail(self.id, force_send=True)
    
    def _create_crm_lead(self):
        """Create CRM lead from inquiry"""
        self.ensure_one()
        if not self.lead_id:
            lead_vals = {
                'name': f"Tour Inquiry: {self.package_name}",
                'partner_id': self.partner_id.id,
                'email_from': self.customer_email,
                'phone': self.customer_phone or self.customer_mobile,
                'description': self.message,
                'user_id': self.user_id.id,
                'team_id': self.team_id.id if self.team_id else False,
                'type': 'opportunity',
                'expected_revenue': self.estimated_price,
            }
            lead = self.env['crm.lead'].sudo().create(lead_vals)
            self.lead_id = lead.id
            self.message_post(body=_('CRM Lead created: %s', lead.name))
    
    def action_in_progress(self):
        """Mark inquiry as in progress and update CRM lead"""
        self.write({'state': 'in_progress'})
        for inquiry in self:
            if inquiry.lead_id:
                inquiry.lead_id.message_post(body=_('Tour inquiry marked as In Progress'))
    
    def action_quote(self):
        """Generate quotation, send quote and update CRM lead"""
        for inquiry in self:
            if not inquiry.sale_order_id and inquiry.package_id:
                # Generate a draft sale order
                product = inquiry.package_id.product_id
                if not product:
                    product = self.env.ref('cyllo_vacations.product_tour_booking', raise_if_not_found=False)
                if product:
                    order_lines = []
                    description_lines = [
                        f"Tour Package: {inquiry.package_name}",
                        f"Destination: {inquiry.package_id.destination}",
                        f"Duration: {inquiry.package_id.duration_days} Days / {inquiry.package_id.duration_nights} Nights",
                    ]
                    if inquiry.preferred_date:
                        description_lines.append(f"Travel Date: {inquiry.preferred_date}")
                    base_description = '\n'.join(description_lines)
                    if inquiry.package_id.price_type == 'per_person':
                        if inquiry.num_adults:
                            order_lines.append((0, 0, {
                                'product_id': product.id,
                                'name': f"{inquiry.package_name} - Adult x{inquiry.num_adults}\n{base_description}",
                                'product_uom_qty': inquiry.num_adults,
                                'price_unit': inquiry.package_id.adult_price or inquiry.package_id.base_price,
                            }))
                        if inquiry.num_children and inquiry.package_id.child_price:
                            order_lines.append((0, 0, {
                                'product_id': product.id,
                                'name': f"{inquiry.package_name} - Child x{inquiry.num_children}",
                                'product_uom_qty': inquiry.num_children,
                                'price_unit': inquiry.package_id.child_price,
                            }))
                        if inquiry.num_infants and inquiry.package_id.infant_price:
                            order_lines.append((0, 0, {
                                'product_id': product.id,
                                'name': f"{inquiry.package_name} - Infant x{inquiry.num_infants}",
                                'product_uom_qty': inquiry.num_infants,
                                'price_unit': inquiry.package_id.infant_price,
                            }))
                    else:
                        order_lines.append((0, 0, {
                            'product_id': product.id,
                            'name': f"{inquiry.package_name}\n{base_description}",
                            'product_uom_qty': 1,
                            'price_unit': inquiry.package_id.base_price,
                        }))
                    order_vals = {
                        'partner_id': inquiry.partner_id.id,
                        'partner_invoice_id': inquiry.partner_id.id,
                        'partner_shipping_id': inquiry.partner_id.id,
                        'date_order': fields.Datetime.now(),
                        'validity_date': inquiry.preferred_date,
                        'user_id': inquiry.user_id.id,
                        'team_id': inquiry.team_id.id if inquiry.team_id else False,
                        'order_line': order_lines,
                        'client_order_ref': inquiry.name,
                        'note': f"Quotation for Tour Inquiry: {inquiry.name}",
                        'currency_id': inquiry.currency_id.id,
                    }
                    sale_order = self.env['sale.order'].sudo().create(order_vals)
                    inquiry.sale_order_id = sale_order.id
                    inquiry.message_post(body=_('Quotation created: %s', sale_order.name))
            # Update CRM lead expected revenue
            if inquiry.lead_id:
                inquiry.lead_id.write({
                    'expected_revenue': inquiry.estimated_price,
                })
                inquiry.lead_id.message_post(body=_('Quote sent to customer. Estimated price: %s', inquiry.estimated_price))
        self.write({'state': 'quoted'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Quotation Sent'),
                'message': _('The quotation email has been sent to the customer.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_reject(self):
        """Reject inquiry and update CRM lead"""
        self.write({'state': 'rejected'})
        for inquiry in self:
            if inquiry.lead_id:
                # Mark lead as lost
                inquiry.lead_id.action_set_lost()
                inquiry.lead_id.message_post(body=_('Tour inquiry was rejected'))
    
    def action_convert_to_booking(self):
        """Convert inquiry to booking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Booking'),
            'res_model': 'tour.booking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_inquiry_id': self.id,
                'default_package_id': self.package_id.id,
                'default_partner_id': self.partner_id.id,
                'default_num_adults': self.num_adults,
                'default_num_children': self.num_children,
                'default_num_infants': self.num_infants,
                'default_preferred_date': self.preferred_date,
            },
        }
    
    def action_create_booking_direct(self):
        """Directly create booking from inquiry without wizard"""
        self.ensure_one()
        if self.booking_id:
            raise ValidationError(_('A booking already exists for this inquiry.'))
        booking_vals = {
            'package_id': self.package_id.id,
            'partner_id': self.partner_id.id,
            'num_adults': self.num_adults,
            'num_children': self.num_children,
            'num_infants': self.num_infants,
            'travel_start_date': self.preferred_date or fields.Date.today(),
            'special_requirements': self.special_requirements,
            'customer_notes': self.message,
            'source': self.source,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id if self.team_id else False,
            'inquiry_id': self.id,
            'sale_order_id': self.sale_order_id.id if self.sale_order_id else False,
        }
        booking = self.env['tour.booking'].create(booking_vals)
        self.write({
            'state': 'converted',
            'booking_id': booking.id,
        })
        # Update CRM lead
        if self.lead_id:
            self.lead_id.message_post(body=_('Converted to Booking: %s', booking.name))
        self.message_post(body=_('Booking created: %s', booking.name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Booking'),
            'res_model': 'tour.booking',
            'res_id': booking.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_lead(self):
        self.ensure_one()
        if not self.lead_id:
            raise ValidationError(_('No CRM lead linked to this inquiry.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('CRM Lead'),
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_sale_order(self):
        """View related quotation"""
        self.ensure_one()
        if not self.sale_order_id:
            raise ValidationError(_('No quotation linked to this inquiry.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quotation'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_booking(self):
        """View related booking"""
        self.ensure_one()
        if not self.booking_id:
            raise ValidationError(_('No booking linked to this inquiry.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Booking'),
            'res_model': 'tour.booking',
            'res_id': self.booking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.customer_name = self.partner_id.name
            self.customer_email = self.partner_id.email
            self.customer_phone = self.partner_id.phone
            self.customer_mobile = self.partner_id.mobile
    
    @api.depends('package_id', 'num_adults', 'num_children', 'num_infants')
    def _compute_estimated_price(self):
        for record in self:
            if not record.package_id:
                record.estimated_price = 0
                continue
            total = 0
            if record.package_id.price_type == 'per_person':
                total += record.num_adults * (record.package_id.adult_price or record.package_id.base_price)
                total += record.num_children * (record.package_id.child_price or 0)
                total += record.num_infants * (record.package_id.infant_price or 0)
            else:
                total = record.package_id.base_price
            record.estimated_price = total

