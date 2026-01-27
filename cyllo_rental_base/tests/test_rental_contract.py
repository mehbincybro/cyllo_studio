# -*- coding: utf-8 -*-
from odoo.addons.cyllo_rental_base.tests.common import RentalOrder


class TestRentalContract(RentalOrder):

    def test_action_create_invoice(self):
        self.rental_contract.action_create_invoice()
        self.assertTrue(self.rental_contract.is_paid)
        self.assertEqual(self.rental_contract.state, 'in_contract')

    def test_action_get_invoice(self):
        action = self.rental_contract.action_get_invoice()
        self.assertEqual(action['name'], 'Invoice')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'account.move')

    def test_action_close(self):
        self.rental_contract.action_close()
        self.assertEqual(self.rental_contract.state, 'closed')


class TestRentalContractLines(RentalOrder):
    def test__compute_product_uom_id(self):
        self.rental_contract_line._compute_product_uom_id()
        self.assertEqual(self.rental_contract_line.product_uom_id, self.rental_contract_line.product_id.uom_id)

    def test_compute_price_unit(self):
        self.rental_contract_line._compute_price_unit()
        self.assertEqual(self.rental_contract_line.price_unit,0.0)
        self.assertFalse(self.rental_contract_line.charge_per)
