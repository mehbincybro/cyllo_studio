# -*- coding: utf-8 -*-
from odoo.tests import common


class TestCylloSmsGateway(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sms_gateway = cls.env['sms.gateway.config'].browse(2)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'mobile': '+9876543210',
        })
        cls.send_sms = cls.env['send.sms'].create({
            'sms_id': cls.sms_gateway.id,
            'sms_to': cls.partner.mobile,
            'text': 'Test Text',
            'partner_ids': cls.partner.ids,
        })
