# -*- coding: utf-8 -*-
from werkzeug.exceptions import Forbidden

from odoo import _, fields, http, SUPERUSER_ID, tools
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request


class CustomerPortalInherited(sale_portal.CustomerPortal):
    """ This class extends the functionality of sale_portal.CustomerPortal by
     overriding the '_get_payment_values' method for specific purposes."""

    def _get_payment_values(self, order_sudo, website_id=None, **kwargs):
        """ Super this function for override purpose."""
        website_id = website_id or order_sudo.website_id.id
        return super(CustomerPortalInherited, self)._get_payment_values(order_sudo, website_id, **kwargs)


class PaymentPortalInherited(payment_portal.PaymentPortal):
    """ This class extends the functionality of payment_portal.PaymentPortal by
    overriding the '_compute_show_tokenize_input_mapping' method for specific purposes."""

    @http.route('/invoice/transaction/<int:invoice_id>', type='json', auth='public')
    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.
        :param int invoice_id: The invoice to pay, as an `account.move` id
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the invoice id or the access token is invalid
        """
        # Check the invoice id and the access token
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError(_("The access token is invalid."))
        logged_in = not request.env.user._is_public()
        partner_sudo = request.env.user.partner_id if logged_in else invoice_sudo.partner_id
        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            'currency_id': invoice_sudo.currency_id.id,
            'partner_id': partner_sudo.id,
        })  # Inject the create values taken from the invoice into the kwargs.
        tx_sudo = self._create_transaction(custom_create_values={'invoice_ids': [Command.set([invoice_id])]}, **kwargs)
        return tx_sudo._get_processing_values()

    def _compute_show_tokenize_input_mapping(providers, **kwargs):
        """ Determine for each provider whether the tokenization input should
        be shown or not."""
        res = super()._compute_show_tokenize_input_mapping(providers)
        return res

    def _create_transaction(self, *args, rental_order_id=None, custom_create_values=None, **kwargs):
        """ Override of payment to add the rental order id in the custom create
        values.
        :param int rental_order_id: The rental order for which a payment id
        made, as a `rental.order` id
        :param dict custom_create_values: Additional create values overwriting
        the default ones
        :return: The result of the parent method
        :rtype: recordset of `payment.transaction`
        """
        if rental_order_id:
            if custom_create_values is None:
                custom_create_values = {}
            if 'rental_order_ids' not in custom_create_values:
                custom_create_values['rental_order_ids'] = [Command.set([int(rental_order_id)])]
        return super()._create_transaction(*args, rental_order_id=rental_order_id,
                                           custom_create_values=custom_create_values, **kwargs)

    @http.route('/rental/payment/transaction/<int:order_id>', type='json', auth='public', website=True)
    def rental_payment_transaction(self, order_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.
        :param int order_id: The rental order to pay, as a `rental.order` id
        :param str access_token: The access token used to authenticate the
         request
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the invoice id or the access token is invalid
        """
        try:
            order_sudo = request.env['rental.order'].sudo().browse(order_id)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError(_("The access token is invalid."))
        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            'partner_id': order_sudo.partner_invoice_id.id,
            'currency_id': order_sudo.currency_id.id,
            'rental_order_id': order_id,
        })
        if not kwargs.get('amount'):
            kwargs['amount'] = order_sudo.amount_total
        if tools.float_compare(
                kwargs['amount'], order_sudo.amount_total,
                precision_rounding=order_sudo.currency_id.rounding):
            raise ValidationError(
                _("The rental has been updated. Please refresh the page."))
        tx_sudo = self._create_transaction(
            custom_create_values={
                'rental_order_ids': [Command.set([order_id])]}, **kwargs, )
        request.session['__website_sale_last_tx_id'] = tx_sudo.id
        self._validate_transaction_for_order(tx_sudo, order_id)
        return tx_sudo._get_processing_values()


class WebsiteSaleInherited(WebsiteSale):
    """ Inheriting WebsiteSale for making payment transactions for rental orders."""

    def rental_order_2_return_dict(self, order):
        """ Returns the tracking_cart dict of the order."""
        tracking_cart_dict = {
            'transaction_id': order.id,
            'affiliation': order.company_id.name,
            'value': order.amount_total,
            'tax': order.amount_tax,
            'currency': order.currency_id.name,
        }
        return tracking_cart_dict

    def rental_checkout_values(self, **kw):
        """ Retrieve and prepare checkout details for a rental order."""
        order = request.env['rental.order'].sudo().browse(request.session['rental_order'])
        shippings = []
        if order.partner_id != request.website.user_id.sudo().partner_id:
            partner = order.partner_id.with_context(show_address=1).sudo()
            shippings = partner.search([("id", "child_of", order.partner_id.commercial_partner_id.ids),
                                        '|', ("type", "in", ["delivery", "other"]),
                                        ("id", "=", order.partner_id.commercial_partner_id.id)], order='id desc')
            if shippings:
                if kw.get('partner_id') or 'use_billing' in kw:
                    if 'use_billing' in kw:
                        partner_id = order.partner_id.id
                    else:
                        partner_id = int(kw.get('partner_id'))
                    if partner_id in shippings.mapped('id'):
                        order.partner_shipping_id = partner_id
        values = {
            'order': order,
            'shippings': shippings,
            'amount_total': order.amount_total,
        }
        return values

    def _get_country_related_render_values_rental(self, kw, render_values):
        """ This method provides fields related to the country to render the
         rental order."""
        values = render_values['checkout']
        mode = render_values['mode']
        order = render_values['website_sale_order']
        def_country_id = order.partner_id.country_id
        if order._is_public_order():
            if request.geoip.country_code:
                def_country_id = request.env['res.country'].search([('code', '=', request.geoip.country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id

        country = 'country_id' in values and values['country_id'] != '' and \
                  request.env['res.country'].browse(int(values['country_id']))
        country = country and country.exists() or def_country_id
        res = {
            'country': country,
            'country_states': country.get_website_sale_states(mode=mode[1]),
            'countries': country.get_website_sale_countries(mode=mode[1]),
        }
        return res

    @http.route(['/rental_order/payment'], type='http', auth="public", website=True, sitemap=False)
    def rental_checkout(self, **post):
        """ Perform the checkout process for a rental order."""
        order = request.env['rental.order'].sudo().browse(
            request.session['rental_order'])
        redirection = self.rental_checkout_redirection(order)
        if redirection:
            return redirection
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            return request.redirect('/rental/address')
        redirection = self.rental_checkout_check_address(order)
        if redirection:
            return redirection
        values = self.rental_checkout_values(**post)
        if post.get('express'):
            return request.redirect('/rental/confirm_order')
        values.update({'rental_order': order})
        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("cyllo_rental_base.rental_checkout", values)

    @http.route(['/rental/confirm_order'], type='http', auth="public", website=True, sitemap=False)
    def confirm_rental_order(self, **post):
        """ Confirm a rental order for processing."""
        order = request.env['rental.order'].sudo().browse(request.session['rental_order'])
        redirection = (self.rental_checkout_redirection(order) or self.rental_checkout_check_address(order))
        if redirection:
            return redirection
        request.session['rental_last_order_id'] = order.id
        return request.redirect("/rental/payment")

    def _get_express_rental_payment_values(self, order, **kwargs):
        """ Calculate and return payment values for processing transactions in an express rental checkout scenario."""
        request.session['sale_last_order_id'] = order.id
        payment_form_values = sale_portal.CustomerPortal._get_payment_values(self, order, **kwargs)
        payment_form_values.update({
            'payment_access_token': payment_form_values.pop('access_token'),
            'minor_amount': payment_utils.to_minor_currency_units(order.amount_total, order.currency_id),
            'merchant_name': request.website.name,
            'transaction_route': f'/rental/payment/transaction/{order.id}',
            'express_checkout_route': self._express_checkout_route,
            'landing_route': f'/rental/payment/validate/{order.id}',
        })
        if request.website.is_public_user():
            payment_form_values['partner_id'] = -1
        if request.website.enabled_delivery:
            payment_form_values.update({
                'shipping_info_required': not order.only_services,
                'shipping_address_update_route': self.
                _express_checkout_shipping_route,
            })
        return payment_form_values

    def _get_rental_payment_values(self, order, **kwargs):
        """ Retrieve payment values specific to a rental order."""
        checkout_page_values = {
            'rental_order': order,
            'errors': [],
            'partner': order.partner_invoice_id,
            'order': order,
            'payment_action_id': request.env.ref('payment.action_payment_provider').id,
            'action_activate_stripe_id': request.env.ref('website_payment.action_activate_stripe').id,
        }
        payment_form_values = {
            **sale_portal.CustomerPortal._get_payment_values(self, order, website_id=request.website.id),
            'display_submit_button': False,
            'transaction_route': f'/rental/payment/transaction/{order.id}',
            'landing_route': f'/rental/payment/validate/{order.id}',
        }
        values = {**checkout_page_values, **payment_form_values}
        if request.website.enabled_delivery:
            has_storable_products = any(line.product_id.type in ['consu', 'product'] for line in order.order_line_ids)
            values['delivery_has_storable'] = has_storable_products
            values['delivery_action_id'] = request.env.ref('delivery.action_delivery_carrier_form').id
        return values

    @http.route('/rental/payment/', type='http', auth='public', website=True, sitemap=False)
    def rental_payment(self, **post):
        """ Payment step. This page proposes several payment means based on available payment.provider."""
        order = request.env['rental.order'].sudo().browse(request.session['rental_order'])
        if order and (request.httprequest.method == 'POST'):
            carrier_id = post.get('carrier_id')
            keep_carrier = post.get('keep_carrier', False)
            if keep_carrier:
                keep_carrier = bool(int(keep_carrier))
            if carrier_id:
                carrier_id = int(carrier_id)
            order._check_carrier_quotation(force_carrier_id=carrier_id, keep_carrier=keep_carrier)
            if carrier_id:
                return request.redirect("/rental/payment")
        render_values = self._get_rental_payment_values(order, **post)
        providers = request.env['payment.provider'].sudo().search([('state', 'in', ['test', 'enabled'])])
        providers_vals = (payment_portal.PaymentPortal._compute_show_tokenize_input_mapping(providers))
        if render_values['errors']:
            render_values.pop('payment_methods_sudo', '')
            render_values.pop('tokens_sudo', '')
        render_values.update({
            'providers': providers,
            'show_tokenize_input': providers_vals
        })
        return request.render("cyllo_rental_base.rental_payment", render_values)

    @http.route('/rental/payment/validate/<int:rental_order_id>', type='http',
                auth='public', website=True, sitemap=False)
    def rental_payment_validate(self, rental_order_id, **post):
        """ Method that should be called by the server when receiving an update for a transaction."""
        if rental_order_id is None:
            order = request.env['rental.order'].sudo().search([], order="create_date desc", limit=1)
            if not order and 'sale_last_order_id' in request.session:
                last_order_id = request.session['sale_last_order_id']
                order = request.env['rental.order'].sudo().browse(last_order_id).exists()
        else:
            order = request.env['rental.order'].sudo().browse(rental_order_id)
        tx_sudo = order.get_portal_last_transaction() if order else order.env['payment.transaction']
        if not order or (order.amount_total and not tx_sudo):
            return request.redirect('/rental')
        if order and not order.amount_total and not tx_sudo:
            order.with_context(send_email=True).with_user(SUPERUSER_ID).action_confirm()
            return request.redirect(order.get_portal_url())
        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx_sudo and tx_sudo.state == 'draft':
            return request.redirect('/rental')
        return request.redirect('/rental/confirmation')

    @http.route(['/rental/confirmation'], type='http', auth="public", website=True, sitemap=False)
    def rental_payment_confirmation(self, **post):
        """ End of checkout process controller."""
        rental_order_id = request.env['rental.order'].sudo().browse(request.session['rental_order'])
        if rental_order_id:
            rental_order_id.action_pay_now()
            values = self._prepare_rental_payment_confirmation_values(rental_order_id)
            return request.render("cyllo_rental_base.rental_confirmation", values)
        else:
            return request.redirect('/rental')

    def _rental_checkout_form_save(self, mode, checkout, all_values):
        """ Save rental checkout information for a partner."""
        partner_id = request.env['res.partner']
        if mode[0] == 'new':
            partner_id = request.env['res.partner'].sudo().with_context(tracking_disable=True).create(checkout).id
        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                order = request.env['rental.order'].sudo().search([], order="create_date desc", limit=1)
                shippings = request.env['res.partner'].sudo().search([("id", "child_of",
                                                                       order.partner_id.commercial_partner_id.ids)])
                if (partner_id not in shippings.mapped('id') and partner_id != order.partner_id.id):
                    return Forbidden()
                request.env['res.partner'].browse(partner_id).sudo().write(checkout)
        return partner_id

    def _prepare_rental_payment_confirmation_values(self, order):
        """ Prepare and return payment confirmation values for a rental order."""
        return {
            'order': order,
            'order_tracking_info': self.rental_order_2_return_dict(order),
        }

    @http.route(['/rental/address'], type='http', methods=['GET', 'POST'],
                auth="public", website=True, sitemap=False)
    def rental_address(self, **kw):
        """ Manage address selection and validation for a rental order,
        including cases where the order is associated with a partner or is a
        public order. Guide the user through the address selection process and
        proceed to the next rental order step, such as payment or order
        confirmation."""
        partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.env['rental.order'].sudo().browse(request.session['rental_order'])
        redirection = self.rental_checkout_redirection(order)
        if redirection:
            return redirection
        can_edit_vat = False
        values, errors = {}, {}
        partner_id = int(kw.get('partner_id', -1))
        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            can_edit_vat = True
        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                    can_edit_vat = order.partner_id.can_edit_vat()
                else:
                    shippings = partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                    if order.partner_id.commercial_partner_id.id == partner_id:
                        mode = ('new', 'shipping')
                        partner_id = -1
                    elif partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode and partner_id != -1:
                    values = partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/rental/payment')
        # IF POSTED
        if 'submitted' in kw and request.httprequest.method == "POST":
            pre_values = self.values_preprocess(kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)
            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._rental_checkout_form_save(mode, post, kw)
                if isinstance(partner_id, Forbidden):
                    return partner_id
                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.partner_invoice_id = partner_id
                    if not kw.get('use_same'):
                        kw['callback'] = (kw.get('callback') or (mode[0] == 'edit' and '/rental_order/payment' or
                                                                 '/rental/address'))
                    if kw.get('callback', False) != '/rental_order/payment':
                        request.website.sale_get_order(update_pricelist=True)
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id
                order.message_partner_ids = [Command.link(partner_id), Command.unlink(request.website.partner_id.id)]
                if not errors:
                    return request.redirect(kw.get('callback') or '/rental/payment')
        render_values = {
            'website_sale_order': order,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'can_edit_vat': can_edit_vat,
            'error': errors,
            'callback': kw.get('callback'),
            'account_on_checkout': request.website.account_on_checkout,
            'is_public_user': request.website.is_public_user()
        }
        render_values.update(self._get_country_related_render_values_rental(kw, render_values))
        return request.render("cyllo_rental_base.rental_address", render_values)

    def rental_checkout_check_address(self, order):
        """ Check if the required address information is provided for billing and shipping."""
        billing_fields_required = self._get_mandatory_fields_billing(
            order.partner_id.country_id.id)
        if not all(order.partner_id.read(billing_fields_required)[0].values()):
            return request.redirect('/rental/address?partner_id=%d' % order.partner_id.id)
        shipping_fields_required = self._get_mandatory_fields_shipping(
            order.partner_shipping_id.country_id.id)
        if not all(order.partner_shipping_id.read(shipping_fields_required)[0].values()):
            return request.redirect('/rental/address?partner_id=%d' % order.partner_shipping_id.id)

    def rental_checkout_redirection(self, order):
        """ Redirect based on the state of a rental order. It ensures that the
        order is in the rented state and contains order lines.
        Also handles cases where user login is mandatory before proceeding to
        checkout."""
        # must have a rented rental order with lines at this point, otherwise
        # reset
        if not order or (order.state not in ['rented', 'partial_return']):
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/rental')
        if order and not order.order_line_ids:
            return request.redirect('/rental')
        if (request.website.is_public_user() and request.website.account_on_checkout == 'mandatory'):
            return request.redirect('/web/login?redirect=/rental/payment')
        tx = request.env.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/rental/payment')

    @http.route(['/rental/print'], type='http', auth="public", website=True, sitemap=False)
    def print_rental_order(self, **kwargs):
        """ Generate and display a PDF of the rental order."""
        rental_order_id = request.env['rental.order'].sudo().search([], order="create_date desc", limit=1)
        if rental_order_id:
            pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'cyllo_rental_base.report_action_rental_order', [rental_order_id.id])
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/rental')


class RentalOrderPortal(portal.PaymentPortal):
    """ Class to specify the route and template for rental order document"""

    @http.route(['/my/rentals'], type='http', auth='user', website=True)
    def get_rental_orders(self):
        """Function to get rental orders in portal"""
        model = request.env['rental.order'].sudo()
        partner_id = request.env.user.partner_id.id
        domain = ('partner_id', '=', partner_id)
        return request.render("cyllo_rental_base.rental_order_data", {
            'all_records': model.search([domain]),
            'draft_records': model.search([('state', '=', 'draft'), domain]),
            'rented_records': model.search([('state', '=', 'rented'), domain]),
            'return_records': model.search([('state', '=', 'return'), domain]),
            'page_name': 'rental_record'
        })

    @http.route(['/confirm/stock-return-orders'], type="json", auth="public", website=True)
    def confirm_stock_return(self, **kw):
        request.env['stock.return.picking'].sudo().browse(int(kw.get('pick_id'))).create_returns()
        return True

    @http.route(['/update/stock-return-orders'], type="json", auth="public", website=True)
    def update_stock_return(self, **kw):
        request.env['stock.return.picking.line'].sudo().browse(
            int(kw.get('pick_id'))).update({'quantity': int(kw.get('quantity'))})

    @http.route(['/create/stock-return-orders'], type="json", auth="public", website=True)
    def create_stock_return(self, **kw):
        return_id = request.env['stock.return.picking'].sudo().create({'picking_id': int(kw.get('pick_id'))})
        return {'pick_id': return_id.id, 'lines': [
            {'id': line.id, 'name': line.product_id.name,
             'quantity': line.quantity} for line in return_id.product_return_moves]}

    @http.route(['/rental-return'], type="json", auth="public", website=True)
    def rental_return_modal(self, **kwargs):
        """Function for adding values to the modal"""
        return request.env['rental.order'].sudo().browse(
            int(kwargs['rental_order_id'])).action_ready_to_return()

    @http.route('/my/rentals/record/<int:record_id>', type='http', auth="public", website=True)
    def my_rental_order_record_select(self, record_id, report_type=None, download=True):
        """Function to get details of rental orders in the portal"""
        request.session['rental_order'] = record_id
        record = request.env['rental.order'].sudo().browse(record_id)
        records = request.env['rental.order'].sudo().search([('partner_id', '=', request.env.user.partner_id.id)]).ids
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=record, report_type=report_type,
                                     report_ref='cyllo_rental_base.report_rental_order', download=download)
        index = records.index(record_id) if record_id in records else -1
        prev_record = records[index - 1] if index > 0 else False
        next_record = records[index + 1] if index < len(records) - 1 else False
        return request.render("cyllo_rental_base.portal_rental_order_record_template", {
            'prev_record': f'/my/rentals/record/{prev_record}' if prev_record else False,
            'next_record': f'/my/rentals/record/{next_record}' if next_record else False,
            'object': record,
            'page_name': 'rental_portal_form'
        })

    @http.route(['/rental/cart'], type='http', auth="public", website=True, sitemap=False)
    def rental_cart(self, access_token=None, **post):
        """Display the rental cart page with the list of rental orders and order lines.
        Return: A response rendering the 'cyllo_rental_base.rental_cart_order'
        template with the rental orders and order lines."""
        rental_orders = request.env['rental.order'].sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id),
             ('website_id', '=', request.env.get('website_id', request.website_routing)),
             ('is_invoiced', '=', False)])
        if rental_orders:
            total_quantity = sum(rental_orders.order_line_ids.mapped('product_uom_qty'))
            request.session['rental_cart_quantity'] = total_quantity
        else:
            request.session['rental_cart_quantity'] = None
        rental_order_lines = request.env['rental.order.line'].sudo().search([('order_id', 'in', rental_orders.ids)])
        return request.render("cyllo_rental_base.rental_cart_order", {
            'orders': rental_orders, 'rental_order_lines': rental_order_lines})

    @http.route(['/update/rental/cart'], type="json", auth="public", website=True, methods=['POST'], csrf=False)
    def _update_rental_cart(self, **kwargs):
        """Update the rental cart based on the provided data.
        :return: A dictionary containing values for updating the rental cart UI."""
        order_line = request.env['rental.order.line'].sudo().browse(kwargs['line_id'])
        order_line.product_uom_qty = kwargs['quantity']
        order = request.env['rental.order'].sudo().browse(kwargs['order_id'])
        values = {'total_amount': order.amount_total, 'untaxed_total': order.amount_untaxed, 'tax': order.amount_tax,
                  'currency_symbol': order.currency_id.symbol,
                  're_render': request.env['ir.ui.view']._render_template("cyllo_rental_base.rental_cart_order")}
        if order:
            total_quantity = sum(order.order_line_ids.mapped('product_uom_qty')) or 0
            request.session['rental_cart_quantity'] = total_quantity
            values['rental_cart_quantity'] = total_quantity
            values['rental_total_template'] = request.env['ir.ui.view']._render_template(
                "cyllo_rental_base.rental_cart_total", {'orders': order})
            if len(order.order_line_ids) == 1:
                if order.order_line_ids.product_uom_qty == 0:
                    order.unlink()
        if order_line.product_uom_qty == 0:
            order_line.sudo().unlink()
            values['re_render'] = ""
            values['reload'] = True
        else:
            values['line_sub_total'] = order_line.price_subtotal
            values['re_render'] = request.env['ir.ui.view']._render_template(
                "cyllo_rental_base.line_total", {'line': order_line})
        return values

    @http.route(['/rental-extra-payment'], type="http", website=True, auth="public")
    def rental_extra_payment(self):
        """Function for the website extra payment"""
        rental_order = request.env['rental.order'].sudo().browse(request.session['rental_order'])
        invoiced_products = rental_order.sudo().payment_id.invoice_line_ids.mapped('product_id')
        invoice_lines = []
        for line in rental_order.order_line_ids:
            if line.product_id.id not in invoiced_products.ids:
                invoice_lines.append(Command.create({
                    'name': line.product_id.name,
                    'quantity': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'product_id': line.product_id.id,
                }))
        new_invoice = request.env['account.move'].sudo().create({
            'partner_id': request.env.user.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Datetime.now(),
            'invoice_line_ids': invoice_lines
        })
        new_invoice.action_post()
        rental_order.payment_ids = [Command.link(new_invoice.id)]
        rental_order.extra_time_invoice_id = new_invoice.id
        return request.redirect('/my/invoices/%s?access_token=%s' % (new_invoice.id, request.csrf_token()))
