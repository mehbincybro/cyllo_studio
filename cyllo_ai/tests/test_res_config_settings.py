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
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase

class TestResConfigSettings(TransactionCase):
    """
    Test cases for 'res.config.settings' related to AI configuration and connectivity.
    """

    def setUp(self):
        """
        Setup test data for AI configuration tests.
        """
        super(TestResConfigSettings, self).setUp()
        self.ResConfigSettings = self.env['res.config.settings']
        self.CylloLlm = self.env['cyllo.llm']
        
        self.llm_model = self.CylloLlm.create({
            'name': 'gpt-4o',
            'display_name': 'GPT 4o',
            'wrapper': 'ChatOpenAI'
        })
        
        self.config = self.ResConfigSettings.create({
            'cyllo_agent': True,
            'cyllo_agent_llm': 'ChatOpenAI',
            'cyllo_agent_api': 'sk-valid-api-key-1234567890',
            'agent_llm_model_id': self.llm_model.id
        })

    @patch('odoo.addons.cyllo_ai.models.res_config_settings.ChatOpenAI')
    def test_test_connection_openai_success(self, MockChatOpenAI):
        """
        Test successful connection to OpenAI through the configuration settings.
        """
        # Setup mock behavior
        mock_llm_instance = MockChatOpenAI.return_value
        mock_response = MagicMock()
        mock_response.content = "Pong"
        mock_llm_instance.invoke.return_value = mock_response

        # Execute
        res = self.config.action_test_cyllo_llm_connection()
        
        # Verify
        self.assertEqual(res['type'], 'ir.actions.client')
        self.assertEqual(res['params']['type'], 'success')
        self.assertTrue(self.config.cyllo_ai_widget)
        
        MockChatOpenAI.assert_called() 
        mock_llm_instance.invoke.assert_called()

    @patch('odoo.addons.cyllo_ai.models.res_config_settings.ChatOpenAI')
    @patch('odoo.addons.cyllo_ai.models.res_config_settings._logger')
    def test_test_connection_openai_failure(self, mock_logger, MockChatOpenAI):
        """
        Test connection failure handling for OpenAI with an invalid API key.
        """
        # Setup mock to raise exception
        mock_llm_instance = MockChatOpenAI.return_value
        mock_llm_instance.invoke.side_effect = Exception("Auth Error")
        
        # Execute
        res = self.config.with_user(self.env.user).action_test_cyllo_llm_connection()
        
        # Verify returns danger notification
        self.assertEqual(res['type'], 'ir.actions.client')
        self.assertEqual(res['params']['type'], 'danger')
        self.assertEqual(res['params']['title'], 'Connection Failed')

    @patch('odoo.addons.cyllo_ai.models.res_config_settings.requests.get')
    def test_get_openrouter_models_success(self, mock_get):
        """
        Test the successful retrieval of available models from OpenRouter.
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'mistralai/mistral-7b', 'name': 'Mistral 7B'},
                {'id': 'openai/gpt-3.5-turbo', 'name': 'GPT 3.5'}
            ]
        }
        mock_get.return_value = mock_response
        
        # Execute
        models = self.ResConfigSettings._get_openrouter_models()
        
        # Verify
        self.assertTrue(len(models) > 1)
        self.assertEqual(models[0], ('', '-- Select a Model --'))
        model_ids = [m[0] for m in models]
        self.assertIn('mistralai/mistral-7b', model_ids)

    @patch('odoo.addons.cyllo_ai.models.res_config_settings.requests.get')
    def test_get_openrouter_models_error(self, mock_get):
        """
        Test the handling of API errors when fetching models from OpenRouter.
        """
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        models = self.ResConfigSettings._get_openrouter_models()
        self.assertIn(('error', 'Error loading models'), models)
