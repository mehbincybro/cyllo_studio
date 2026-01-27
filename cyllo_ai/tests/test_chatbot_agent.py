# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo.tests.common import TransactionCase

class TestChatbotAgent(TransactionCase):
    """
    Test cases for 'chatbot.agent' model, focusing on query validation,
    normalization, and ORM query building.
    """

    def setUp(self):
        """
        Setup test environment for chatbot agent tests.
        """
        super(TestChatbotAgent, self).setUp()
        self.ChatbotAgent = self.env['chatbot.agent']
        
    def test_is_risky_query(self):
        """
        Test the detection of potentially risky queries that involve data modification.
        """
        safe_queries = [
            "env['res.partner'].search([])",
            "self.env['product.product'].browse(1).name",
            "select * from res_partner"
        ]
        risky_queries = [
            "env['res.partner'].create({'name': 'Hack'})",
            "record.write({'name': 'Hack'})",
            "record.unlink()",
            "env['res.users'].sudo().create({})"
        ]
        
        for q in safe_queries:
            self.assertFalse(self.ChatbotAgent._is_risky_query(q), f"Query should be safe: {q}")
            
        for q in risky_queries:
            self.assertTrue(self.ChatbotAgent._is_risky_query(q), f"Query should be risky: {q}")

    def test_normalize_main_table(self):
        """
        Test the normalization of table names and aliases for SQL/ORM processing.
        """
        # String input
        res = self.ChatbotAgent._normalize_main_table("res_partner")
        self.assertEqual(res, {"name": "res_partner", "alias": "res_partner"})
        
        # Dict input
        res_dict = self.ChatbotAgent._normalize_main_table({"name": "sale_order", "alias": "so"})
        self.assertEqual(res_dict, {"name": "sale_order", "alias": "so"})
        
        # Dict partial
        res_partial = self.ChatbotAgent._normalize_main_table({"table": "stock_picking"})
        self.assertEqual(res_partial["name"], "stock_picking")

    def test_build_orm_query_string_valid(self):
        """
        Test building a valid ORM query string from a structured plan.
        """
        plan = {
            "action": "create",
            "model": "res.partner",
            "data": [{"field": "name", "value": "Test Partner"}],
            "lines": []
        }
        res = self.ChatbotAgent._build_orm_query_string(plan)
        self.assertEqual(res["error"], "")
        self.assertIn("env['res.partner'].create", res["query"])
        self.assertIn("'name': 'Test Partner'", res["query"])

    def test_build_orm_query_string_error(self):
        """
        Test error handling when building an ORM query string with invalid parameters.
        """
        plan = {
            "action": "create",
            "model": "", # Missing model
            "data": []
        }
        res = self.ChatbotAgent._build_orm_query_string(plan)
        self.assertNotEqual(res["error"], "")
        self.assertEqual(res["query"], "")

    def test_get_model_from_table(self):
        """
        Test resolving Odoo model names from database table names.
        """
        # Case 1: Existing model
        res = self.ChatbotAgent._get_model_from_table(["res_partner"])
        self.assertEqual(res, ["res.partner"])

        # Case 2: Model name passed
        res_model = self.ChatbotAgent._get_model_from_table(["res.users"])
        self.assertEqual(res_model, ["res.users"])

    def test_get_fields_for_models(self):
        """
        Test retrieving field metadata for a given list of Odoo models.
        """
        fields_map = self.ChatbotAgent._get_fields_for_models(["res.partner"])
        self.assertIn("res.partner", fields_map)
        self.assertTrue(len(fields_map["res.partner"]) > 0)
        self.assertIn("name", fields_map["res.partner"])
