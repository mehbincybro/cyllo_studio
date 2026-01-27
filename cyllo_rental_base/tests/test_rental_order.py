# -*- coding: utf-8 -*-
from odoo.addons.cyllo_rental_base.tests.common import RentalOrder


class TestRentalOrder(RentalOrder):

    def test_action_pay_extra(self):
        action = self.rental_order.action_pay_extra()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['target'], 'current')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_model'], 'account.move')

    def test_action_pay_now(self):
        action = self.rental_order.action_pay_now()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['target'], 'current')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_model'], 'account.move')

    def test_compute_return_count(self):
        self.rental_order._compute_return_count()
        self.assertEqual(self.rental_order.return_count, 0)

    def test_compute_picking_count(self):
        self.rental_order._compute_picking_count()
        self.assertEqual(self.rental_order.picking_count, 0)

    def test_compute_amount_total(self):
        self.rental_order._compute_amount_total()
        self.assertEqual(self.rental_order.amount_untaxed, 0.0)
        self.assertEqual(self.rental_order.amount_tax, 0.0)
        self.assertEqual(self.rental_order.amount_total, 0.0)

    def test_compute_partner_shipping_id(self):
        self.rental_order._compute_partner_shipping_id()
        self.assertEqual(self.rental_order.partner_shipping_id, self.partner)

    def test_compute_partner_invoice_id(self):
        self.rental_order._compute_partner_invoice_id()
        self.assertEqual(self.rental_order.partner_invoice_id, self.partner)

    def test_compute_note(self):
        self.rental_order._compute_note()
        self.assertEqual(self.rental_order.note,
                         '<p>Terms &amp; Conditions: <a href="http://localhost:8019/terms" target="_blank" rel="noreferrer noopener">http://localhost:8019/terms</a></p>')

    def test_action_confirm(self):
        self.rental_order.action_confirm()
        self.assertEqual(self.rental_order.state, 'rented')

    def test_action_print_token(self):
        action = self.rental_order.action_print_token()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['binding_type'], 'action')

    def test_action_pickup(self):
        action = self.rental_order.action_pickup()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['res_model'], 'rental.delivery')

    def test_action_see_returns(self):
        action = self.rental_order.action_see_returns()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.picking')
        self.assertEqual(action['name'], 'Returns')

    def test_action_see_deliveries(self):
        action = self.rental_order.action_see_deliveries()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['name'], 'Deliveries')
        self.assertEqual(action['res_model'], 'stock.picking')

    def test_action_ready_to_return(self):
        action = self.rental_order.action_ready_to_return()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.return.picking')
        self.assertEqual(action['view_mode'], 'form')

    def test_action_return(self):
        self.rental_order.action_return()
        self.assertEqual(self.rental_order.state, 'return')
        self.assertTrue(self.rental_order.is_returned)

    def test_action_get_invoice(self):
        action = self.rental_order.action_get_invoice()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['name'], 'invoice')
        self.assertEqual(action['res_model'], 'account.move')

    def test_get_report_base_filename(self):
        action = self.rental_order._get_report_base_filename()
        self.assertEqual(action, 'Rental Order-Test Order')
