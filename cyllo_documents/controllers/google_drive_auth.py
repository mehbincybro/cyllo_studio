# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class GoogleDriveAuth(http.Controller):
    """Controller for handling Google Drive authentication."""

    @http.route('/google_drive/auth', type='http', auth="public")
    def gdrive_oauth2callback(self, **kw):
        """Callback function for Google Drive authentication. This function is used as the callback URL when
        authorizing access to Google Drive.It retrieves the authorization code and uses it
            :param kw: Keyword arguments containing information from the
             Google Drive authentication callback.
            return: Redirects to the specified URL after obtaining access tokens.
            :rtype: http.Response
        """
        state = json.loads(kw['state'])
        google_drive_connector = request.env['google.drive.connector'].sudo().browse(
            state.get('google_drive_connector_id'))
        google_drive_connector.get_google_drive_tokens(kw.get('code'))
        return request.redirect(state.get('url_return'))
