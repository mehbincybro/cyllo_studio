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


class TourPackage(models.Model):
    _name = 'tour.package'
    _description = 'Tour Package'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.seo.metadata', 'website.published.mixin', 'website.cover_properties.mixin']
    _order = 'sequence, name'
    
    # Basic Information
    name = fields.Char(string='Package Name', required=True, tracking=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True, tracking=True)
    code = fields.Char(string='Package Code', copy=False, readonly=True, index=True)
    # Description and Details
    description = fields.Html(string='Description', translate=True)
    short_description = fields.Text(string='Short Description', translate=True)
    # Images
    image_1920 = fields.Image(string='Main Image', max_width=1920, max_height=1920)
    image_1024 = fields.Image(related='image_1920', max_width=1024, max_height=1024, store=True)
    image_512 = fields.Image(related='image_1920', max_width=512, max_height=512, store=True)
    image_256 = fields.Image(related='image_1920', max_width=256, max_height=256, store=True)
    image_128 = fields.Image(related='image_1920', max_width=128, max_height=128, store=True)
    # Additional Images
    image_ids = fields.One2many('tour.package.image', 'package_id', string='Additional Images')
    # Tour Details
    destination = fields.Char(string='Destination', required=True, tracking=True)
    country_id = fields.Many2one('res.country', string='Country')
    duration_days = fields.Integer(string='Duration (Days)', required=True, default=1)
    duration_nights = fields.Integer(string='Duration (Nights)', compute='_compute_duration_nights', store=True)
    # Category and Tags
    category_id = fields.Many2one('tour.package.category', string='Category', tracking=True)
    tag_ids = fields.Many2many('tour.package.tag', string='Tags')
    # Pricing
    price_type = fields.Selection([
        ('per_person', 'Per Person'),
        ('per_package', 'Per Package'),
    ], string='Price Type', default='per_person', required=True)
    price = fields.Monetary(string='Price', currency_field='currency_id',
                            help='Standard package price')
    base_price = fields.Monetary(string='Base Price', currency_field='currency_id', required=True)
    adult_price = fields.Monetary(string='Adult Price', currency_field='currency_id')
    child_price = fields.Monetary(string='Child Price', currency_field='currency_id')
    infant_price = fields.Monetary(string='Infant Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                   default=lambda self: self.env.company.currency_id)
    pricing_rule_ids = fields.One2many('tour.package.pricing.rule', 'package_id', string='Pricing Rules')
    # Inclusions and Exclusions
    inclusion_ids = fields.One2many('tour.package.inclusion', 'package_id', string='Inclusions')
    exclusion_ids = fields.One2many('tour.package.exclusion', 'package_id', string='Exclusions')
    # Itinerary
    itinerary_ids = fields.One2many('tour.itinerary', 'package_id', string='Itinerary')
    itinerary_count = fields.Integer(compute='_compute_itinerary_count', string='Itinerary Days')
    # Hotels
    hotel_ids = fields.Many2many('tour.hotel', string='Hotels')
    # Transportation
    transportation_ids = fields.Many2many('tour.transportation', string='Transportation')
    # Meals
    meal_ids = fields.Many2many('tour.meal', string='Meals')
    # Attractions
    attraction_ids = fields.Many2many('tour.attraction', string='Attractions')
    # Availability
    start_date = fields.Date(string='Start Date', help='Tour start date')
    end_date = fields.Date(string='End Date', help='Tour end date')
    available_from = fields.Date(string='Available From')
    available_to = fields.Date(string='Available To')
    max_participants = fields.Integer(string='Maximum Participants', default=50)
    min_participants = fields.Integer(string='Minimum Participants', default=1)
    max_persons = fields.Integer(string='Maximum Persons', default=50)
    min_persons = fields.Integer(string='Minimum Persons', default=1)
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    # Statistics
    view_count = fields.Integer(string='Views', default=0, readonly=True)
    inquiry_count = fields.Integer(compute='_compute_inquiry_count', string='Inquiries')
    booking_count = fields.Integer(compute='_compute_booking_count', string='Bookings')
    # Relations
    inquiry_ids = fields.One2many('tour.inquiry', 'package_id', string='Inquiries')
    booking_ids = fields.One2many('tour.booking', 'package_id', string='Bookings')
    # Sales and Accounting
    product_id = fields.Many2one('product.product', string='Product', 
                                  help='Product for invoicing this package')
    # Responsible
    user_id = fields.Many2one('res.users', string='Responsible', 
                              default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    website_id = fields.Many2one('website', string='Website', 
                                  help='Website where this tour package will be published')
    # Terms and Conditions
    terms_conditions = fields.Html(string='Terms & Conditions', translate=True)
    cancellation_policy = fields.Html(string='Cancellation Policy', translate=True)
    # Featured
    is_featured = fields.Boolean(string='Featured Package', default=False)
    is_popular = fields.Boolean(string='Popular Package', default=False)
    
    @api.depends('duration_days')
    def _compute_duration_nights(self):
        for record in self:
            record.duration_nights = max(0, record.duration_days - 1)
    
    @api.depends('itinerary_ids')
    def _compute_itinerary_count(self):
        for record in self:
            record.itinerary_count = len(record.itinerary_ids)
    
    @api.depends('inquiry_ids')
    def _compute_inquiry_count(self):
        for record in self:
            record.inquiry_count = len(record.inquiry_ids)
    
    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = len(record.booking_ids.filtered(lambda b: b.state != 'cancel'))
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('tour.package') or _('New')
        return super().create(vals_list)
    
    @api.constrains('min_persons', 'max_persons')
    def _check_persons(self):
        for record in self:
            if record.min_persons < 0:
                raise ValidationError(_('Minimum persons cannot be negative.'))
            if record.max_persons < record.min_persons:
                raise ValidationError(_('Maximum persons must be greater than or equal to minimum persons.'))
    
    @api.constrains('available_from', 'available_to')
    def _check_dates(self):
        for record in self:
            if record.available_from and record.available_to:
                if record.available_to < record.available_from:
                    raise ValidationError(_('Available To date must be after Available From date.'))
    
    def action_publish(self):
        self.write({'state': 'published', 'is_published': True})
        return True
    
    def action_archive(self):
        self.write({'state': 'archived', 'is_published': False})
        return True
    
    def action_draft(self):
        self.write({'state': 'draft', 'is_published': False})
        return True
    
    def action_view_inquiries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inquiries'),
            'res_model': 'tour.inquiry',
            'view_mode': 'list,form',
            'domain': [('package_id', '=', self.id)],
            'context': {'default_package_id': self.id},
        }
    
    def action_view_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bookings'),
            'res_model': 'tour.booking',
            'view_mode': 'list,form',
            'domain': [('package_id', '=', self.id)],
            'context': {'default_package_id': self.id},
        }
    
    def increment_view_count(self):
        self.sudo().write({'view_count': self.view_count + 1})
    
    def _compute_website_url(self):
        for package in self:
            package.website_url = f'/tour/package/{package.id}'

    def action_apply_pricing_rules(self):
        self.ensure_one()
        # Find all draft bookings associated with this package
        bookings = self.env['tour.booking'].search([
            ('package_id', '=', self.id),
            ('state', '=', 'draft')
        ])
        if not bookings:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Apply Pricing Rules'),
                    'message': _('No draft bookings found for this package.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        applied_count = 0
        for booking in bookings:
            booking.apply_pricing_rules()
            applied_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Apply Pricing Rules'),
                'message': _('Pricing rules evaluated and applied to %d draft booking(s).') % applied_count,
                'sticky': False,
                'type': 'success',
            }
        }
