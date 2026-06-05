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

# Validation constants
_REQUIRED_KEYS      = {'object', 'trigger', 'conditions', 'actions'}
_VALID_TRIGGERS     = {'On Create', 'On Write', 'On Unlink'}
_VALID_ACTION_TYPES = {'Warning', 'Mail', 'SMS', 'Activity', 'Write', 'Reuse Automation'}


_SYSTEM_PROMPT = """You are a Cyllo 17 workflow automation expert. Convert the user query into a single raw JSON object.

RULES:
1. Return RAW JSON only — no markdown, no explanation, no preamble.
2. Exactly four top-level keys: "object", "trigger", "conditions", "actions".
3. Strings: double quotes. Numbers: unquoted. Booleans: true/false.
4. When unsure, pick the most reasonable default.

"object" — Cyllo technical model name:
  Sales Order→sale.order | Purchase Order→purchase.order | Invoice/Bill→account.move
  Contact/Partner→res.partner | Product→product.template | Product Variant→product.product
  Employee→hr.employee | CRM Lead→crm.lead | Project Task→project.task
  Stock Picking→stock.picking | Manufacturing Order→mrp.production | Expense→hr.expense
  Leave/Time Off→hr.leave | Payslip→hr.payslip | Helpdesk Ticket→helpdesk.ticket

"trigger" — exactly one of: "On Create" | "On Write" | "On Unlink"
  posted/confirmed/validated/approved/done→On Write
  created/new/added/submitted→On Create
  deleted/removed/archived→On Unlink
  ambiguous→On Write

"conditions" — array ([] if none). Each item:
  {"field":"<field_or_dotted.path>","operator":"="|"!="|">"|"<"|">="|"<=","value":<str|num|bool>}
  Direct fields (main record): use field name directly, e.g. "amount_total"
  Relational fields (sub-records): use dotted path, e.g. "order_line.product_uom_qty"

  Key fields:
    sale.order: state(draft|sent|sale|done|cancel), amount_total, partner_id
      lines: order_line.product_uom_qty, .price_unit, .discount, .product_id
    purchase.order: state(draft|sent|purchase|done|cancel), amount_total
      lines: order_line.product_qty, .price_unit, .product_id
    account.move: state(draft|posted|cancel), amount_total, payment_state, move_type
      lines: invoice_line_ids.quantity, .price_unit, .product_id
    crm.lead: expected_revenue, stage_id, probability
    hr.leave: state(draft|confirm|validate1|validate|refuse), number_of_days
    project.task: stage_id, priority(0|1)
    hr.employee: active, department_id
    res.partner: country_id, category_id, customer_rank, supplier_rank, is_company
      dotted: country_id.name, category_id.name

  Value rules: selection fields use technical keys ("posted" not "Posted"), numbers unquoted, operator "=" not "=="

"actions" — array, at least one item. Use these exact types:

Warning (warning_type="error"):
  {"type":"Warning","label":"...","warning_type":"error","warning":"UserError"|"ValidationError"|"AccessError","message":"..."}
Warning (warning_type="notification"):
  {"type":"Warning","label":"...","warning_type":"notification","notification_type":"success"|"info"|"warning"|"danger","notification_title":"...","message":"...","sticky":true|false}
Mail:
  {"type":"Mail","label":"...","subject":"...","body":"...","recipient_role":"current_user"|"assigned_user"|"customer"|"partner"|"employee"}
SMS:
  {"type":"SMS","label":"...","message":"<max 160 chars>","recipient_role":"current_user"|"assigned_user"|"customer"|"partner"|"employee"}
Activity:
  {"type":"Activity","label":"...","activity_type_name":"Email"|"Call"|"Meeting"|"To-Do"|"Upload Document","summary":"...","assignee_role":"current_user"|"assigned_user","deadline":"YYYY-MM-DD or empty"}
  (email/e-mail→Email | call/phone→Call | meeting→Meeting | todo/follow-up/unspecified→To-Do | document/file→Upload Document)
Write:
  {"type":"Write","label":"...","field":"<technical field>","value":<str|num|bool>}
Reuse Automation (only when user explicitly names an existing workflow to call):
  {"type":"Reuse Automation","label":"...","reuse_automation_name":"<exact name from user>"}

EXAMPLES:
Query: Raise an error on Sale Order if discount > 50
{"object":"sale.order","trigger":"On Create","conditions":[{"field":"order_line.discount","operator":">","value":50}],"actions":[{"type":"Warning","label":"High Discount Warning","warning_type":"error","warning":"UserError","message":"Discount exceeds 50%. Please review before confirming."}]}

Query: Send an email when an Invoice is posted and amount > 2000
{"object":"account.move","trigger":"On Write","conditions":[{"field":"state","operator":"=","value":"posted"},{"field":"amount_total","operator":">","value":2000}],"actions":[{"type":"Mail","label":"High Value Invoice Alert","subject":"Invoice Posted: Amount Exceeds 2000","body":"An invoice has been posted with an amount greater than 2000. Please review.","recipient_role":"assigned_user"}]}

Query: Show a success notification when an invoice is posted
{"object":"account.move","trigger":"On Write","conditions":[{"field":"state","operator":"=","value":"posted"}],"actions":[{"type":"Warning","label":"Invoice Posted","warning_type":"notification","notification_type":"success","notification_title":"Invoice Posted","message":"The invoice has been posted successfully.","sticky":false}]}

Query: When a lead is created with expected revenue > 5000 send an email and schedule a follow-up
{"object":"crm.lead","trigger":"On Create","conditions":[{"field":"expected_revenue","operator":">","value":5000}],"actions":[{"type":"Mail","label":"High Revenue Lead Email","subject":"New High-Value Lead Created","body":"A new lead with expected revenue over 5000 has been created.","recipient_role":"assigned_user"},{"type":"Activity","label":"Lead Follow-up Activity","activity_type_name":"To-Do","summary":"Follow up on high-value lead","assignee_role":"assigned_user","deadline":""}]}

Query: When a sale order is created run the "Customer Onboarding" reusable workflow
{"object":"sale.order","trigger":"On Create","conditions":[],"actions":[{"type":"Reuse Automation","label":"Run Customer Onboarding","reuse_automation_name":"Customer Onboarding"}]}

Now generate workflow JSON for this user query:
{user_query}"""


def _build_workflow_context_prompt(workflow_context):
    if not isinstance(workflow_context, dict):
        return ""
    if workflow_context.get('mode') != 'update':
        return ""

    object_name = workflow_context.get('object') or ''
    trigger = workflow_context.get('trigger') or ''
    existing_actions = workflow_context.get('existing_actions') or []
    actions_text = ', '.join(existing_actions) if existing_actions else 'none'

    return f"""

CURRENT WORKFLOW CONTEXT:
- The user is editing an EXISTING workflow, not creating a new one.
- Keep the same object exactly: "{object_name}"
- Keep the same trigger exactly: "{trigger}"
- Existing actions already on the workflow: {actions_text}
- Return only the NEW action(s) needed for the user's latest request.
- Do NOT repeat existing actions unless the user explicitly asks to duplicate them.
- Keep "conditions" as [] unless the user explicitly asks for a new condition.
- You may omit "object" and "trigger" in your reasoning, but the final JSON must still be valid for an update.
"""


def _build_reusable_create_context_prompt(workflow_context):
    if not isinstance(workflow_context, dict):
        return ""
    if workflow_context.get('mode') != 'reusable_create':
        return ""

    return """

CURRENT WORKFLOW CONTEXT:
- The user is creating a GENERIC REUSABLE workflow.
- Do NOT depend on a specific object model.
- This workflow should start directly from the trigger.
- Return actions that can run in a reusable workflow.
- Set "conditions" to [] unless the user explicitly asks for them.
- Use an empty string for "object".
"""


def _normalize_update_payload(data, workflow_context):
    if not isinstance(data, dict) or not isinstance(workflow_context, dict):
        return data
    if workflow_context.get('mode') != 'update':
        return data

    normalized = dict(data)
    normalized.setdefault('object', workflow_context.get('object') or '')
    normalized.setdefault('trigger', workflow_context.get('trigger') or '')
    normalized.setdefault('conditions', [])
    return normalized


def _normalize_reusable_create_payload(data, workflow_context):
    if not isinstance(data, dict) or not isinstance(workflow_context, dict):
        return data
    if workflow_context.get('mode') != 'reusable_create':
        return data

    normalized = dict(data)
    normalized.setdefault('object', '')
    normalized.setdefault('conditions', [])
    return normalized

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
        return model_name or 'gemini-2.5-flash'

    @api.model
    def my_python_method(self, user_query, workflow_context=None):
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
        prompt_text += _build_workflow_context_prompt(workflow_context)
        prompt_text += _build_reusable_create_context_prompt(workflow_context)

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

        data = _normalize_update_payload(data, workflow_context)
        data = _normalize_reusable_create_payload(data, workflow_context)

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
            # Reuse Automation requires a name to search for
            if action_type == 'Reuse Automation' and not action.get('reuse_automation_name', '').strip():
                return {
                    "error": (
                        "A 'Reuse Automation' action is missing 'reuse_automation_name'. "
                        "Please specify the name of the existing reusable workflow."
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
