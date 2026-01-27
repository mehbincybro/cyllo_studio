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
import ast
import json
import re
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

import psycopg2
from langchain.agents import create_agent
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, add_messages
from langgraph.types import interrupt
from odoo import models
from odoo.exceptions import UserError
from odoo.fields import Date, _logger
from odoo.tools import SQL, Query
from typing_extensions import TypedDict


class BasicChatState(TypedDict):
    """Conversation state for managing user queries and chat history in Cyllo chatbot."""
    user_query: Optional[str]
    messages: Annotated[list, add_messages]
    company_id: Optional[list]


class CylloQuery(Query):
    group_by = None

    def select(self, *args: str | SQL) -> SQL:
        """ Return the SELECT query as an ``SQL`` object. """
        sql_args = map(SQL, args) if args else [SQL.identifier(self.table, 'id')]
        return SQL(
            "%s%s%s%s%s%s%s",
            SQL("SELECT %s", SQL(", ").join(sql_args)),
            SQL(" FROM %s", self.from_clause),
            SQL(" WHERE %s", self.where_clause) if self._where_clauses else SQL(),
            SQL(f" GROUP BY {self.group_by}") if self.group_by else SQL(),
            SQL(" ORDER BY %s", self._order) if self._order else SQL(),
            SQL(" LIMIT %s", self.limit) if self.limit else SQL(),
            SQL(" OFFSET %s", self.offset) if self.offset else SQL(),
        )




class ChatbotAgent(models.AbstractModel):
    """Abstract model for managing a LangGraph-based chatbot agent in Cyllo."""
    _name = "chatbot.agent"
    _description = "LangGraph Chatbot Agent"
    _memory_cache = {}

    def _get_memory(self, thread_id):
        """Retrieve or initialize memory for the given thread ID."""
        if thread_id not in self._memory_cache:
            self._memory_cache[thread_id] = MemorySaver()
        return self._memory_cache[thread_id]

    def _get_llm(self):
        """Fetch the configured LLM instance (ChatGoogleGenerativeAI, ChatOpenAI or Openrouter) based on system parameters."""
        param = self.env['ir.config_parameter'].sudo()
        agent_llm = param.get_param('cyllo_agent.llm')
        api_key = param.get_param('cyllo_agent.api_key')
        model_id = param.get_param('agent.llm_model_id')
        model_name = self.env['cyllo.llm'].browse(int(model_id)).name
        if agent_llm == "ChatGoogleGenerativeAI":
            return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, max_retries=3)
        elif agent_llm == 'ChatOpenAI':
            return ChatOpenAI(model=model_name, api_key=api_key, max_retries=3)
        elif agent_llm == 'OpenRouter':
            # Get the OpenRouter model from config parameter
            model_name = self.env['ir.config_parameter'].sudo().get_param('openrouter.model')
            if not model_name:
                raise UserError("OpenRouter model is not configured. Please select a model in Settings.")

            return ChatOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                model=model_name,
                max_retries=3,
                default_headers={
                    "HTTP-Referer": "https://your-domain.com",  # Optional: Replace with your domain
                    "X-Title": "Cyllo Agent"  # Optional: Your app name
                }
            )

    def _get_model_from_table(self, tables):
        """
        Retrieve the model names associated with the given table names.
        If a table is already a model name (e.g., 'account.move'), it is returned as-is.

        :param tables: A list or set of table names or model names (str)
        :return: A list of model names (str)
        """
        if not tables:
            return []

        # If a single string is passed, wrap it into a list
        if isinstance(tables, str):
            tables = [tables]

        models_list = []

        # open a completely fresh cursor for this lookup
        with self.env.registry.cursor() as new_cr:
            new_env = self.env(cr=new_cr)  # new environment bound to new cursor

            for table in tables:
                # First, try to find it as a table_name in ir.model
                model_rec = new_env['ir.model'].sudo().search([('table_name', '=', table)], limit=1)
                if model_rec:
                    models_list.append(model_rec.model)
                else:
                    # Assume it's already a model name and add it
                    models_list.append(table)
        return models_list

    def _get_table_from_model(self, inputs):
        """
        Retrieve the table names associated with the given model names.
        If a name is already a table name (i.e., not found as a model), it is returned as-is.

        :param inputs: A list or set of model names or table names (str)
        :return: A list of table names (str)
        """
        if not inputs:
            return []

        # If a single string is passed, wrap it into a list
        if isinstance(inputs, str):
            inputs = [inputs]

        table_list = []

        # use a completely fresh cursor & environment
        with self.env.registry.cursor() as new_cr:
            new_env = self.env(cr=new_cr)

            for name in inputs:
                # Try to find it as a model name
                model_rec = new_env['ir.model'].sudo().search([('model', '=', name)], limit=1)

                if model_rec and model_rec.table_name:
                    table_list.append(model_rec.table_name)
                else:
                    # If no model found, assume it's already a table name
                    table_list.append(name)

        return table_list

    def _get_model_name(self):
        """Select appropriate model names where _auto = True."""
        model_objs = self.env['ir.model'].sudo().search([])
        # Use list comprehension
        model_names = [
            model.model
            for model in model_objs
            if (model_class := self.env.registry.get(model.model)) and getattr(model_class, '_auto', True)
        ]
        return model_names

    def _is_risky_query(self, query: str) -> bool:
        """
        Returns True if the ORM query contains create/write/unlink calls.
        Uses AST parsing to avoid false positives.
        """
        risky_ops = {"create", "write", "unlink"}
        try:
            tree = ast.parse(query)  # parse into AST
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in risky_ops:  # method name
                        return True
        except Exception as e:
            _logger.debug('AST parsing failed for risky query detection, using string fallback: %s', str(e),
                          exc_info=True)
            # fallback to string detection if parsing fails
            return any(op in query for op in risky_ops)
        return False

    def _get_fields_for_models(self, models, crud=False):
        """
        Retrieve field names for a list of Cyllo model names.

        :param models: List or set of model names (e.g., ['account.move', 'res.partner'])
        :param crud: Boolean (default False). If True, include One2many and Many2many fields.
        :return: Dict mapping model name -> list of field names (with relation info for O2M/M2M)
        """
        if not models:
            return {}

        fields_by_model = {}

        # Search condition
        domain = [('model', 'in', list(models)), ('store', '=', True)]
        if not crud:
            domain.append(('ttype', 'not in', ["many2many", "one2many"]))

        fields = self.env['ir.model.fields'].sudo().search(domain)

        for field in fields:
            # For O2M and M2M, add extra info if crud=True
            if crud and field.ttype in ("many2many", "one2many"):
                field_label = f"{field.name} ({field.ttype} → {field.relation})"
            else:
                field_label = field.name

            fields_by_model.setdefault(field.model, []).append(field_label)
        return fields_by_model

    def _is_translatable_field(self, model_field: str):
        """Checks if a field is translatable using Cyllo metadata."""
        try:
            model, field = model_field.split('.')
            model_name = self._get_model_from_table(model)[0]
            return self.env[model_name]._fields[field].translate
        except Exception as e:
            _logger.debug('Failed to check if field %s is translatable: %s', model_field, str(e), exc_info=True)
        return False

    def _normalize_main_table(self, main_table_info: Any) -> Dict[str, str]:
        """
        Accepts either a string or a dict and returns:
        {"name": <table_name>, "alias": <alias>}
        Falls back across name/table/alias keys if some are missing.
        """
        if isinstance(main_table_info, str):
            return {"name": main_table_info, "alias": main_table_info}
        # if it's a dict-like
        name = (main_table_info.get("name") or main_table_info.get("table") or main_table_info.get("alias"))
        alias = (main_table_info.get("alias") or main_table_info.get("name") or main_table_info.get("table"))
        if not name or not alias:
            raise ValueError("Invalid main_table format. Expected string or dict with name/alias.")
        return {"name": name, "alias": alias}

    def _get_query_object(self, sql_query):
        """Build a `CylloQuery` SQL object from a structured SQL query dictionary returned by the LLM."""
        main_table = self._normalize_main_table(sql_query.get("main_table"))
        query = CylloQuery(
            self.env.cr,
            self._get_table_from_model(main_table["alias"])[0],
            self._get_table_from_model(main_table["name"])[0]
        )

        # Process JOINs
        for join in sql_query.get("joins", []):
            lhs_table = self._get_table_from_model(join['lhs_alias'])[0]
            lhs_column = self._get_table_from_model(join['lhs_column'])[0]
            rhs_table = self._get_table_from_model(join['rhs_alias'])[0]
            rhs_column = self._get_table_from_model(join['rhs_column'])[0]

            join_condition = SQL(f"{lhs_table}.{lhs_column} = {rhs_table}.{rhs_column}")
            query.add_join(join["type"], rhs_table, self._get_table_from_model(join['rhs_table'])[0], join_condition)

        # Process WHERE clause
        where = sql_query.get("where")
        if isinstance(where, dict):
            where_clause = (where.get("where_clause") or "").strip()
            where_params = where.get("where_params", [])
        elif isinstance(where, str):
            where_clause = where.strip()
            where_params = sql_query.get("where_params", []) if isinstance(sql_query.get("where_params"),
                                                                           list) else []
        else:
            where_clause, where_params = "", []

        # Fix EXTRACT(YEAR/MONTH/DAY FROM %s)
        extract_map = {
            "YEAR": lambda d: datetime.fromisoformat(d).year,
            "MONTH": lambda d: datetime.fromisoformat(d).month,
            "DAY": lambda d: datetime.fromisoformat(d).day,
        }

        for extract_part, extract_func in extract_map.items():
            extract_pattern = f"EXTRACT({extract_part} FROM %s)"
            if extract_pattern in where_clause:
                where_clause = where_clause.replace(extract_pattern, "%s")
                where_params = [
                    extract_func(p) if isinstance(p, str) and "-" in p else p
                    for p in where_params
                ]

        # --- Fix IN %s (convert list to tuple) ---
        if isinstance(where_params, list) and "IN %s" in where_clause:
            where_params = [
                tuple(p) if isinstance(p, list) else p
                for p in where_params
            ]

        # (Optional) Handle BETWEEN — can ensure ISO or datetime objects if needed
        if "BETWEEN %s AND %s" in where_clause:
            # Assume params are in correct order and date strings
            where_params = [
                datetime.fromisoformat(p).date() if isinstance(p, str) and "-" in p else p
                for p in where_params
            ]

        # Add WHERE clause
        if where_clause:
            # Matches: product_template.name = %s, product_template.name ILIKE %s, etc.
            pattern = re.compile(r'(\w+\.\w+)\s+(ILIKE|=|!=|LIKE|NOT ILIKE|NOT LIKE)', re.IGNORECASE)

            matches = pattern.findall(where_clause)
            for field, operator in matches:
                if "->>" not in field and self._is_translatable_field(field):
                    where_clause = where_clause.replace(field, f"{field}->>'en_US'")

            # --- Fix parameter mismatch between placeholders and params ---
            placeholder_count = where_clause.count("%s")
            if isinstance(where_params, list):
                if placeholder_count == 0:
                    # No placeholders in WHERE clause — ignore all params (likely for SELECT/subqueries)
                    where_params = []
                elif len(where_params) > placeholder_count:
                    where_params = where_params[:placeholder_count]
                elif len(where_params) < placeholder_count:
                    where_params += [None] * (placeholder_count - len(where_params))
            query.add_where(where_clause, where_params)
        # Group by
        if sql_query.get("group_by"):
            query.group_by = sql_query["group_by"]

        # Order by
        if sql_query.get("order_by"):
            query.order = sql_query["order_by"]

        # Limit
        if sql_query.get("limit"):
            query.limit = sql_query["limit"]

        return query

    def _build_orm_query_string(self, plan: Dict[str, Any]) -> Dict[str, str]:
        """
        Builds an Odoo ORM query as a string based on a structured JSON plan, without executing it.

        Args:
            plan: JSON plan with keys: action, model, data, lines, lines_field, line_model, inverse_field, filters,
                  additional_fields, validation_required

        Returns:
            Dictionary with:
            - query: String representation of the Odoo ORM query
            - error: Error message if the plan is invalid (query will be empty)
        """
        try:
            # Check for validation errors
            if plan.get("validation_required", []):
                return {
                    "query": "",
                    "error": f"Cannot generate query: {', '.join(plan['validation_required'])}"
                }

            # Extract plan components
            action = plan.get("action")
            model_name = plan.get("model")
            data = plan.get("data", [])
            lines = plan.get("lines", [])
            lines_field = plan.get("lines_field")
            line_model = plan.get("line_model")
            inverse_field = plan.get("inverse_field")
            filters = plan.get("filters", [])
            additional_fields = plan.get("additional_fields", [])

            # Validate inputs
            if not model_name:
                return {"query": "", "error": "Missing model in plan"}
            if action not in ["create", "read", "update", "delete"]:
                return {"query": "", "error": f"Unsupported action: {action}"}
            if lines and (not lines_field or not line_model or not inverse_field):
                return {"query": "",
                        "error": "Missing lines_field, line_model, or inverse_field for x2many operations"}

            # Helper function to format field values
            def format_value(field_data: Dict[str, Any]) -> str:
                value = field_data["value"]
                if field_data.get("model"):  # Relational field
                    return f"env['{field_data['model']}'].search([('name', '=', {repr(value)})], limit=1).id"
                return repr(value)  # Non-relational field (string, number, etc.)

            # Helper function to format domain filters
            def format_domain(domain: List, is_line: bool = False) -> str:
                if not domain:
                    return "[]"
                domain_parts = []
                for filter_tuple in domain:
                    if isinstance(filter_tuple, list) and len(filter_tuple) == 3:
                        field, operator, value = filter_tuple
                        if isinstance(value, dict) and value.get("model"):
                            value_str = f"env['{value['model']}'].search([('name', '=', {repr(value['value'])})], limit=1).id"
                        else:
                            value_str = repr(value)
                        domain_parts.append(f"('{field}', '{operator}', {value_str})")
                    else:
                        raise ValueError(f"Invalid filter format: {filter_tuple}")
                return f"[{', '.join(domain_parts)}]"

            # Build main domain for parent
            parent_domain_str = format_domain(filters)

            # Build data dictionary for main record
            values_parts = []
            for field_data in data + additional_fields:
                values_parts.append(f"    '{field_data['field']}': {format_value(field_data)}")

            # Build x2many commands
            if lines and lines_field:
                commands_parts = []
                for line in lines:
                    operation = line.get("operation")
                    line_id = line.get("id")
                    line_filter = line.get("line_filter", [])
                    values = line.get("values", [])

                    # Build values string for create/update/replace
                    if values and operation in ["create", "update", "replace"]:
                        line_parts = []
                        for field_data in values:
                            line_parts.append(f"    '{field_data['field']}': {format_value(field_data)}")
                        values_str = "{\n" + ",\n".join(line_parts) + "\n}" if line_parts else "{}"

                    # Resolve line ID if not provided and line_filter is given
                    if operation in ["update", "delete", "link", "unlink"] and not line_id and line_filter:
                        full_line_domain = f"[('{inverse_field}', 'in', env['{model_name}'].search({parent_domain_str}).ids)] + {format_domain(line_filter, is_line=True)}"
                        line_id = f"env['{line_model}'].search({full_line_domain}, limit=1).id"

                    if operation == "create":
                        commands_parts.append(f"(0, 0, {values_str})")
                    elif operation == "update":
                        if not line_id:
                            raise ValueError("Missing id or line_filter for update operation")
                        commands_parts.append(f"(1, {line_id}, {values_str})")
                    elif operation == "delete":
                        if not line_id:
                            raise ValueError("Missing id or line_filter for delete operation")
                        commands_parts.append(f"(2, {line_id}, 0)")
                    elif operation == "link":
                        if not line_id:
                            raise ValueError("Missing id or line_filter for link operation")
                        commands_parts.append(f"(4, {line_id}, 0)")
                    elif operation == "unlink":
                        if not line_id:
                            raise ValueError("Missing id or line_filter for unlink operation")
                        commands_parts.append(f"(3, {line_id}, 0)")
                    elif operation == "clear":
                        commands_parts.append(f"(5, 0, 0)")
                    elif operation == "replace":
                        if not values:
                            raise ValueError("Missing values for replace operation")
                        id_list = [format_value(v) for v in values]
                        commands_parts.append(f"(6, 0, [{', '.join(id_list)}])")
                    else:
                        raise ValueError(f"Unsupported x2many operation: {operation}")

                if commands_parts:
                    values_parts.append(f"    '{lines_field}': [{', '.join(commands_parts)}]")

            # Construct values string
            values_str = "{\n" + ",\n".join(values_parts) + "\n}" if values_parts else "{}"

            # Build query based on action
            if action == "create":
                query = f"env['{model_name}'].create({values_str})"
            elif action == "read":
                query = f"env['{model_name}'].search({parent_domain_str}).read()"
            elif action == "update":
                query = f"env['{model_name}'].search({parent_domain_str}).write({values_str})"
            elif action == "delete":
                query = f"env['{model_name}'].search({parent_domain_str}).unlink()"
            else:
                return {"query": "", "error": f"Unsupported action: {action}"}

            return {"query": query, "error": ""}

        except Exception as e:
            return {"query": "", "error": f"⚠️ Error in build_orm_query_string: {str(e)}"}

    def build_agent(self, thread_id):
        """
        Build a Cyllo ReAct agent with memory, tools, and security rules.

        - Initializes LLM (Google Generative AI or OpenAI) from system config
        - Provides tools for analytics (SQL), CRUD (ORM), and record links
        - Enforces access rights, data privacy, and safe query generation
        - Returns a compiled conversational agent with thread-based memory
        """
        llm = self._get_llm()
        tools = []  # Add your tools here


        @tool
        def analytic_record( runtime: ToolRuntime) -> str:
            """getting an analytic result based on the user query
            "Some fields in Cyllo are stored in related models and require joins. Important relationships include:\n"
            "- `res_users.partner_id → res_partner.id → res_partner.name` (User Name)\n"
            "- `sale_order.partner_id → res_partner.id → res_partner.name` (Customer Name)\n"
            "- `sale_order.user_id → res_users.id`\n"
            "- `res_users.id → hr_employee.user_id`\n"
            "- `product_template.id → product_product.product_tmpl_id → product_template.name`\n"
            "- `sale_order_line.order_id → sale_order.id`\n"
            "- `sale_order_line.product_id → product_product.id`\n\n"
            "**Always resolve fields via correct relationships and joins.**\n"
            "_Example_: For a query like 'filter by user name John', join `res_users` to `res_partner` on `partner_id`, and use a WHERE clause on `res_partner.name = %s`.\n\n"
            "---\n"
             "- Never display, use, or reference sensitive fields such as `login`, `password`, `api_key`, `token`, or `access_token`\n"
            "- If a field contains credentials or identifiers meant for internal use only, **exclude it** from all outputs\n"
            "- If a user asks for sensitive data, respond that it cannot be shown due to security policy\n"
            "- When referring to users, always prefer `res_partner.name` (via the `partner_id` relationship) instead of `res_users.login`\n"
            "- Do not include or infer login names unless explicitly required and authorized by tool logic\n"
            "- If unsure whether a field is sensitive, treat it as sensitive by default\n"
            "after getting query, go to 'get_url' tool to get the url for providing hyperlink"
            "entities (optional): A list of objects representing items that should be hyperlinked. Each object must include:"
            "text: The exact text in the summary that should be converted to a hyperlink"
            "record_id: The corresponding record ID"
            "model: The model name to generate the hyperlink for"
            """
            try:
                user_query = runtime.state.get("user_query")
                company_ids = runtime.state["company_id"]
                models = self._get_model_name()
                prompt_model = f"""You are an Cyllo SQL table selector. From the list of provided models, return only the list of 
                relevant table names needed to answer the given question.
                                    Respond with only the table names, nothing else.
                                    Available Models: {models}
                                    User Question: {user_query}
                              """
                response_text = llm.invoke(prompt_model)
                model_list = [line.strip() for line in response_text.content.strip().splitlines() if line.strip()]
                model_list = self._get_model_from_table(model_list)
                fields_info = self._get_fields_for_models(model_list)
                tables = self._get_table_from_model(model_list)
                prompt = f"""
                        You are generating a SQL query based on the following inputs:

                        - User Query: "{user_query}"
                        - Main Model: "{tables}"
                        - Fields to Retrieve: {fields_info}
                        - System Time: {Date.today()}

                        🧩 Rules:
                        -  All output must be in **valid JSON** format (RFC 8259 compliant).
                        -  Use **JSON lists** (square brackets [ ]) — never use Python tuples (( )).
                            - Example: ["value1", "value2"] ✅ — NOT ("value1", "value2") ❌
                        - Resolve all fields correctly using model relationships.
                        - Use JOINs only when needed to access fields in related models.
                        - JOIN aliases (rhs_alias) must match rhs_table unless otherwise required.
                        - Join types must be "JOIN" for inner joins or "LEFT JOIN" for left joins — do not use "INNER JOIN".
                        - Do not use short aliases like "pt" or "pp" unless the system expects them.
                        - Use %s for parameter placeholders (not ?).
                        - For IN clauses, always pass tuples, not lists.
                        - If GROUP BY is required, only select grouped and aggregated fields — never use SELECT *.
                        - Do not hallucinate fields or joins.
                        - Ensure all aliases used in SELECT or JOINs are declared and consistent.
                        - If monetary field is present, include the respective currency id make sure to return currency symbol

                        🧭 Select Field Guidelines:
                        - Include only the fields needed to fulfill the user query.
                        - Never default to SELECT * unless user says “all fields” or “full details.”
                        - Do not include fallback fields like create_uid, write_date, etc.
                        - Always Include id fields (e.g., sale_order.id, res_partner.id, product_template.id).
                        - When selecting product or partner names:
                            - Use product_template.name instead of product_product.name.
                            - Use res_partner.name instead of res_users.name.
                        - For on-hand quantity, always check the quantity only in internal locations (e.g., filter stock_quant by location usage = 'internal').
    
                        🔁 Output Format (as JSON):
                        - main_table: include name and alias(alias is same as name of table)
                        - select: list of strings (e.g., ["sale_order.name", "sale_order.id"])
                        - joins: list of objects, each with:
                            - type ("JOIN" or "LEFT JOIN")
                            - lhs_alias, lhs_column
                            - rhs_table, rhs_column
                            - rhs_alias
                        - where: include where_clause: str, where_params: list 
                        - group_by: str (can be null)
                        - order_by: str (can be null)
                        - limit: int (can be null)
                        - tables: list of all tables used

                        🎯 Output JSON only — no explanations or text outside the structure.
                """

                response = llm.invoke(prompt)
                sql_query = response.content if hasattr(response, "content") else str(response)
                sql_query = re.sub(r"```(?:json|python)?", "", sql_query).replace("`", "").strip()
                sql_query = json.loads(sql_query)
                query = self._get_query_object(sql_query)
                tables = sql_query.get("tables")
                model_list = self._get_model_from_table(tables)
                if model_list:
                    # Force environment to see only current company
                    env_single_company = self.env(context=dict(
                        self.env.context,
                        allowed_company_ids = company_ids
                    ))
                    for model in model_list:
                        model_obj = env_single_company[f"{model}"]
                        model_obj._apply_ir_rules(query, "read")
                        model_obj._flush_search([])
                sql, params = query.select(*[SQL(f) for f in sql_query.get("select")])
                try:

                    # Validate SQL with EXPLAIN
                    self.env.cr.execute(f"EXPLAIN {sql}", params)
                    # Execute actual query
                    self.env.cr.execute(sql, params)
                    rows = self.env.cr.fetchall()
                    # Get column names
                    column_names = [description[0] for description in self.env.cr.description]
                    # Convert rows to dict
                    result = [dict(zip(column_names, row)) for row in rows]
                    # Build entity links
                    select_fields = sql_query.get("select", [])
                    entities = []
                    # Identify id fields dynamically
                    id_fields = [f for f in select_fields if f.endswith(".id")]

                    # Build a quick lookup map between simple field names and actual column names
                    # (to handle cases where SQL might alias or omit prefixes)
                    column_map = {col.split(".")[-1]: col for col in column_names}

                    for id_field in id_fields:
                        table_name, id_col = id_field.split(".", 1)
                        model_name = self._get_model_from_table(table_name)[0]
                        # Find matching name/display_name field
                        name_field = next(
                            (f for f in select_fields if f.startswith(f"{table_name}.") and
                             (f.endswith(".name") or f.endswith(".display_name"))),
                            None
                        )

                        # Match against actual result column names
                        id_key = id_col if id_col in column_names else column_map.get(id_col)
                        name_key = None
                        if name_field:
                            name_col = name_field.split(".", 1)[1]
                            name_key = name_col if name_col in column_names else column_map.get(name_col)

                        for row in result:
                            record_id = row.get(id_key)
                            text = row.get(name_key) if name_key else None
                            if isinstance(text, dict):
                                # pick the first available translation (or en_US specifically)
                                text = text.get('en_US') or next(iter(text.values()), None)

                            if isinstance(text, str) and text.strip():
                                entities.append({
                                    "text": text,
                                    "record_id": record_id,
                                    "model": model_name
                                })

                    return json.dumps({"result": result, "entities": entities}, default=str)

                except psycopg2.Error as e:
                    self.env.cr.rollback()

                    # Build prompt for LLM to correct query
                    prompt = f"""
                    The following SQL query failed during validation or execution:

                    User Query:
                    {user_query}

                    SQL:
                    {sql}

                    Params:
                    {params}

                    Error Message:
                    {e}

                    Please generate a corrected SQL query that resolves the above error and fulfills the user intent along with corresponding params in pure JSON format only:
                    {{
                      "sql": "SELECT ... WHERE ...",
                      "params": [ ... ]
                    }}
                    """
                    # Invoke LLM for corrected query
                    query = llm.invoke(prompt).content
                    corrected = re.sub(r"```(?:json|python)?", "", query).replace("`", "").strip()
                    sql_query = json.loads(corrected)

                    # Re-extract SQL and sanitize params
                    sql = sql_query.get("sql", "").strip()
                    if not sql:
                        raise ValueError("Corrected SQL is empty!")

                    params = sql_query.get("params", [])
                    params = [
                        tuple(p) if isinstance(p, list) else p
                        for p in sql_query.get("params", [])
                    ]
                    # Retry execution
                    self.env.cr.execute(sql, params)
                    rows = self.env.cr.fetchall()
                    # Get column names
                    column_names = [description[0] for description in self.env.cr.description]

                    # Convert each row to a dictionary with column names
                    result = [dict(zip(column_names, row)) for row in rows]

                    # Extract possible hyperlink candidates (assuming select fields contain id + name)
                    select_fields = sql_query.get("select", [])
                    entities = []

                    # Map table name -> model
                    id_fields = [(f, f) for f in select_fields if f.endswith(".id")]

                    # Build a quick lookup map between simple field names and actual column names
                    # (to handle cases where SQL might alias or omit prefixes)
                    column_map = {col.split(".")[-1]: col for col in column_names}

                    for id_field in id_fields:
                        table_name, id_col = id_field.split(".", 1)
                        model_name = self._get_model_from_table(table_name)[0]
                        # Find matching name/display_name field
                        name_field = next(
                            (f for f in select_fields if f.startswith(f"{table_name}.") and
                             (f.endswith(".name") or f.endswith(".display_name"))),
                            None
                        )

                        # Match against actual result column names
                        id_key = id_col if id_col in column_names else column_map.get(id_col)
                        name_key = None
                        if name_field:
                            name_col = name_field.split(".", 1)[1]
                            name_key = name_col if name_col in column_names else column_map.get(name_col)

                        for row in result:
                            record_id = row.get(id_key)
                            text = row.get(name_key) if name_key else None
                            if isinstance(text, dict):
                                # pick the first available translation (or en_US specifically)
                                text = text.get('en_US') or next(iter(text.values()), None)

                            if isinstance(text, str) and text.strip():
                                entities.append({
                                    "text": text,
                                    "record_id": record_id,
                                    "model": model_name
                                })
                    return json.dumps({"result": result, "entities": entities}, default=str)

            except Exception as e:
                # Catch all errors and return a safe fallback message
                error_msg = f"⚠️ Error in analytic_record tool: {str(e)}"
                return error_msg

        tools.append(analytic_record)

        @tool
        def prepare_crud(user_query: str) -> dict:
            """
            Converts a user query into a structured JSON plan for the Odoo query builder.
            The plan includes all fields, filters, and one2many/many2many data so the resulting ORM query
            can be constructed and executed as a **single Odoo ORM operation** rather than multiple steps."""

            try:
                models = self._get_model_name()
                prompt_model = f"""You are a Cyllo SQL table selector. 
                From the list of provided models, return only the list of 
                relevant table names needed to answer the given question.
                Respond with only the table names, nothing else.
                Available Models: {models}
                User Question: {user_query}
                """
                response_text = llm.invoke(prompt_model)
                model_list = [line.strip() for line in response_text.content.strip().splitlines() if line.strip()]
                model_list = self._get_model_from_table(model_list)
                fields_info = self._get_fields_for_models(model_list, crud=True)


                prompt = f"""
                You are a Cyllo ORM data planner.
                Given a user question and the available models (tables and fields), return a structured JSON object
                that can be used by a query builder to construct an Odoo ORM query.

                Rules:
                - Identify the correct action: "create", "update", "delete", or "read".
                - Select the most relevant Odoo model (e.g., "sale.order", "purchase.order").
                - For create/update:
                  - Include a "data" list of dictionaries with keys "model", "field", and "value".
                  - For relational fields (e.g., "partner_id"), set "model" to the related Odoo model (e.g., "res.partner") and "value" to the name or ID.
                  - For non-relational fields (e.g., "product_qty"), set "model" to null and "value" to the raw value.
                  - Map "customer" or "supplier" to "partner_id".
                - For x2many (one2many/many2many) fields:
                  - Specify the field name in "lines_field" (e.g., "order_line" for sale.order/purchase.order, "move_ids" for stock.picking, or null if not applicable).
                  - Specify the related model in "line_model" (e.g., "sale.order.line").
                  - Specify the inverse field in "inverse_field" (e.g., "order_id" for sale.order.line).
                  - Include a "lines" list where each item is an object:
                    {{
                      "operation": "create" | "update" | "delete" | "link" | "unlink" | "clear" | "replace",
                      "id": existing record ID (or null for create/clear/replace),
                      "line_filter": array of filter tuples to find the line record (e.g., [["product_id", "=", {{"model": "product.product", "value": "Pop Up Toaster"}}]]) (optional, used for update/delete/link/unlink if id is not provided),
                      "values": [{{"model": ..., "field": ..., "value": ...}}] (used for create/update/replace)
                    }}
                - For read/update/delete:
                  - Include a "filters" array of tuples (e.g., [["name", "=", "SO001"]]).
                  - For relational fields in filters, use {{"model": ..., "value": ...}} (e.g., {{"model": "res.partner", "value": "ABC Corp"}}).
                - Only use provided fields from the input tables. Do not guess missing data.
                - If required info (e.g., customer, product) is missing, include a "validation_required" key with a list of missing details.
                - Include an "additional_fields" list of {{"model": ..., "field": ..., "value": ...}} for optional fields inferred from the query.
                - Use exact Odoo field names (e.g., "product_qty" for purchase.order, "product_uom_qty" for sale.order).

                Example Output for "create a purchase order for supplier: ABC Corp, product: Wireless Mouse, qty 10":
                {{
                  "action": "create",
                  "model": "purchase.order",
                  "data": [{{"model": "res.partner", "field": "partner_id", "value": "ABC Corp"}}],
                  "lines_field": "order_line",
                  "line_model": "purchase.order.line",
                  "inverse_field": "order_id",
                  "lines": [
                    {{
                      "operation": "create",
                      "id": null,
                      "line_filter": [],
                      "values": [
                        {{"model": "product.product", "field": "product_id", "value": "Wireless Mouse"}},
                        {{"model": null, "field": "product_qty", "value": 10}}
                      ]
                    }}
                  ],
                  "filters": [],
                  "additional_fields": [],
                  "validation_required": []
                }}

                Example Output for "to sale order S00672, remove the product Pop Up Toaster and add Armchair, qty 2":
                {{
                  "action": "update",
                  "model": "sale.order",
                  "data": [],
                  "lines_field": "order_line",
                  "line_model": "sale.order.line",
                  "inverse_field": "order_id",
                  "lines": [
                    {{
                      "operation": "delete",
                      "id": null,
                      "line_filter": [["product_id", "=", {{"model": "product.product", "value": "Pop Up Toaster"}}]],
                      "values": []
                    }},
                    {{
                      "operation": "create",
                      "id": null,
                      "line_filter": [],
                      "values": [
                        {{"model": "product.product", "field": "product_id", "value": "Armchair"}},
                        {{"model": null, "field": "product_uom_qty", "value": 2}}
                      ]
                    }}
                  ],
                  "filters": [["name", "=", "S00672"]],
                  "additional_fields": [],
                  "validation_required": []
                }}

                Example Output for missing data:
                {{
                  "action": "create",
                  "model": "sale.order",
                  "data": [],
                  "lines_field": "order_line",
                  "line_model": "sale.order.line",
                  "inverse_field": "order_id",
                  "lines": [],
                  "filters": [],
                  "additional_fields": [],
                  "validation_required": ["customer name is missing"]
                }}

                Tables and Fields: {fields_info}
                User Question: {user_query}
                """


                # Invoke LLM
                response = llm.invoke(prompt)
                raw = response.content if hasattr(response, "content") else str(response)

                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?\n?", "", raw)
                    raw = re.sub(r"\n?```$", "", raw)
                raw = raw.strip()

                # If LLM returned JSON as a quoted string, unquote
                if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                    raw = raw[1:-1]


                parsed = json.loads(raw)

                if not isinstance(parsed, dict):
                    raise Exception(f"❌ Expected a dict, got {type(parsed)}: {parsed}")

                orm_query = self._build_orm_query_string(parsed)
                if orm_query.get('error'):
                    raise ValueError(f"Failed to build ORM query: {orm_query['error']}")
                query = orm_query.get('query')

                return query

            except Exception as e:
                return {"error": f"⚠️ Error in prepare_crud tool: {str(e)}"}

        tools.append(prepare_crud)

        @tool
        def execute_crud(query: str) -> dict:
            """
            Executes a confirmed ORM query passed from the previous step.
            Always returns model + id if available.
            Only interrupts for CREATE, WRITE, UNLINK operations.
            """
            _logger.info("ORM Query Received: %s", query)

            # ✅ Interrupt only if risky
            if self._is_risky_query(query):
                _logger.info("Risky ORM Query detected: %s", query)
                result = interrupt("⚠️ This operation modifies data. Do you want to proceed?")
                if result != "proceed":
                    return {"message": "✅ Cancellation confirmed. The requested operation was stopped before execution. No changes were made."}
                _logger.info("Past risky check, about to enter try")

            _logger.info("Reached end of risky check, going to try block now")

            try:
                _logger.info("inside try: else-condition")

                # ✅ Safe locals for eval
                safe_locals = {"self": self, "env": self.env}
                record = eval(query, {}, safe_locals)

                # Case 1: recordset object
                if hasattr(record, "_name") and getattr(record, "ids", False):
                    return {
                        "message": "✅ Operation successfully completed.",
                        "model": record._name,
                        "id": record.id,
                        "name": getattr(record, "name", None)
                    }

                # Case 2: list of dicts (e.g. read())
                if isinstance(record, list) and len(record) > 0 and isinstance(record[0], dict):
                    # take the first dict's id and name
                    rec_dict = record[0]
                    return {
                        "message": "✅ Operation successfully completed.",
                        "model": safe_locals['self']._name if hasattr(safe_locals['self'], '_name') else None,
                        "id": rec_dict.get("id"),
                        "name": rec_dict.get("name")
                    }

                # If nothing matched:
                return {"message": "✅ Operation completed, but no record returned."}

            except Exception as e:
                # ✅ Rollback to avoid "transaction aborted" issue
                self.env.cr.rollback()
                _logger.error("ORM execution failed: %s", e)
                return {"message": f"❌ ORM query failed: {str(e)}"}

        tools.append(execute_crud)

        @tool
        def get_url(text: str,record_id: str, model: str) -> str:
            """generating url for providing hyperlink using the record id and its corresponding model generated from execute_crud and analytic_record tool"""
            _logger.debug("text for url: ", text)
            url = f'web?studio=#id={record_id}&cids=1&model={self._get_model_from_table(model)[0]}&view_type=form'
            return url
        tools.append(get_url)

        @tool
        def currency_conversion(amount: float, from_currency_name: str, to_currency_name: str) -> dict:
            """Convert an amount from one currency to another using the currency rates configured in Cyllo.
            For example, converting 100 USD to EUR will return the equivalent EUR amount based on the
            current exchange rate."""

            Currency = self.env['res.currency']
            # Search currencies by symbol
            from_currency = Currency.search([("name", "=", from_currency_name)], limit=1)
            to_currency = Currency.search([("name", "=", to_currency_name)], limit=1)

            # Validation if inactive
            if not from_currency.active:
                return {"error": f"Currency '{from_currency_name}' is inactive."}

            if not to_currency.active:
                return {"error": f"Currency '{to_currency_name}' is inactive."}

            # Perform conversion using Odoo’s internal method
            converted_amount = from_currency._convert(
                amount,
                to_currency,
                self.env.company,
            )
            return {
                "amount": converted_amount,
                "from": from_currency_name,
                "to": to_currency_name,
            }
        tools.append(currency_conversion)

        @tool
        def get_currency_name(id: int) -> dict:
            """Returns the currency name from the currency id"""
            currency = self.env['res.currency'].search([('id','=',id)], limit=1)
            if not currency.active:
                return {"error": f"Currency with'{id}' is inactive."}
            return {'name' : currency.name}
        tools.append(get_currency_name)

        system_prompt = (
                "You are a helpful assistant for **Cyllo**, a modern ERP system. "
                "Cyllo is a powerful, modular business management platform designed for flexibility and customization. "
                "Cyllo is built on top of a robust open-source ERP engine, but for all user-facing communication, you must "
                "refer to it only as **Cyllo**. Never mention the underlying platform or the word **Odoo** unless specifically "
                "asked to explain the history or technology stack. "
                "Your goal is to help users interact with the Cyllo ERP system by using available tools to answer questions, "
                "generate reports, or manage operations.\n\n"

                "You follow the **ReAct pattern** (Thought → Action → Observation) and use tools to query or modify ERP data.\n"
                "Time: " + str(Date.today()) + "\n"

            "## Available Actions\n"
            "You can use tools to:\n"
            "- Analyze or fetch data (e.g., sales, inventory, products)\n"
            "- Create, update, or delete records\n"
            "- Generate SQL queries or correct them\n\n"

            "**🛠 Tool Selection Rules:**\n"
            "- For **analytical queries or data insights**, you must use the **`analytic_record`** tool only.\n"
            "- For **CRUD operations** (create, read, update, delete), you must use the **`prepare_crud`** tool only.\n"
            "- Do not attempt CRUD with `analytic_record`, and do not perform analysis with `prepare_crud`.\n\n"

            "**⚡ CRUD Execution Rules:**\n"
            "- When using the `prepare_crud` tool, always produce all the data needed to build **one complete ORM query per operation** (create/update/delete/read) — do **not** break it into micro-steps.\n"
            "- The output of `prepare_crud` must be sufficient for constructing a **single Odoo ORM statement** that performs the full intended action in one go (e.g., create a record with all fields, update with all values, delete with all filters).\n"
            "- Do not divide CRUD operations into multiple partial calls. Each logical user request = exactly one CRUD plan.\n"
            "- Handle validation dynamically: if required records (e.g., customer or product) don’t exist, surface that as **one consolidated validation failure** rather than multiple interruptions.\n"
            "- After `prepare_crud` returns the plan, the system will build the ORM query and then `execute_crud` will be called to confirm and execute — there should be no intermediate CRUD steps between them.\n\n"

            "## 🔗 URL Generation Workflow Rules\n"
            "- For every CRUD operation that needs a link, the agent **must** follow this exact sequence:\n"
            "  1. **Call `prepare_crud`** to generate the ORM query for the requested action (create, read, update, delete).\n"
            "  2. **Call `execute_crud`** to run that ORM query and obtain the resulting `model` and `id`.\n"
            "  3. **Only after `execute_crud` returns a valid `model` and `id`, call `get_url`** with exactly that `model` and `id` to generate the link.\n\n"
            "- Do **not** call `get_url` before `execute_crud` or with guessed/stale IDs.\n"
            "- If `execute_crud` returns no `id` (record not found or no record created), do **not** call `get_url`. Instead, inform the user that no record was found or created.\n"
            "- When the user asks for a link to a specific record (e.g., “link of purchase order P00945”), the agent must:\n"
            "  - Use a **READ** operation via `prepare_crud` to locate the record’s `id`.\n"
            "  - Pass that `id` to `execute_crud` to retrieve the record.\n"
            "  - Then call `get_url` with the `model` and `id` returned by `execute_crud`.\n\n"
            "- Never generate or guess URLs yourself; only use the `get_url` tool with a verified `model` + `id`.\n\n"

            "## Error Handling\n"
            "- If a tool returns a failed SQL or validation error:\n"
            "  - **Reflect**, fix the issue, and retry with the corrected tool input\n"
            "---\n"

            "## Data Privacy and Security Rules\n"
            "- Never display, use, or reference sensitive fields such as `login`, `password`, `api_key`, `token`, or `access_token`\n"
            "- If a field contains credentials or identifiers meant for internal use only, **exclude it** from all outputs\n"
            "- If a user asks for sensitive data, respond that it cannot be shown due to security policy\n"
            "- When referring to users, always prefer `res_partner.name` (via the `partner_id` relationship) instead of `res_users.login`\n"
            "- Do not include or infer login names unless explicitly required and authorized by tool logic\n"
            "- If unsure whether a field is sensitive, treat it as sensitive by default\n"
            "---\n"

            "## Response Format\n"
            "- Use **Markdown** for all replies\n"
            "- Use `#`, `##` headings, **bold**, _italic_, `code`, and tables/bullets to organize data\n"
            "- Never return plain text — even short answers must follow markdown rules\n"
            "- If a record ID is present, use the corresponding model name and record ID to construct a URL pointing to the record from the 'get_url' tool. \n"
            "- The associated text (e.g., name or title) should be clickable and act as a hyperlink. Do not display the raw URL itself in the message; only the clickable text should appear.\n"
            "- The URL must be obtained strictly via the 'get_url' tool; **do not generate or hallucinate the link yourself under any circumstance.**\n"
            "- If your response involves numerical data suitable for visualization (e.g., comparisons, trends, distributions), return a `chart_config` alongside your `text` output.\n"
            "- `chart_config` must be a valid [Apache ECharts](https://echarts.apache.org/en/index.html) configuration in JSON format.\n"
            "- You must return your response as a JSON object with two fields:\n"
            "  - `text`: Markdown-formatted summary of the result.\n"
            "  - `chart_config`: (optional) A JSON-compatible object for an ECharts chart.\n"
            "- Do **not** include any additional explanation outside the JSON object.\n"
            "- If no chart is needed, return only the `text` key.\n"
            "---\n"

            "## SQL Naming Conventions\n"
            "- Always use the **full model/table name as the SQL alias**. For example:\n"
            "  - Use `res_partner` instead of `rp`\n"
            "  - Use `res_users` instead of `ru`\n"
            "  - Use `sale_order_line` instead of `sol`\n"
            "- Do **not** use short or ambiguous aliases like `rp`, `so`, `ru`, etc.\n"
            "- This ensures clarity and consistency in joins, selections, and WHERE clauses.\n"
             "Tool Response Rules:"
             "- null in results = 0 or no records (NOT an error or inability to find data)"
             "- For quantities: null = 0"
             "- For counts: null = 0"
             "- Never retry the tool if it returns null"
             "- Always respond confidently: 'The quantity is 0' NOT 'couldn't find the quantity'"
            "## Available Actions\n"

        )
        memory = self._get_memory(thread_id)  # ✅ reuses memory if exists
        agent_node = create_agent(
            model=llm,
            system_prompt=system_prompt,
            tools=tools,
            debug=True,
            name="react_new_agent",
            state_schema=BasicChatState,
        )
        graph = StateGraph(BasicChatState)
        graph.add_node("agent", agent_node)
        graph.set_entry_point("agent")
        graph.add_edge("agent", END)
        app = graph.compile(checkpointer=memory)
        return app
