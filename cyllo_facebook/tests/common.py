from odoo.tests.common import TransactionCase


class TestEnvSetup(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
