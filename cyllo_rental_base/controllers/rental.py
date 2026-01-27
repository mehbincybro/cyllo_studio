# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _, http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.fields import Command


class WebsiteSaleInherited(WebsiteSale):
    """ Rental Products """
    @http.route(['/rental/', '/rental/<int:category>', ], type='http', auth="public", website=True)
    def rental_shop(self, category=None, **kwargs):
        """ Shows Rental Products """
        if kwargs:
            website_product_ids = request.env['product.product'].sudo().search(
                [('is_rental', '=', True), ('name', 'ilike', kwargs['search']), ('rental_charging_ids', '!=', False)])
        else:
            website_product_ids = request.env['product.product'].sudo().search([('is_rental', '=', True),
                                                                                ('rental_charging_ids', '!=', False)])
        categories = request.env['product.public.category'].sudo().search([])
        if category:
            website_product_ids = request.env['product.product'].sudo().search(
                [('is_rental', '=', True), ('rental_charging_ids', '!=', False),
                 ('public_categ_ids', '=', int(category))])
        return request.render('cyllo_rental_base.rental_shop', {
            'products': website_product_ids,
            'categories': categories,
            'categ_id': category if category else False,
            'search': kwargs['search'] if kwargs else False,
            'search_count': len(website_product_ids.ids) if kwargs else False
        })

    @http.route(['/rental_shop/product/<int:product_id>'], type='http', auth="public", website=True)
    def rental_products(self, product_id):
        """ Product details """
        product = request.env['product.product'].sudo().browse(product_id)
        return request.render('cyllo_rental_base.rental_product_details', {'product': product})

    @http.route(['/create/rental_order'], type='http', auth="public", website=True, sitemap=False)
    def create_rental_order(self, **kwargs):
        """ Create Rental Order """
        format_string = "%Y-%m-%dT%H:%M"
        product = request.env['product.product'].sudo().browse(int(kwargs.get('Product ID')))
        user_timezone = pytz.timezone(request.env.user.tz or 'UTC')
        pickup_time = user_timezone.localize(datetime.strptime(kwargs.get('Date'), format_string)).astimezone(
            user_timezone)
        return_time = user_timezone.localize(datetime.strptime(kwargs.get('Return Date'), format_string)).astimezone(
            user_timezone)
        pickup_time = pickup_time - pickup_time.utcoffset()
        return_time = return_time - return_time.utcoffset()
        if product.qty_available < int(kwargs.get('Quantity')):
            raise ValidationError(_("Only" + str(product.qty_available) + "Available"))
        else:
            rental_order = request.env['rental.order'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id),
                 ('website_id', '=', request.env.get('website_id', request.website_routing)),
                 ('is_invoiced', '=', False)])
            if rental_order:
                rental_order.sudo().write({
                    'order_line_ids': [Command.create({
                        'product_id': int(kwargs.get('Product ID')),
                        'pickup_date': pickup_time.replace(tzinfo=None),
                        'return_date': return_time.replace(tzinfo=None),
                        'name': kwargs.get('Product Name'),
                        'product_uom_qty': kwargs.get('Quantity')
                    })]
                })
            else:
                rental_order = rental_order.sudo().create({
                    'partner_id': request.env.user.partner_id.id,
                    'state': 'draft',
                    'website_id': request.env.get('website_id', request.website_routing),
                    'user_id': False,
                    'order_line_ids': [Command.create({
                        'product_id': int(kwargs.get('Product ID')),
                        'pickup_date': pickup_time.replace(tzinfo=None),
                        'return_date': return_time.replace(tzinfo=None),
                        'name': kwargs.get('Product Name'),
                        'product_uom_qty': kwargs.get('Quantity')
                    })]
                })
            total_quantity = sum(rental_order.order_line_ids.mapped('product_uom_qty'))
            request.session['rental_cart_quantity'] = total_quantity
            request.session['rental_order'] = rental_order.id
            return request.redirect(f"rental_shop/product/{int(kwargs.get('Product ID'))}")

    @http.route('/rental_charge', type='json', auth='public')
    def rental_charge(self, **kwargs):
        """ Rental pricing of products """
        start_date = datetime.fromtimestamp(kwargs['dates']['start_date'] / 1000)
        end_date = datetime.fromtimestamp(kwargs['dates']['end_date'] / 1000)
        user_timezone = pytz.timezone(request.env.user.tz or 'UTC')
        start_date = start_date.astimezone(user_timezone)
        end_date = end_date.astimezone(user_timezone)
        difference = relativedelta(end_date, start_date)
        price_rules = request.env['rental.charging'].sudo().search([('product_id', '=', int(kwargs['p_id']))])
        available_prices = {}
        for period in ['hours', 'days', 'months', 'years']:
            period_cost = price_rules.filtered(lambda b: b.rental_period == period).mapped('price')
            if period_cost:
                available_prices[period] = period_cost[0]
        yearly_cost = 0
        monthly_cost = 0
        daily_cost = 0
        hourly_cost = 0
        if difference.years:
            if 'years' in available_prices:
                yearly_cost = difference.years * available_prices['years']
            elif 'months' in available_prices:
                yearly_cost = difference.years * 12 * available_prices['months']
            elif 'days' in available_prices:
                yearly_cost = difference.years * 365 * available_prices['days']
            else:
                yearly_cost = difference.years * 8760 * available_prices['hours']
        if difference.months:
            if 'months' in available_prices:
                monthly_cost = difference.months * available_prices['months']
            elif 'days' in available_prices:
                monthly_cost = difference.months * 30 * available_prices['days']
            elif 'hours' in available_prices:
                monthly_cost = difference.months * 7200 * available_prices['hours']
            else:
                monthly_cost = (difference.months / 12) * available_prices['years']
        if difference.days:
            if 'days' in available_prices:
                daily_cost = difference.days * available_prices['days']
            elif 'hours' in available_prices:
                daily_cost = difference.days * 24 * available_prices['hours']
            elif 'months' in available_prices:
                daily_cost = (difference.days / 30) * available_prices['months']
            else:
                daily_cost = (difference.days / 365) * available_prices['years']
        if difference.hours:
            if 'hours' in available_prices:
                hourly_cost = difference.hours * available_prices['hours']
            elif 'days' in available_prices:
                hourly_cost = (difference.hours / 24) * available_prices['days']
            elif 'months' in available_prices:
                hourly_cost = (difference.hours / 7200) * available_prices['months']
            else:
                hourly_cost = (difference.hours / 8760) * available_prices['years']
        periods = price_rules.mapped('rental_period')
        duration = ""
        if difference.years:
            duration += f"{difference.years} years "
        if difference.months:
            duration += f"{difference.months} months "
        if difference.days:
            duration += f"{difference.days} days "
        if difference.hours:
            duration += f"{difference.hours} hours"
        rental_price_rules = {}
        for lines in price_rules:
            rental_price_rules[lines.rental_period] = (lines.price, lines.rental_period)
        currency_symbol = request.env.ref('base.main_company').sudo().currency_id.symbol
        return {
            'periods': periods,
            'sub_total': yearly_cost + monthly_cost + daily_cost + hourly_cost,
            'duration': duration,
            'currency_symbol': currency_symbol, 'rental_price_rules': rental_price_rules}

    @http.route("/rental/search", type="http", website=True, auth='public')
    def product_search(self, **kwargs):
        """Handle product search and redirect to the search results page."""
        return request.redirect('/rental/?' + '&'.join(f'{key}={value}' for key, value in kwargs.items()))

    @http.route("/rental/product", type="json", website=True, auth="public")
    def get_product_details(self, **kw):
        """Get details of a specific product."""
        product = request.env['product.product'].sudo().search_read([('id', '=', int(kw['product_id']))])
        return product
