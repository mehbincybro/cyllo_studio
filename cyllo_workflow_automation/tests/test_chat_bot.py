# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_workflow_automation.models.chat_bot import (
    _clean_json_text,
    _normalize_reusable_create_payload,
    _normalize_update_payload,
)


class TestChatBotHelpers(TransactionCase):

    def test_clean_json_text_strips_fences_and_prefix(self):
        raw_text = """```json
Here is your workflow:
{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[]}
```"""
        cleaned = _clean_json_text(raw_text)
        self.assertEqual(
            cleaned,
            '{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[]}',
        )

    def test_normalize_update_payload_backfills_required_context(self):
        payload = {"actions": [{"type": "Warning"}]}
        workflow_context = {
            "mode": "update",
            "object": "sale.order",
            "trigger": "On Write",
        }

        normalized = _normalize_update_payload(payload, workflow_context)

        self.assertEqual(normalized["object"], "sale.order")
        self.assertEqual(normalized["trigger"], "On Write")
        self.assertEqual(normalized["conditions"], [])
        self.assertEqual(normalized["actions"], [{"type": "Warning"}])

    def test_normalize_reusable_create_payload_sets_blank_object(self):
        payload = {"trigger": "On Create", "actions": [{"type": "SMS"}]}
        workflow_context = {"mode": "reusable_create"}

        normalized = _normalize_reusable_create_payload(payload, workflow_context)

        self.assertEqual(normalized["object"], "")
        self.assertEqual(normalized["conditions"], [])
        self.assertEqual(normalized["trigger"], "On Create")
