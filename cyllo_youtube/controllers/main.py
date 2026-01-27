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
from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import json


class YouTubeAuthorizationController(http.Controller):
    """
        Controller for handling YouTube authorization callbacks.
        """

    @http.route('/odoo_youtube', type='http', auth='public', website=True)
    def youtube_auth_callback(self, **kwargs):
        """
            Callback function for handling YouTube authorization.
        """
        state = json.loads(kwargs['state'])
        authorization_code = kwargs.get('code')
        if authorization_code:
            request.env['youtube.account'].sudo().browse(state['id']).authenticate_with_youtube(authorization_code)
            return request.redirect(state['url_return'])
