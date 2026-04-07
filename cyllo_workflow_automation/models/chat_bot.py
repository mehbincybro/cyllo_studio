from odoo import models, fields, api
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI
# import json
import re

class ChatBot(models.Model):
    _name = 'chat.bot'
    _description = 'AI Chat Bot'

    name = fields.Char()

    @api.model
    def my_python_method(self, user_query):
        print(user_query)
        client = genai.Client(api_key='AIzaSyBbFScW3Q4eGH9LNw9R9Hr4uY1-of4_QLI')

        prompt = f"""
        You are an Odoo workflow automation assistant. Your task is to convert a user’s natural language request into a structured JSON workflow that can be used in Odoo.

        Rules:
        1. Choose the Odoo model (object) the workflow applies to (e.g., sale.order, purchase.order, account.move).
        2. Choose a trigger: [on_create, on_delete, on_write].
        3. Specify conditions as a list of objects:
           [{{"field": "field_name", "operator": ">", "value": 0}}]
           - Only include conditions mentioned in the user query.
        4. Specify building_blocks: ["create", "write"]
           - "create" → creating new records
           - "write" → updating existing records
        5. Specify actions as a list:
           - warning → show a warning message
           - mail → send an email
           - sms → send an SMS
           - write → update fields in the record
           - followup → create a follow-up activity

        JSON must follow this format exactly. Do not include explanations or extra text.

        Example 1:
        User query: Create a warning when a Sale Order is created if discount > 50%
        Output:
        {{
            "object": "sale.order",
            "trigger": "on_create",
            "building_blocks": ["create"],
            "conditions": [{{"field": "discount", "operator": ">", "value": 50}}],
            "actions": [{{"type": "warning", "message": "Discount greater than 50%"}}]
        }}

        Example 2:
        User query: Update sale order if total greater than 100, tax will be 20%
        Output:
        {{
            "object": "sale.order",
            "trigger": "on_write",
            "building_blocks": ["write"],
            "conditions": [{{"field": "total", "operator": ">", "value": 100}}],
            "actions": [{{"type": "write", "field": "tax", "value": 20}}]
        }}

        Example 3:
        User query: Send email to manager when invoice amount exceeds 5000
        Output:
        {{
            "object": "account.move",
            "trigger": "on_write",
            "building_blocks": ["write"],
            "conditions": [{{"field": "amount_total", "operator": ">", "value": 5000}}],
            "actions": [{{"type": "mail", "to": "manager"}}]
        }}

        Now generate workflow JSON for this user query:
        {user_query}
        """

        content = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
#ai json data

        # text = content.text.strip()
        # # Remove Markdown formatting like ```json or ```
        # text = re.sub(r"^```[a-zA-Z]*", "", text)
        # text = re.sub(r"```$", "", text)
        # text = text.strip()
        #
        # try:
        #     data = json.loads(text)
        #     return data
        #
        # except Exception as e:
        #     print("JSON decode error:", e)
        #     return {"error": "Invalid JSON", "raw": text}

#testing with demo data
        demo = {
        "object": "sale.order",
        "trigger": "On Unlink",
        "building_blocks": ["create"],
        "conditions": [
            {"field": "discount", "operator": ">", "value": 50}
        ],
        "actions": [
            {"type": "Warning", "message": "Discount greater than 50%"},
            {"type": "SMS", "to": "manager@example.com"},
            {"type": "Mail", "summary": "Check discount approval"}
        ]
    }
        return demo


