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
import base64
from pickle import FALSE

import requests

from odoo import fields, http,release
from odoo.exceptions import ValidationError
from odoo.http import request, _logger
from odoo.addons.iap.tools import iap_tools

import json
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'



class CylloVoiceToTextChatter(http.Controller):
    """Class for Summarise the text in chatter"""

    @http.route('/cyllo_studio/summarise/text', type='json', auth="public")
    def summarise_text(self,transcribed_text):
        """Function for summarise transcribed data."""
        config_parameter = request.env['ir.config_parameter'].sudo()
        olg_api_endpoint = config_parameter.get_param(
            'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
        summarization_prompt = (
            "Summarize the following text into concise bullet points while keeping the tense consistent with the original text. "
            "Remove repetition and avoid unnecessary reported speech. Return precise points only.\n\n"
            f"{transcribed_text}"
        )
        response = iap_tools.iap_jsonrpc(
            olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': summarization_prompt,
                'conversation_history': [],
                'version': release.version,
            }, timeout=30
        )
        if response['status'] == 'success':
            return {'content': response['content']}
        else:
            return {'error': response.get('status', 'error')}
