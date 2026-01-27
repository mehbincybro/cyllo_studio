# -*- coding: utf-8 -*-
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
