# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class OneDriveAuth(http.Controller):
    """Controller for handling OneDrive authentication."""
    @http.route('/one_drive/auth', type='http', auth="public")
    def oauth2callback(self, **kw):
        """Callback function for OneDrive authentication.
        param kw: A dictionary of keyword arguments.
        return: A redirect response."""
        state = json.loads(kw['state'])
        one_drive_connector = request.env['one.drive.connector'].sudo().browse(state.get('one_drive_connector_id'))
        one_drive_connector.get_onedrive_tokens(kw.get('code'))
        return request.redirect(state.get('url_return'))
