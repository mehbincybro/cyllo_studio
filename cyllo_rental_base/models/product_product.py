# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductProduct(models.Model):
    """ Adding rental details in product form """
    _inherit = 'product.product'

    is_rental = fields.Boolean(help='Check this box if this product can be rented')
    rental_charging_ids = fields.One2many(comodel_name='rental.charging', inverse_name='product_id',
                                          string='Rental Charges')
    extra_hourly_price = fields.Float(string='Per hour', default=0.00,
                                      help="Additional hourly price for renting this product")
    apply_after = fields.Float(string='Apply after (hours)', default=2,
                               help="Apply the extra hourly price after this duration")
    delay_product_id = fields.Many2one("product.product", string=" Delay product",
                                       help="The product used to add extra cost to the rental order",
                                       domain="[('type', '=', 'service')]")
    rental_location_id = fields.Many2one('stock.location', string=' Rental location',
                                         domain="[('is_rental_location', '=', True)]",
                                         help="The default rental location for this product")
    rental_checklist_ids = fields.One2many(comodel_name='rental.checklist', inverse_name='product_id',
                                           string=' Rental Checklist',
                                           help="Checklist for rental products and accessories")
    current_rented_quantity = fields.Integer(string="Currently Rented Quantity",
                                             help="The number of products currently in rented state",
                                             compute='_compute_current_rented_quantity')
    is_extra_cost = fields.Boolean(string="Extra Charges", help="Enable this to add extra charges")
    min_quantity = fields.Integer(string="Min Qty", help="Minimum quantity for renting")
    min_qty_amt = fields.Monetary(string="Per Product Price",
                                  help="Price for the individual item if it meets the required min qty")

    def _compute_rental_location_id(self):
        """ Default rental location """
        location = self.env['stock.location'].search([('name', '=', 'Rental'),
                                                      ('company_id', '=', self.env.company.id)])
        for product in self:
            product.rental_location_id = location or False

    def _compute_current_rented_quantity(self):
        """ Function to find currently rented quantity """
        for rec in self:
            orders = self.env['rental.order'].search([('state', '=', 'rented')]).mapped('id')
            rec.current_rented_quantity = sum(self.env['rental.order.line'].search(
                    [('product_id', '=', rec.id), ('order_id', 'in', orders)]).mapped('product_uom_qty'))


class RentalCharging(models.Model):
    """ Rental Charges """
    _name = 'rental.charging'
    _description = 'Rental Charges'

    rental_period = fields.Selection(selection=[('hours', 'Hours'), ('days', 'Days'), ('months', 'Months'),
                                                ('years', 'Years')], string='Period', required=True, default='hours',
                                     help="The charging period for the rental")
    product_id = fields.Many2one('product.product', help="The product associated with this rental charge")
    rental_price = fields.Monetary(string='Per hour', default=1.0, help="The rental price per hour")
    price = fields.Monetary(required=True, default=1.0, help="The total price for the rental charge")
    company_id = fields.Many2one('res.company', copy=False, default=lambda self: self.env.user.company_id.id,
                                 help="The company to which this rental charge belongs")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  help="The currency used for transactions related to this rental charge")

    def rental_charges(self, p_id):
        """ Rental pricing of products """
        price_rules = self.search([('product_id', '=', int(p_id))])
        prices = price_rules.mapped('price')
        periods = price_rules.mapped('rental_period')
        rental_price_rules = {}
        for lines in price_rules:
            rental_price_rules[lines.rental_period] = (lines.price, lines.rental_period)
        currency_symbol = self.env.ref('base.main_company').currency_id.symbol
        return {
            'prices': prices,
            'periods': periods,
            'currency_symbol': currency_symbol,
            'rental_price_rules': rental_price_rules
        }


class RentalChecklist(models.Model):
    """ Checklist for rental products and accessories """
    _name = 'rental.checklist'
    _description = 'Rental Checklist'

    name = fields.Char(help="The name of the checklist item")
    is_available = fields.Boolean(string='Available', help="Indicates whether the checklist item is available")
    remarks = fields.Text(help="Additional remarks or notes for the checklist item")
    product_id = fields.Many2one('product.product', help="The product associated with this checklist item")
