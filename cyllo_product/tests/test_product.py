# -*- coding: utf-8 -*-
import logging
from odoo.addons.cyllo_product.tests.common import TestCyProduct

_logger = logging.getLogger(__name__)


class TestProduct(TestCyProduct):

    def test_create(self):
        vals_list = {
            'name': 'New pd',
            'list_price': 100,
            'product_approver_line_ids': self.env.ref('base.user_admin').ids,
        }
        result = self.pro_temp.create(vals_list)
        self.assertEqual(result.product_approver_line_ids[0].product_approver_id.name, 'Mitchell Admin')
        self.assertEqual(result.product_approver_line_ids[0].status, 'approved')
        self.assertFalse(result.active)
        self.pro_temp.button_approve()


