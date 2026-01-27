from odoo.tests.common import HttpCase


class TestWebsiteBlogInherit(HttpCase):

    def setUp(self):
        super(TestWebsiteBlogInherit, self).setUp()

    def test_blog(self):
        response = self.url_open('/blog')
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        super(TestWebsiteBlogInherit, self).tearDown()

