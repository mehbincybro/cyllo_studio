from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SunscriptionPricing(models.Model):
    _name = 'subscription.pricing'
    _description = 'Subscription Pricing'


    def _default_pricelist_id(self):
        return self.env['product.pricelist'].search([
            '|', ('company_id', '=', False),
            ('company_id', '=', self.env.company.id)], limit=1)

    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        index=True, ondelete='cascade',
        required=True,
        default=_default_pricelist_id)

    company_id = fields.Many2one(related='pricelist_id.company_id', store=True)
    currency_id = fields.Many2one(related='pricelist_id.currency_id', store=True)

    date_start = fields.Datetime(
        string="Start Date",
        help="Starting datetime for the pricelist item validation\n"
             "The displayed value depends on the timezone set in your preferences.")
    date_end = fields.Datetime(
        string="End Date",
        help="Ending datetime for the pricelist item validation\n"
             "The displayed value depends on the timezone set in your preferences.")

    min_quantity = fields.Float(
        string="Min. Quantity",
        default=0,
        digits='Product Unit of Measure',
        help="For the rule to apply, bought/sold quantity must be greater "
             "than or equal to the minimum quantity specified in this field.\n"
             "Expressed in the default unit of measure of the product.")

    # applied_on = fields.Selection(
    #     selection=[
    #         ('3_global', "All Products"),
    #         ('2_product_category', "Product Category"),
    #         ('1_product', "Product"),
    #         ('0_product_variant', "Product Variant"),
    #     ],
    #     string="Apply On",
    #     default='3_global',
    #     required=True,
    #     help="Pricelist Item applicable on selected option")

    # categ_id = fields.Many2one(
    #     comodel_name='product.category',
    #     string="Product Category",
    #     ondelete='cascade',
    #     help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Product",
        ondelete='cascade', check_company=True,
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product Variant",
        ondelete='cascade', check_company=True,
        help="Specify a product if this rule only applies to one product. Keep empty otherwise.")

    # base = fields.Selection(
    #     selection=[
    #         ('list_price', 'Sales Price'),
    #         ('standard_price', 'Cost'),
    #         ('pricelist', 'Other Pricelist'),
    #     ],
    #     string="Based on",
    #     default='list_price',
    #     required=True,
    #     help="Base price for computation.\n"
    #          "Sales Price: The base price will be the Sales Price.\n"
    #          "Cost Price: The base price will be the cost price.\n"
    #          "Other Pricelist: Computation of the base price based on another Pricelist.")
    # base_pricelist_id = fields.Many2one('product.pricelist', 'Other Pricelist', check_company=True)

    # compute_price = fields.Selection(
    #     selection=[
    #         ('fixed', "Fixed Price"),
    #         ('percentage', "Discount"),
    #         ('formula', "Formula"),
    #     ],
    #     index=True, default='fixed', required=True)

    fixed_price = fields.Float(string="Fixed Price", digits='Product Price')
    # percent_price = fields.Float(
    #     string="Percentage Price",
    #     help="You can apply a mark-up by setting a negative discount.")
    #
    # price_discount = fields.Float(
    #     string="Price Discount",
    #     default=0,
    #     digits=(16, 2),
    #     help="You can apply a mark-up by setting a negative discount.")
    # price_round = fields.Float(
    #     string="Price Rounding",
    #     digits='Product Price',
    #     help="Sets the price so that it is a multiple of this value.\n"
    #          "Rounding is applied after the discount and before the surcharge.\n"
    #          "To have prices that end in 9.99, set rounding 10, surcharge -0.01")
    # price_surcharge = fields.Float(
    #     string="Price Surcharge",
    #     digits='Product Price',
    #     help="Specify the fixed amount to add or subtract (if negative) to the amount calculated with the discount.")
    #
    # price_min_margin = fields.Float(
    #     string="Min. Price Margin",
    #     digits='Product Price',
    #     help="Specify the minimum amount of margin over the base price.")
    # price_max_margin = fields.Float(
    #     string="Max. Price Margin",
    #     digits='Product Price',
    #     help="Specify the maximum amount of margin over the base price.")
    #
    # # functional fields used for usability purposes
    # name = fields.Char(
    #     string="Name",
    #     compute='_compute_name_and_price',
    #     help="Explicit rule name for this pricelist line.")
    # price = fields.Char(
    #     string="Price",
    #     compute='_compute_name_and_price',
    #     help="Explicit rule name for this pricelist line.")
    # rule_tip = fields.Char(compute='_compute_rule_tip')
    subscription_unit = fields.Selection(selection=[('weeks', 'Weeks'), ('months', 'Months'),
                                                    ('years', 'Years')])
    duration = fields.Integer(help='Duration of the subscription')

