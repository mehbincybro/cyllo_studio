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
import json
import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# ── Validation constants ─────────────────────────────────────────────────────
_REQUIRED_KEYS      = {'object', 'trigger', 'conditions', 'actions'}
_VALID_TRIGGERS     = {'On Create', 'On Write', 'On Unlink'}
_VALID_ACTION_TYPES = {'Warning', 'Mail', 'SMS', 'Activity', 'Write'}

# ── Prompt ───────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a Cyllo 17 workflow automation expert.
Your ONLY job is to convert a natural language request into a single JSON object.

ABSOLUTE RULES — violating any rule makes your output unusable:
1. Return RAW JSON and nothing else. No markdown fences, no explanation, no preamble, no trailing text.
2. The JSON must have exactly four top-level keys: "object", "trigger", "conditions", "actions".
3. Every string value must use double quotes. Numbers must be unquoted. Booleans: true / false.
4. If you are unsure about any field, pick the most reasonable default rather than omitting it.

FIELD: "object"  - Cyllo technical model name (string)
Use the exact technical name. Common mappings:
  Sales Order            -> "sale.order"
  Purchase Order         -> "purchase.order"
  Invoice / Bill         -> "account.move"
  Contact / Partner      -> "res.partner"
  Product                -> "product.template"
  Product Variant        -> "product.product"
  Employee               -> "hr.employee"
  CRM Lead / Opportunity -> "crm.lead"
  Project Task           -> "project.task"
  Stock Picking          -> "stock.picking"
  Manufacturing Order    -> "mrp.production"
  Expense                -> "hr.expense"
  Leave / Time Off       -> "hr.leave"
  Payslip                -> "hr.payslip"
  Helpdesk Ticket        -> "helpdesk.ticket"

FIELD: "trigger"  - EXACTLY one of these three strings
  "On Create"  -> new record is saved for the first time
  "On Write"   -> existing record is updated / confirmed / validated
  "On Unlink"  -> record is deleted

Selection rules:
  "posted", "confirmed", "validated", "approved", "done"  -> "On Write"
  "created", "new", "added", "submitted"                  -> "On Create"
  "deleted", "removed", "archived"                        -> "On Unlink"
  Ambiguous or unspecified                                -> "On Write"

FIELD: "conditions"  - array (use [] when there are no conditions)
Each condition object:
{
  "field":    "<technical_field_name_or_dotted_path>",
  "operator": "=" | "!=" | ">" | "<" | ">=" | "<=",
  "value":    <string | number | boolean>
}

CRITICAL RULE FOR FIELD PATHS:
- If the condition is about a field on the main record itself, use the direct field name.
  Example: sale.order.amount_total -> "field": "amount_total"
- If the condition is about a field on a related sub-record (one2many / many2many line),
  use a dotted path: "<relation_field>.<sub_field>".
  Example: checking product quantity on a sale order line -> "field": "order_line.product_uom_qty"
  Example: checking a tag on a contact -> "field": "category_id.name"

Common DIRECT fields per model:
  sale.order     : state (draft|sent|sale|done|cancel), amount_total, partner_id
  purchase.order : state (draft|sent|purchase|done|cancel), amount_total
  account.move   : state (draft|posted|cancel), amount_total, payment_state, move_type
  crm.lead       : expected_revenue, stage_id, probability
  hr.leave       : state (draft|confirm|validate1|validate|refuse), number_of_days
  project.task   : stage_id, priority (0|1)
  hr.employee    : active, department_id
  res.partner    : country_id, category_id, customer_rank, supplier_rank, is_company

Common RELATIONAL (dotted) paths:
  Sale order lines (sale.order):
    order_line.product_uom_qty   -> quantity of any product in the order lines
    order_line.price_unit        -> unit price on any order line
    order_line.discount          -> discount on any order line
    order_line.product_id        -> product on any order line
  Purchase order lines (purchase.order):
    order_line.product_qty       -> quantity on any purchase order line
    order_line.price_unit        -> unit price on any purchase order line
    order_line.product_id        -> product on any purchase order line
  Invoice lines (account.move):
    invoice_line_ids.quantity    -> quantity on any invoice line
    invoice_line_ids.price_unit  -> unit price on any invoice line
    invoice_line_ids.product_id  -> product on any invoice line
  Contact (res.partner):
    country_id.name              -> country name of the contact
    category_id.name             -> tag name of the contact

Value rules:
  - Selection fields: use technical key e.g. "posted" not "Posted"
  - Numbers must be numeric type: 2000 not "2000"
  - Use "=" not "==" as the equality operator
  - For dotted paths: use the value appropriate to the SUB-field type

FIELD: "actions"  - array with at least one item
Use EXACTLY these "type" values. Include ALL listed keys for the chosen type.

TYPE "Warning":
Use "warning_type": "error" for Python exceptions (blocks execution).
Use "warning_type": "notification" for UI pop-up notifications (non-blocking).

When warning_type is "error":
{
  "type":         "Warning",
  "label":        "<short canvas title>",
  "warning_type": "error",
  "warning":      "UserError" | "ValidationError" | "AccessError",
  "message":      "<error message shown to the user>"
}

When warning_type is "notification":
{
  "type":               "Warning",
  "label":              "<short canvas title>",
  "warning_type":       "notification",
  "notification_type":  "success" | "info" | "warning" | "danger",
  "notification_title": "<short notification title>",
  "message":            "<notification body text>",
  "sticky":             true | false
}

TYPE "Mail":
{
  "type":           "Mail",
  "label":          "<short canvas title>",
  "subject":        "<email subject line>",
  "body":           "<full email body>",
  "recipient_role": "current_user" | "assigned_user" | "customer" | "partner" | "employee"
}

TYPE "SMS":
{
  "type":           "SMS",
  "label":          "<short canvas title>",
  "message":        "<SMS text max 160 chars>",
  "recipient_role": "current_user" | "assigned_user" | "customer" | "partner" | "employee"
}

TYPE "Activity":
{
  "type":               "Activity",
  "label":              "<short canvas title>",
  "activity_type_name": "<Odoo activity type name — see mapping below>",
  "summary":            "<activity description shown in the chatter>",
  "assignee_role":      "current_user" | "assigned_user",
  "deadline":           "<YYYY-MM-DD if explicitly given, otherwise empty string>"
}

  activity_type_name mapping:
    "email" / "e-mail" / "send email" / "mail activity"  -> "Email"
    "call" / "phone call" / "phone"                       -> "Phone Call"
    "meeting" / "schedule meeting" / "calendar"           -> "Meeting"
    "to-do" / "todo" / "task" / "follow up" / unspecified -> "To-Do"
    "upload document" / "document" / "file"               -> "Upload Document"

TYPE "Write":
{
  "type":  "Write",
  "label": "<short canvas title>",
  "field": "<technical field name to update>",
  "value": <new value — correct type: string, number, or boolean>
}

EXAMPLES:

Query: Raise an error on Sale Order if discount > 50
{"object":"sale.order","trigger":"On Create","conditions":[{"field":"order_line.discount","operator":">","value":50}],"actions":[{"type":"Warning","label":"High Discount Warning","warning_type":"error","warning":"UserError","message":"Discount exceeds 50%. Please review before confirming."}]}

Query: Add a discount when a sale order is created and any product has a quantity greater than 2 apply a 3% discount
{"object":"sale.order","trigger":"On Create","conditions":[{"field":"order_line.product_uom_qty","operator":">","value":2}],"actions":[{"type":"Write","label":"Apply 3% Discount","field":"order_line.discount","value":3}]}

Query: On write of Purchase Order send an email if quantity < 10
{"object":"purchase.order","trigger":"On Write","conditions":[{"field":"order_line.product_qty","operator":"<","value":10}],"actions":[{"type":"Mail","label":"Low Quantity Alert","subject":"Purchase Order: Low Quantity Alert","body":"A purchase order has a quantity below 10. Please review and reorder stock as needed.","recipient_role":"assigned_user"}]}

Query: Send an email when an Invoice is posted and the amount is greater than 2000
{"object":"account.move","trigger":"On Write","conditions":[{"field":"state","operator":"=","value":"posted"},{"field":"amount_total","operator":">","value":2000}],"actions":[{"type":"Mail","label":"High Value Invoice Alert","subject":"Invoice Posted: Amount Exceeds 2000","body":"An invoice has been posted with an amount greater than 2000. Please review and take the necessary action.","recipient_role":"assigned_user"}]}

Query: On creation of a Contact set the tag as New Customer if the country is India
{"object":"res.partner","trigger":"On Create","conditions":[{"field":"country_id.name","operator":"=","value":"India"}],"actions":[{"type":"Write","label":"Set New Customer Tag","field":"category_id","value":"New Customer"}]}

Query: Schedule a follow-up activity when an invoice is created with amount > 1000
{"object":"account.move","trigger":"On Create","conditions":[{"field":"amount_total","operator":">","value":1000}],"actions":[{"type":"Activity","label":"High-Value Invoice Follow-up","activity_type_name":"To-Do","summary":"Follow up on high-value invoice exceeding 1000","assignee_role":"current_user","deadline":""}]}

Query: When creating a sale order please create an email activity for the customer
{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[{"type":"Activity","label":"Customer Email Activity","activity_type_name":"Email","summary":"Send an email to the customer regarding the new sale order","assignee_role":"assigned_user","deadline":""}]}

Query: When creating a sale order schedule a phone call activity
{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[{"type":"Activity","label":"Customer Phone Call","activity_type_name":"Phone Call","summary":"Call the customer to confirm the new sale order","assignee_role":"assigned_user","deadline":""}]}

Query: Send an SMS when a sale order is created
{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[{"type":"SMS","label":"New Order SMS","message":"A new sale order has been created. Please review it in Cyllo.","recipient_role":"customer"}]}

Query: When a lead is created with expected revenue > 5000 send an email and schedule a follow-up
{"object":"crm.lead","trigger":"On Create","conditions":[{"field":"expected_revenue","operator":">","value":5000}],"actions":[{"type":"Mail","label":"High Revenue Lead Email","subject":"New High-Value Lead Created","body":"A new lead with expected revenue over 5000 has been created. Please assign a sales rep and follow up promptly.","recipient_role":"assigned_user"},{"type":"Activity","label":"Lead Follow-up Activity","activity_type_name":"To-Do","summary":"Follow up on high-value lead with expected revenue greater than 5000","assignee_role":"assigned_user","deadline":""}]}

Query: On write of a product set the priority to high
{"object":"product.template","trigger":"On Write","conditions":[],"actions":[{"type":"Write","label":"Set Priority High","field":"priority","value":"1"}]}

Query: Send a warning when a leave request is confirmed and days > 5
{"object":"hr.leave","trigger":"On Write","conditions":[{"field":"state","operator":"=","value":"confirm"},{"field":"number_of_days","operator":">","value":5}],"actions":[{"type":"Warning","label":"Long Leave Warning","warning_type":"error","warning":"UserError","message":"This leave request exceeds 5 days. Manager approval is required."}]}

Query: Create a success sticky notification when a sale order is created
{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[{"type":"Warning","label":"Sale Order Created","warning_type":"notification","notification_type":"success","notification_title":"Sale Order Created","message":"A new sale order has been successfully created.","sticky":true}]}

Query: Show a success notification when an invoice is posted
{"object":"account.move","trigger":"On Write","conditions":[{"field":"state","operator":"=","value":"posted"}],"actions":[{"type":"Warning","label":"Invoice Posted","warning_type":"notification","notification_type":"success","notification_title":"Invoice Posted","message":"The invoice has been posted successfully.","sticky":false}]}

Query: Show an info notification when a new contact is created
{"object":"res.partner","trigger":"On Create","conditions":[],"actions":[{"type":"Warning","label":"New Contact","warning_type":"notification","notification_type":"info","notification_title":"New Contact Added","message":"A new contact has been added to the system.","sticky":false}]}

Query: When a task priority is set to high send an email to the assigned user
{"object":"project.task","trigger":"On Write","conditions":[{"field":"priority","operator":"=","value":"1"}],"actions":[{"type":"Mail","label":"High Priority Task Alert","subject":"Task Marked as High Priority","body":"A project task has been marked as high priority. Please review and take immediate action.","recipient_role":"assigned_user"}]}

Query: On updating a Product show a warning if the price is less than 10
{"object":"product.template","trigger":"On Write","conditions":[{"field":"list_price","operator":"<","value":10}],"actions":[{"type":"Warning","label":"Low Price Warning","warning_type":"error","warning":"ValidationError","message":"Product price is below 10. Please verify before saving."}]}

Now generate workflow JSON for this user query:
{user_query}"""


def _clean_json_text(text):
    """Strip markdown fences / BOM / extra surrounding text from AI output."""
    text = (text or '').strip().lstrip('\ufeff')
    text = re.sub(r'^```[a-zA-Z]*\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    brace_start = text.find('{')
    brace_end   = text.rfind('}')
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]
    return text.strip()


class ChatBot(models.Model):
    _name        = 'chat.bot'
    _description = 'AI Chat Bot'

    name = fields.Char()

    def _get_api_key(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('cyllo_agent.api_key')
        )

    def _get_model_name(self):
        param      = self.env['ir.config_parameter'].sudo()
        model_name = None
        try:
            model_id = param.get_param('agent.llm_model_id')
            if model_id:
                llm_record = self.env['cyllo.llm'].sudo().browse(int(model_id))
                if llm_record.exists():
                    model_name = llm_record.name
        except Exception as exc:
            _logger.warning("Workflow AI: could not read cyllo.llm model — %s", exc)
        return model_name or 'gemini-2.0-flash'

    @api.model
    def my_python_method(self, user_query):
        if not user_query or not str(user_query).strip():
            return {"error": "Empty query provided. Please describe the workflow you want to create."}

        user_query = str(user_query).strip()
        _logger.info("Workflow AI: received query — %s", user_query)

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage
        except ImportError:
            _logger.error("Workflow AI: langchain_google_genai is not installed on the server.")
            return {
                "error": (
                    "Required Python library 'langchain-google-genai' is not installed. "
                    "Please ask your system administrator to run: "
                    "pip install langchain-google-genai"
                ),
            }

        api_key = self._get_api_key()
        if not api_key:
            _logger.error("Workflow AI: API key 'cyllo_agent.api_key' is not configured.")
            return {
                "error": (
                    "Gemini API key is not configured. "
                    "Please set it in Cyllo AI Settings → API Key."
                ),
            }

        model_name = self._get_model_name()
        _logger.info("Workflow AI: using model '%s'", model_name)

        prompt_text = _SYSTEM_PROMPT.replace('{user_query}', user_query)

        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
            )
            message  = HumanMessage(content=[{"type": "text", "text": prompt_text}])
            response = llm.invoke([message])
            raw_text = response.content
        except Exception as exc:
            error_str = str(exc)
            _logger.error("Workflow AI: Gemini call failed — %s", error_str)
            return {"error": "The AI service returned an error. Please try again.", "details": error_str}

        text = _clean_json_text(raw_text)

        if not text:
            _logger.warning("Workflow AI: empty response from model '%s'", model_name)
            return {"error": "The AI returned an empty response. Please rephrase your query and try again."}

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            _logger.warning(
                "Workflow AI: JSON decode error — %s | raw (first 500 chars): %.500s", exc, text,
            )
            return {
                "error":   "The AI response could not be parsed as JSON. Please rephrase your query.",
                "details": str(exc),
            }

        if not isinstance(data, dict):
            return {"error": "The AI returned an unexpected data type. Please try again."}

        missing = _REQUIRED_KEYS - set(data.keys())
        if missing:
            _logger.warning("Workflow AI: response missing keys %s | raw: %.500s", missing, text)
            return {
                "error": (
                    f"AI response is missing required fields: "
                    f"{', '.join(sorted(missing))}. "
                    f"Please rephrase your query."
                ),
            }

        if data.get('trigger') not in _VALID_TRIGGERS:
            return {
                "error": (
                    f"AI returned an invalid trigger: \"{data.get('trigger')}\". "
                    f"Expected one of: On Create, On Write, On Unlink."
                ),
            }

        if not isinstance(data.get('actions'), list) or not data['actions']:
            return {
                "error": (
                    "AI returned no actions. Please describe what should happen "
                    "(e.g. send an email, show a warning)."
                ),
            }

        for action in data['actions']:
            action_type = action.get('type', '')
            if action_type not in _VALID_ACTION_TYPES:
                return {
                    "error": (
                        f"AI returned an unsupported action type: \"{action_type}\". "
                        f"Supported types: {', '.join(sorted(_VALID_ACTION_TYPES))}."
                    ),
                }

        if not isinstance(data.get('conditions'), list):
            data['conditions'] = []

        _logger.info(
            "Workflow AI: success — model=%s object=%s trigger=%s actions=%d conditions=%d",
            model_name, data.get('object'), data.get('trigger'),
            len(data.get('actions', [])), len(data.get('conditions', [])),
        )
        return data