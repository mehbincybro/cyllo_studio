# -*- coding: utf-8 -*-
from odoo.tests import common


class TestCyProduct(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pro_approve = cls.env['product.approve'].create({
            'product_approver_id': cls.env.user.id,
            'status': 'pending',
        })
        cls.pro_temp = cls.env['product.template'].create({
            'name': 'Test pro',
            'product_approver_line_ids': cls.pro_approve.ids,
            'list_price': 100,
        })
