# -*- coding: utf-8 -*-
from odoo.addons.cyllo_rental_base.tests.common import RentalOrder


class TestRentalOrderLine(RentalOrder):

    def test_onchange_product_id(self):
        self.order_line._onchange_product_id()
        self.assertEqual(self.order_line.product_location_id, self.order_line.product_id.rental_location_id)

    def test_compute_product_uom_id(self):
        self.order_line._compute_product_uom_id()
        self.assertEqual(self.order_line.product_uom_id, self.order_line.product_id.uom_id)

    def test_compute_duration(self):
        self.order_line._compute_duration()
        self.assertEqual(self.order_line.duration, '10 days')

