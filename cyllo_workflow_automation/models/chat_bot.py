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
_SYSTEM_PROMPT = """You are an Cyllo 17 workflow automation expert.
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
  "field":    "<technical_field_name>",
  "operator": "=" | "!=" | ">" | "<" | ">=" | "<=",
  "value":    <string | number | boolean>
}

Common field names per model:
  account.move   : state (draft|posted|cancel), amount_total, payment_state, move_type
  sale.order     : state (draft|sent|sale|done|cancel), amount_total
  purchase.order : state (draft|sent|purchase|done|cancel), amount_total, product_qty
  crm.lead       : expected_revenue, stage_id, probability
  hr.leave       : state (draft|confirm|validate1|validate|refuse), number_of_days
  project.task   : stage_id, priority (0|1)
  hr.employee    : active, department_id

Value rules:
  - Selection fields: use technical key e.g. "posted" not "Posted"
  - Numbers must be numeric type: 2000 not "2000"
  - Use "=" not "==" as the equality operator

FIELD: "actions"  - array with at least one item
Use EXACTLY these "type" values. Include ALL listed keys for the chosen type.

TYPE "Warning":
{
  "type":    "Warning",
  "label":   "<short canvas title>",
  "message": "<error message shown to the user>"
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
  "type":           "Activity",
  "label":          "<short canvas title>",
  "summary":        "<activity description>",
  "assignee_role":  "current_user" | "assigned_user",
  "deadline":       "<YYYY-MM-DD if explicitly given, otherwise empty string>"
}

TYPE "Write":
{
  "type":  "Write",
  "label": "<short canvas title>",
  "field": "<technical field name to update>",
  "value": <new value — correct type: string, number, or boolean>
}

EXAMPLES:

Query: Raise an error on Sale Order if discount > 50
{"object":"sale.order","trigger":"On Create","conditions":[{"field":"discount","operator":">","value":50}],"actions":[{"type":"Warning","label":"High Discount Warning","message":"Discount exceeds 50%. Please review before confirming."}]}

Query: On write of Purchase Order send an email if quantity < 10
{"object":"purchase.order","trigger":"On Write","conditions":[{"field":"product_qty","operator":"<","value":10}],"actions":[{"type":"Mail","label":"Low Quantity Alert","subject":"Purchase Order: Low Quantity Alert","body":"A purchase order has a quantity below 10. Please review and reorder stock as needed.","recipient_role":"assigned_user"}]}

Query: Send an email when an Invoice is posted and the amount is greater than 2000
{"object":"account.move","trigger":"On Write","conditions":[{"field":"state","operator":"=","value":"posted"},{"field":"amount_total","operator":">","value":2000}],"actions":[{"type":"Mail","label":"High Value Invoice Alert","subject":"Invoice Posted: Amount Exceeds 2000","body":"An invoice has been posted with an amount greater than 2000. Please review and take the necessary action.","recipient_role":"assigned_user"}]}

Query: Schedule a follow-up activity when an invoice is created with amount > 1000
{"object":"account.move","trigger":"On Create","conditions":[{"field":"amount_total","operator":">","value":1000}],"actions":[{"type":"Activity","label":"High-Value Invoice Follow-up","summary":"Follow up on high-value invoice exceeding 1000","assignee_role":"current_user","deadline":""}]}

Query: Send an SMS when a sale order is created
{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[{"type":"SMS","label":"New Order SMS","message":"A new sale order has been created. Please review it in Cyllo.","recipient_role":"customer"}]}

Query: When a lead is created with expected revenue > 5000 send an email and schedule a follow-up
{"object":"crm.lead","trigger":"On Create","conditions":[{"field":"expected_revenue","operator":">","value":5000}],"actions":[{"type":"Mail","label":"High Revenue Lead Email","subject":"New High-Value Lead Created","body":"A new lead with expected revenue over 5000 has been created. Please assign a sales rep and follow up promptly.","recipient_role":"assigned_user"},{"type":"Activity","label":"Lead Follow-up Activity","summary":"Follow up on high-value lead with expected revenue greater than 5000","assignee_role":"assigned_user","deadline":""}]}

Query: On write of a product set the priority to high
{"object":"product.template","trigger":"On Write","conditions":[],"actions":[{"type":"Write","label":"Set Priority High","field":"priority","value":"1"}]}

Query: Send a warning when a leave request is confirmed and days > 5
{"object":"hr.leave","trigger":"On Write","conditions":[{"field":"state","operator":"=","value":"confirm"},{"field":"number_of_days","operator":">","value":5}],"actions":[{"type":"Warning","label":"Long Leave Warning","message":"This leave request exceeds 5 days. Manager approval is required."}]}

Query: When a task priority is set to high send an email to the assigned user
{"object":"project.task","trigger":"On Write","conditions":[{"field":"priority","operator":"=","value":"1"}],"actions":[{"type":"Mail","label":"High Priority Task Alert","subject":"Task Marked as High Priority","body":"A project task has been marked as high priority. Please review and take immediate action.","recipient_role":"assigned_user"}]}

Query: On updating a Product show a warning if the price is less than 10
{"object":"product.template","trigger":"On Write","conditions":[{"field":"list_price","operator":"<","value":10}],"actions":[{"type":"Warning","label":"Low Price Warning","message":"Product price is below 10. Please verify before saving."}]}

Now generate workflow JSON for this user query:
{user_query}"""


def _clean_json_text(text):
    """Strip markdown fences / BOM / extra surrounding text from AI output."""
    text = (text or '').strip().lstrip('\ufeff')
    # Remove markdown code fences if present
    text = re.sub(r'^```[a-zA-Z]*\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    # Extract the outermost JSON object if extra text leaked before or after
    brace_start = text.find('{')
    brace_end   = text.rfind('}')
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]
    return text.strip()


class ChatBot(models.Model):
    _name        = 'chat.bot'
    _description = 'AI Chat Bot'

    name = fields.Char()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_api_key(self):
        """
        Read the Gemini API key from Cyllo AI settings.
        Uses the SAME ir.config_parameter key as cyllo_crm:
            'cyllo_agent.api_key'
        """
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('cyllo_agent.api_key')
        )

    def _get_model_name(self):
        """
        Read the configured LLM model name from Cyllo AI settings.
        Uses the SAME cyllo.llm lookup as cyllo_crm:
            ir.config_parameter 'agent.llm_model_id'  ->  cyllo.llm.name
        Falls back to 'gemini-2.0-flash' when nothing is configured.
        """
        param      = self.env['ir.config_parameter'].sudo()
        model_name = None
        try:
            model_id = param.get_param('agent.llm_model_id')
            if model_id:
                llm_record = self.env['cyllo.llm'].sudo().browse(int(model_id))
                if llm_record.exists():
                    model_name = llm_record.name
        except Exception as exc:
            _logger.warning(
                "Workflow AI: could not read cyllo.llm model — %s", exc
            )
        return model_name or 'gemini-2.0-flash'

    # ── Public RPC method called by the JS chatbot ────────────────────────────

    @api.model
    def my_python_method(self, user_query):
        """
        Convert a natural-language workflow description into a structured JSON
        object using the same Google Gemini integration as cyllo_crm:

          Library  -> langchain_google_genai.ChatGoogleGenerativeAI
          API key  -> ir.config_parameter  'cyllo_agent.api_key'
          Model    -> cyllo.llm            via 'agent.llm_model_id'
        """
        # ── Guard: empty query ────────────────────────────────────────────────
        if not user_query or not str(user_query).strip():
            return {
                "error": "Empty query provided. Please describe the workflow you want to create."
            }

        user_query = str(user_query).strip()
        _logger.info("Workflow AI: received query — %s", user_query)

        # ── Step 1: Import langchain (same as cyllo_crm) ──────────────────────
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage
        except ImportError:
            _logger.error(
                "Workflow AI: langchain_google_genai is not installed on the server."
            )
            return {
                "error": (
                    "Required Python library 'langchain-google-genai' is not installed. "
                    "Please ask your system administrator to run: "
                    "pip install langchain-google-genai"
                ),
            }

        # ── Step 2: Read API key (same parameter as cyllo_crm) ───────────────
        api_key = self._get_api_key()
        if not api_key:
            _logger.error(
                "Workflow AI: API key 'cyllo_agent.api_key' is not configured."
            )
            return {
                "error": (
                    "Gemini API key is not configured. "
                    "Please set it in Cyllo AI Settings → API Key."
                ),
            }

        # ── Step 3: Read model name (same cyllo.llm lookup as cyllo_crm) ─────
        model_name = self._get_model_name()
        _logger.info("Workflow AI: using model '%s'", model_name)

        # ── Step 4: Build prompt ──────────────────────────────────────────────
        prompt_text = _SYSTEM_PROMPT.replace('{user_query}', user_query)

        # ── Step 5: Call Gemini (same pattern as cyllo_crm) ──────────────────
        #   cyllo_crm does:
        #       llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=API_KEY)
        #       message = HumanMessage(content=[{"type": "text", "text": ...}])
        #       response = llm.invoke([message])
        #       data = response.content
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
            )
            message  = HumanMessage(
                content=[{"type": "text", "text": prompt_text}]
            )
            response = llm.invoke([message])
            raw_text = response.content

        except Exception as exc:
            error_str = str(exc)
            _logger.error("Workflow AI: Gemini call failed — %s", error_str)
            return {
                "error":   "The AI service returned an error. Please try again.",
                "details": error_str,
            }

        # ── Step 6: Clean and parse JSON ──────────────────────────────────────
        text = _clean_json_text(raw_text)

        if not text:
            _logger.warning(
                "Workflow AI: empty response from model '%s'", model_name
            )
            return {
                "error": (
                    "The AI returned an empty response. "
                    "Please rephrase your query and try again."
                ),
            }

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            _logger.warning(
                "Workflow AI: JSON decode error — %s | raw (first 500 chars): %.500s",
                exc, text,
            )
            return {
                "error":   "The AI response could not be parsed as JSON. Please rephrase your query.",
                "details": str(exc),
            }

        if not isinstance(data, dict):
            return {"error": "The AI returned an unexpected data type. Please try again."}

        # ── Step 7: Validate required keys ────────────────────────────────────
        missing = _REQUIRED_KEYS - set(data.keys())
        if missing:
            _logger.warning(
                "Workflow AI: response missing keys %s | raw: %.500s",
                missing, text,
            )
            return {
                "error": (
                    f"AI response is missing required fields: "
                    f"{', '.join(sorted(missing))}. "
                    f"Please rephrase your query."
                ),
            }

        # ── Step 8: Validate trigger ──────────────────────────────────────────
        if data.get('trigger') not in _VALID_TRIGGERS:
            return {
                "error": (
                    f"AI returned an invalid trigger: \"{data.get('trigger')}\". "
                    f"Expected one of: On Create, On Write, On Unlink."
                ),
            }

        # ── Step 9: Validate actions ──────────────────────────────────────────
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

        # ── Step 10: Normalise conditions (must always be a list) ─────────────
        if not isinstance(data.get('conditions'), list):
            data['conditions'] = []

        _logger.info(
            "Workflow AI: success — model=%s object=%s trigger=%s actions=%d",
            model_name,
            data.get('object'),
            data.get('trigger'),
            len(data.get('actions', [])),
        )
        return data