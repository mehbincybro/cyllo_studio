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

from google.api_core.exceptions import ResourceExhausted
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.types import Command

import langsmith as ls

from odoo import fields, http
from odoo.http import Controller, request


_logger = logging.getLogger(__name__)


class ChatBotController(Controller):

    @http.route('/cyllo/get_agent_enabled', type='json', auth='user')
    def get_agent_enabled(self):
        """Check if the Cyllo agent is enabled in the system parameters."""
        value = http.request.env['ir.config_parameter'].sudo().get_param('cyllo_agent.enabled')
        return value

    @http.route('/cyllo/get_ai_widget_enabled', type='json', auth='user')
    def get_ai_widget_enabled(self):
        """Check if the Cyllo AI widget is enabled in the system parameters."""
        value = http.request.env['ir.config_parameter'].sudo().get_param('cyllo_ai_widget.enabled')
        return value

    @http.route('/cyllo/speech_to_text', type='json', auth='user')
    def get_text(self, encoded_audio):
        """
        Convert speech to text using the configured LLM provider.

       :param encoded_audio: Base64 encoded audio string
       :return: Transcribed text from the audio
       """
        _logger = logging.getLogger(__name__)
        try:
            param = request.env['ir.config_parameter'].sudo()
            agent_llm = param.get_param('cyllo_agent.llm')
            api_key = param.get_param('cyllo_agent.api_key')
            model_id = param.get_param('agent.llm_model_id')
            model_name = request.env['cyllo.llm'].browse(int(model_id)).name
            if agent_llm == "ChatGoogleGenerativeAI":
                llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, max_retries=0)
                # Gemini format
                message_content = [
                    {"type": "text", "text": "Transcribe the audio."},
                    {
                        "type": "media",
                        "data": encoded_audio,
                        "mime_type": "audio/mpeg",
                    },
                ]
            else:
                # OpenAI and OpenRouter format
                llm = ChatOpenAI(model=model_name, api_key=api_key)
                message_content = [
                    {"type": "text", "text": "Transcribe the audio."},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": encoded_audio,
                            "format": "mp3"  # or "wav", "opus", etc.
                        },
                    },
                ]

            result = llm.invoke([HumanMessage(content=message_content)])
            return result.content

        except ResourceExhausted as e:
            _logger.warning("Quota exceeded for Gemini API in speech-to-text: %s", str(e))
            return "Quota limit exceeded. Please try again later."

        except Exception as e:
            _logger.exception("Unexpected error during speech-to-text: %s", str(e))
            return "An error occurred while transcribing the audio. Please try again."

    @http.route('/chatbot/query', type='json', auth='user', csrf=False)
    def chatbot_query(self, **kwargs):
        """
        Process a user query through the chatbot agent.

        :param kwargs: Dictionary containing 'text', 'userId', and 'interrupted' status
        :return: Dictionary with 'response' and 'last_message'
        """
        text = kwargs.get('text')
        user_id = kwargs.get('userId')
        interrupted = kwargs.get('interrupted')
        session_id = kwargs.get('session_id')
        company_ids = kwargs.get('company_ids')
        agent_mode = kwargs.get('agent_mode')
        active_model = kwargs.get('active_model')
        active_id = kwargs.get('active_id')
        active_view = kwargs.get('active_view')
        active_name = kwargs.get('active_name')
        active_action_id = kwargs.get('active_action_id')

        agent_model = request.env['chatbot.agent'].with_context(
            active_model=active_model,
            active_id=active_id,
            active_view=active_view,
            active_name=active_name,
            active_action_id=active_action_id,
        )
        app = agent_model.build_agent(session_id)
        last_message = ""
        try:
            client = ls.Client(
                api_key="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",  # This can be retrieved from a secrets manager
                api_url="https://api.smith.langchain.com",
                # Update appropriately for self-hosted installations or the EU region
            )
            if not interrupted:
                with ls.tracing_context(client=client, project_name="cyllo-ai-phase2", enabled=True):
                    result = app.invoke(
                        {
                            "messages": [HumanMessage(content=text)],
                            "user_query": text,
                            "company_id": company_ids,
                            "agent_mode": agent_mode,
                            "active_model": active_model,
                            "active_id": active_id,
                            "active_view": active_view,
                            "active_name": active_name,
                            "active_action_id": active_action_id,
                        },
                        config={
                            "configurable": {
                                "thread_id": session_id
                            },
                            "recursion_limit": 15
                        }
                    )
                    last_message = result["messages"][-1].content
            else:
                result = app.invoke(
                    Command(resume=text),
                    config={
                        "configurable": {
                            "thread_id": session_id
                        },
                        "recursion_limit": 15
                    }
                )
                last_message = result["messages"][-1].content
            return {
                'response': result['__interrupt__'][0].value if "__interrupt__" in result else "none",
                'last_message': result["messages"][-1].content
            }

        except ResourceExhausted as e:
            _logger.warning("Quota exceeded for Gemini API: %s", str(e))
            return {
                'response': 'none',
                'last_message': '**Quota limit exceeded. Please try again later.**'
                                '<div style="font-size: smaller;">If the issue persists, please check your **plan** and'
                                ' **billing details** to ensure everything is in order.</div>'
            }

        except Exception as e:
            _logger.exception("Unexpected error during chatbot query")
            return {
                'response': 'none',
                'last_message': last_message
            }

    @http.route('/chatbot/set_conversation', type='json', auth='user')
    def set_conversation(self, user_id, session_id, user_message, response_message, chart_config, interrupted, company_ids):
        """
        Save a conversation entry to the chatbot history.

        :param user_id: ID of the user
        :param session_id: Session identifier
        :param user_message: Message sent by the user
        :param response_message: Response generated by the bot
        :param chart_config: Configuration for any generated charts
        :param interrupted: Boolean indicating if the response was interrupted
        :return: Dictionary containing the ID of the created record
        """


        chart_config = json.dumps(chart_config)
        new_record = request.env['chatbot.history'].create({
            'user_id': user_id,
            'session_id': session_id,
            'user_message': user_message,
            'response_message': response_message,
            'chart_config': chart_config,
            'interrupted': interrupted,
            # Many2many: use (6, 0, ids)
            'company_ids': [(6, 0, company_ids)],
            'create_date': fields.Datetime.now(),
        })
        return {'id': new_record.id}

    @http.route('/chatbot/get_conversation', type='json', auth='user')
    def get_conversation(self, session_id, company_id=None):
        """
        Retrieve the conversation history for a specific session.

        :param session_id: Session identifier
        :return: List of conversation dictionaries
        """

        # Convert single company_id to list for safety
        if company_id and not isinstance(company_id, list):
            company_ids = [company_id]
        else:
            company_ids = company_id or []

        domain = [
            ('session_id', '=', session_id),
            ('user_id', '=', request.env.uid),  # user-specific history
        ]

        # Add Many2many domain only if company_ids is provided
        if company_ids:
            domain.append(('company_ids', 'in', company_ids))

        records = request.env['chatbot.history'].sudo().search(
            domain,
            order='create_date asc, id asc'
        )

        history = []
        for rec in records:
            if rec.user_message:
                history.append({
                    "from": "user",
                    "text": rec.user_message,
                    "timestamp": rec.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "chart_config": None,
                })
            if rec.response_message:
                try:
                    chart_config = json.loads(rec.chart_config)
                except json.JSONDecodeError as e:
                    _logger.debug('Failed to parse chart_config as JSON for record %s: %s', rec.id, str(e),
                                  exc_info=True)
                    chart_config = None
                history.append({
                    "id": rec.id,
                    "from": "bot",
                    "text": rec.response_message,
                    "timestamp": rec.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "chart_config": chart_config,
                    "interrupted": rec.interrupted,
                })
        return history

    @http.route('/chatbot/set_interrupt', type='json', auth='user')
    def set_interrupt(self, record_id): 
        """
        Reset the interrupted status of a conversation record.

        :param record_id: ID of the chatbot history record
        :return: Dictionary with status 'success' or 'error'
        """
        record_id = int(record_id)
        history = request.env['chatbot.history'].browse(record_id)
        if history.exists():
            history.write({'interrupted': False})
            return {'status': 'success'}
        else:
            return {'status': 'error', 'message': 'Record not found'}
