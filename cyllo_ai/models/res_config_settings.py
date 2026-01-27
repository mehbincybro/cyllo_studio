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
import logging

import requests
from google.api_core.exceptions import ResourceExhausted
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from langchain_openai import ChatOpenAI
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cyllo_agent = fields.Boolean(string='Cyllo Chat', default=False, config_parameter='cyllo_agent.enabled')
    cyllo_agent_llm = fields.Selection([
        ('ChatOpenAI', 'ChatGPT'),
        ('ChatGoogleGenerativeAI', 'Google Gemini'),
        ('OpenRouter', 'OpenRouter'),
    ], string='Agent LLM Wrapper', config_parameter='cyllo_agent.llm')

    agent_llm_model_id = fields.Many2one(
        'cyllo.llm',
        string='LLM Model',
        domain="[('wrapper', '=', cyllo_agent_llm)]",
        config_parameter='agent.llm_model_id'
    )

    # OpenRouter specific fields
    openrouter_model = fields.Selection(
        selection='_get_openrouter_models',
        string='OpenRouter Model',
        config_parameter='openrouter.model'
    )

    cyllo_agent_api = fields.Char('Agent API', config_parameter='cyllo_agent.api_key')
    cyllo_ai_widget = fields.Char(string='Cyllo Ai Widget', config_parameter='cyllo_ai_widget.enabled')

    @api.model
    def _get_openrouter_models(self):
        """Fetch available models from OpenRouter API"""
        # Start with a None/Clear option
        models = [('', '-- Select a Model --')]

        try:
            response = requests.get(
                'https://openrouter.ai/api/v1/models',
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # Extract model data from response
                if 'data' in data:
                    for model in data['data']:
                        model_id = model.get('id', '')
                        model_name = model.get('name', model_id)
                        if model_id:
                            models.append((model_id, "%s (%s)" % (model_name, model_id)))

                # Sort only the model entries (skip the first 'None' option)
                model_entries = models[1:]
                model_entries.sort(key=lambda x: x[1])
                models = [models[0]] + model_entries

                if len(models) == 1:  # Only 'None' option exists
                    _logger.warning("No models found in OpenRouter API response")
                    models.append(('error', 'No models available'))

            else:
                _logger.error("Failed to fetch OpenRouter models: HTTP %s", response.status_code)
                models.append(('error', 'Error loading models'))

        except requests.exceptions.RequestException as e:
            _logger.error("Error fetching OpenRouter models: %s", str(e))
            models.append(('error', 'Error loading models'))
        except Exception as e:
            _logger.error("Unexpected error fetching OpenRouter models: %s", str(e))
            models.append(('error', 'Error loading models'))

        return models

    def action_refresh_openrouter_models(self):
        """Refresh the list of OpenRouter models"""
        # Clear the cached selection values
        self.env['ir.model.fields'].clear_caches()

        # Reload the current form view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_test_cyllo_llm_connection(self):
        """
        Validate the configured Cyllo LLM API key (OpenAI, Gemini, or OpenRouter) by sending a
        simple "Ping" request. Returns a success or failure notification.

        Returns:
            dict: Cyllo client action with success or error message.
        Raises:
            UserError: If the API key is invalid or the request fails.
        """
        self.ensure_one()
        self.execute()
        try:
            if self.cyllo_agent_llm == 'ChatOpenAI':
                # Basic sanity check; don't force prefix as Azure/OpenRouter may differ
                if not self.cyllo_agent_api or len(self.cyllo_agent_api) < 10:
                    raise UserError("OpenAI API key looks too short.")

                try:
                    llm = ChatOpenAI(
                        model=self.agent_llm_model_id.name or "gpt-4o-mini",
                        api_key=self.cyllo_agent_api,
                    )
                    response = llm.invoke([HumanMessage(content="Ping")])
                    if not response or not getattr(response, "content", None):
                        raise UserError("OpenAI API key is valid but returned no content.")
                except Exception as e:
                    _logger.error("OpenAI API validation failed: %s", str(e), exc_info=True)
                    raise UserError(_(
                        "There is a problem with your OpenAI API key.\n\n"
                        "OpenAI error:\n%s"
                    ) % str(e))

            elif self.cyllo_agent_llm == 'ChatGoogleGenerativeAI':
                if not self.cyllo_agent_api or len(self.cyllo_agent_api) < 20:
                    raise UserError("Google Gemini API key looks too short.")

                try:
                    llm = ChatGoogleGenerativeAI(
                        model=self.agent_llm_model_id.name or "gemini-pro",
                        google_api_key=self.cyllo_agent_api,
                    )
                    response = llm.invoke([HumanMessage(content="Ping")])
                    if not response or not response.content:
                        raise UserError("Gemini API key is valid but returned no content.")
                except (ResourceExhausted, ChatGoogleGenerativeAIError) as e:
                    _logger.warning("Quota exceeded or API error for Gemini API: %s", str(e))
                    raise UserError(_("Quota limit exceeded for this API key. Please check your plan and billing details."))
                except Exception:
                    raise UserError(_("There seems to be a problem with the provided Gemini key."))

            elif self.cyllo_agent_llm == 'OpenRouter':
                if not self.cyllo_agent_api or len(self.cyllo_agent_api) < 10:
                    raise UserError("OpenRouter API key looks too short.")

                if not self.openrouter_model:
                    raise UserError("Please select an OpenRouter model.")

                try:
                    # OpenRouter uses OpenAI-compatible API
                    llm = ChatOpenAI(
                        model=self.openrouter_model,
                        api_key=self.cyllo_agent_api,
                        base_url="https://openrouter.ai/api/v1",
                        default_headers={
                            "HTTP-Referer": "https://your-domain.com",  # Optional: Replace with your domain
                            "X-Title": "Cyllo Agent"  # Optional: Your app name
                        }
                    )
                    response = llm.invoke([HumanMessage(content="Ping")])
                    if not response or not getattr(response, "content", None):
                        raise UserError("OpenRouter API key is valid but returned no content.")
                except Exception as e:
                    _logger.error("OpenRouter API validation failed: %s", str(e), exc_info=True)
                    raise UserError(_(
                        "There is a problem with your OpenRouter API key.\n\n"
                        "OpenRouter error:\n%s"
                    ) % str(e))

            channel = "your_channel"
            message = {
                "chat_on": True,
                "channel": channel
            }
            self.env["bus.bus"]._sendone(channel, "notification", message)
            self.env['ir.config_parameter'].sudo().set_param('cyllo_ai_widget.enabled', '1')
            self.cyllo_ai_widget = True
            # If everything worked → success popup
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Cyllo AI connected successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except UserError as e:
            channel = "your_channel"
            message = {
                "chat_on": False,
                "channel": channel
            }
            self.env["bus.bus"]._sendone(channel, "notification", message)
            self.env['ir.config_parameter'].sudo().set_param('cyllo_ai_widget.enabled', '0')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Failed',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }
