# -*- coding: utf-8 -*-
import logging
from odoo.tests import common
from odoo import fields

_logger = logging.getLogger(__name__)


class TestSubscriptionOrder(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'John'})
        cls.product = cls.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': True
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': False
        })
        cls.time_based = cls.env['time.based.price'].create({
            'name': 'Mon',
            'subscription_unit': 'months',
            'currency_id': 1
        })
        cls.sale_order_template = cls.env['sale.order.template'].create({
            'name': 'Template1',
            'is_subscription': True,
            'invoice_creation': 'confirmed',
            'sale_order_template_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.sale_order = cls.env['sale.order'].create({
            'name': 'S00001',
            'partner_id': cls.partner.id,
            'order_line': [
                (fields.Command.create({'product_id': cls.product.id}))
            ]
        })
        cls.subscription_order = cls.env['subscription.order'].create({
            'name': 'SO001',
            'partner_id': cls.partner.id,
            'time_based_price_id': cls.time_based.id,
            'sale_order_template_id': cls.sale_order_template.id,
            'renewal_date': '2023-11-16',
            'sale_order_id': cls.sale_order.id,
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'payment_reference': cls.subscription_order.name,
            'invoice_origin': cls.subscription_order.name,
            'invoice_date_due': '2023-12-15',
            'date': '2023-12-15',
            'is_subscription': True,
            'state': 'draft',
            'subscription_order_ids': cls.subscription_order.ids,
            'invoice_line_ids': [
                (fields.Command.create({
                    'product_id': cls.product.id,
                }))]})
        cls.sale_order2 = cls.env['sale.order'].create({
            'name': 'S00002',
            'partner_id': cls.partner.id,
            'order_line': [
                (fields.Command.create({'product_id': cls.product2.id}))
            ]
        })
        cls.subscription_order_alert = cls.env['subscription.order.alert'].create({
            'name': 'Sub alert',
            'action': 'set_to_renew'
        })

    # Test subscription.order
    def test_compute_invoice_count(self):
        _logger.info("Starts tests for so")
        self.subscription_order._compute_invoice_count()
        self.assertEqual(self.subscription_order.invoice_count, 1)
        _logger.info("Ends tests for 'so'")

    def test_compute_recurring_revenue(self):
        _logger.info("Start tests compute_recurring_revenue")
        partner = self.env['res.partner'].create({'name': 'John'})
        product = self.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': True
        })
        time_based = self.env['time.based.price'].create({
            'name': 'Mon',
            'subscription_unit': 'months',
            'currency_id': 1
        })
        subscription_order = self.env['subscription.order'].create({
            'name': 'SO001',
            'partner_id': partner.id,
            'time_based_price_id': time_based.id,
            'recurring_revenue': 1,
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': product.id}))]
        })
        subscription_order._compute_recurring_revenue()
        self.assertEqual(subscription_order.recurring_revenue, 0.0)
        _logger.info("End tests compute_recurring_revenue")

    def test_action_renew_order(self):
        _logger.info("Start tests action_renew_order")
        partner = self.env['res.partner'].create({'name': 'John'})
        product = self.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': True
        })
        time_based = self.env['time.based.price'].create({
            'name': 'Mon',
            'subscription_unit': 'months',
            'currency_id': 1
        })
        subscription_order = self.env['subscription.order'].create({
            'name': 'SO001',
            'partner_id': partner.id,
            'time_based_price_id': time_based.id,
            'recurring_revenue': 1,
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': product.id}))]
        })
        subscription_order.action_renew_order()
        self.assertFalse(self.subscription_order.check_upsell_renewal)
        _logger.info("End tests action_renew_order")

    def test_check_subscription_renewal(self):
        _logger.info("Start tests test_check_subscription_renewal")
        self.subscription_order.check_subscription_renewal()
        self.assertEqual(self.subscription_order.state_subscription, 'renew')
        _logger.info("End tests test_check_subscription_renewal")

    # Test in account.move
    def test_ir_cron_action_post(self):
        _logger.info("Start tests test_ir_cron_action_post")
        self.account_move.ir_cron_action_post()
        self.assertEqual(self.account_move.state, 'posted')
        _logger.info("Ends tests test_ir_cron_action_post")

    # Test in sale.order
    def test_compute_is_subscription(self):
        """Testing if added product is subscription"""
        _logger.info("Start tests test_compute_is_subscription")
        self.sale_order._compute_is_subscription()
        self.assertEqual(self.sale_order.is_subscription, True)
        self.sale_order2._compute_is_subscription()
        self.assertEqual(self.sale_order2.is_subscription, False)
        _logger.info("Ends tests test_compute_is_subscription")

    def test_compute_subscription_orders(self):
        _logger.info("Starts tests test_compute_subscription_orders")
        self.sale_order._compute_subscription_orders()
        self.assertEqual(self.sale_order.subscription_orders, 1)
        self.assertEqual(self.sale_order.state_subscription, 'sub_order')
        _logger.info("Ends tests test_compute_subscription_orders")

    # Test in subscription.order.alert
    def test_compute_order_count(self):
        _logger.info("Starts tests test_compute_order_count")
        self.subscription_order_alert._compute_order_count()
        _logger.info("Ends tests test_compute_order_count")

    def test_action_trigger(self):
        _logger.info("Starts tests test_action_trigger")
        self.subscription_order_alert.action_trigger()
        self.assertEqual(self.subscription_order.state_subscription, 'renew')
        _logger.info("Ends tests test_action_trigger")
