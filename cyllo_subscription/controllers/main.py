# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.http import request, Controller
from odoo.addons.portal.controllers.portal import CustomerPortal


class SubscriptionPortal(CustomerPortal):
    """ Class to define the portal views """
    def _prepare_home_portal_values(self, counters):
        """ Function to get the count of total number of orders """
        vals = super()._prepare_home_portal_values(counters)
        if 'subscription_count' in counters:
            vals['subscription_count'] = request.env[
                'subscription.order'].sudo().search_count(
                [('partner_id', '=', request.env.user.partner_id.id)])
        return vals


class PortalControl(Controller):
    """Class created to render datas to portal"""
    @http.route(['/your_sub_orders'], type='http', auth="public", website=True)
    def _portal_sub_order_tree(self):
        """Method used to return datas to create a tree view with orders of the
         current user in the portal"""
        values = {
            'orders': request.env['subscription.order'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id),
                 ('state', 'in', ('posted', 'sale'))]),
            'active_records': request.env['subscription.order'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id),
                 ('state', 'in', ('posted', 'sale')),
                 ('state_subscription', '=', 'active')]),
            'to_renew': request.env['subscription.order'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id),
                 ('state', 'in', ('posted', 'sale')),
                 ('state_subscription', '=', 'renew')]),
            'churned': request.env['subscription.order'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id),
                 ('state', 'in', ('posted', 'sale')),
                 ('state_subscription', '=', 'churned')]),
            'trial': request.env['subscription.order'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id),
                 ('state', 'in', ('posted', 'sale')),
                 ('state_subscription', '=', 'trial')]),
            'page_name': 'Subscription_Orders'
        }
        return request.render("cyllo_subscription.subscription_orders", values)

    @http.route(['/details/<int:order_id>'], type='http', auth='public',
                website=True)
    def _portal_sub_order_form(self, order_id):
        """Method to render data to the details page of the portal"""
        values = {
            'each_order': request.env['subscription.order'].sudo().browse(
                order_id),
            'reasons': request.env['subscription.order.close.reason'].search([
                ('available_in_portal', '=', True)]),
            'page_name': 'Details'
        }
        return request.render(
            'cyllo_subscription.subscription_details', values)

    @http.route(['/your_sub_orders/close/<int:order_id>'], type='http',
                auth='public', website=True)
    def _subscription_close(self, order_id, **kwargs):
        """Method render values to the subscription close page"""
        record = request.env['subscription.order'].sudo().browse(order_id)
        records = {
            'page_name': 'Close order',
            'order': order_id,
            'orders': record
        }
        record.state_subscription = 'churned'
        record.message_post(
            body=_('Reason to close the subscription: %s', kwargs.get('reasons')), message_type='comment',
            subtype_xmlid='mail.mt_comment')
        return request.render('cyllo_subscription.subscription_closed', records)

    @http.route(['/renew_sub'], type='http', auth='public', website=True)
    def renew_order(self, **kwargs):
        """Method used to render values to renew subscription from portal"""
        request.env['subscription.order'].sudo().create({
            'partner_id': kwargs.get('partner'),
            'time_based_price_id': kwargs.get('plan'),
            'state': 'draft',
            'state_subscription': 'quotation',
            'subscription_order_line_ids': [
                        (fields.Command.create({
                            'product_id': kwargs.get('product'),
                            'subtotal': request.env['time.based.price'].sudo().browse(int(kwargs.get('plan'))).cost,
                        }))]})
        return request.redirect('/my/home')
