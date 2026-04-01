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
import mimetypes
import inspect

from odoo import http
from odoo.http import request


class CylloAutoWorkController(http.Controller):

    @http.route('/cyllo_auto_work/find/functions', type="json", auth="user", csrf=False)
    def cyllo_auto_work_find_functions(self, **kwargs):
        """
            Find and return a list of 'action' methods in the specified model.

            This method inspects the specified model, identifies methods starting with "action",
            and returns their names along with their argument specifications.

            Args:
               kwargs (dict): Keyword arguments passed to the route, expecting 'model' key
                              to specify the model name.

            Returns:
               list: A list of dictionaries, each containing the following:
                   - 'name': The name of the method.
                   - 'args': A list of argument names the method takes.
            """
        model = request.env[kwargs['model']]
        model_class = type(model)
        methods = []

        for attr_name in dir(model_class):
            attr = getattr(model_class, attr_name)
            if inspect.isfunction(attr) or inspect.ismethod(attr):
                if not attr_name.startswith(("__")) and attr_name.startswith("action"):
                    argspec = inspect.getfullargspec(attr)
                    method_info = {
                        'name': attr_name,
                        'args': argspec.args
                    }
                    methods.append(method_info)

        return methods

    @http.route(
        '/cyllo_workflow/upload_wa_attachment',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def upload_wa_attachment(self, name, data, mimetype=None, node_struct_id=None):
        """
            Create an attachment from the WhatsApp node file uploader.

            Args:
                name (str): Original filename.
                data (str): Base64-encoded file contents.
                mimetype (str, optional): Browser-reported mimetype.
                node_struct_id (int, optional): Persist link immediately when editing an existing node.

            Returns:
                dict: The created attachment's id and display name.
            """
        guessed_mimetype, _encoding = mimetypes.guess_type(name or '')
        attachment = request.env['ir.attachment'].sudo().create({
            'name': name,
            'type': 'binary',
            'datas': data,
            'mimetype': mimetype or guessed_mimetype or 'application/octet-stream',
        })
        if node_struct_id:
            node = request.env['node.struct'].sudo().browse(node_struct_id)
            if node.exists():
                node.write({
                    'wa_static_attachment_ids': [(4, attachment.id)],
                })
        return {
            'id': attachment.id,
            'name': attachment.name,
        }

    @http.route(
        '/cyllo_workflow/check_google_meet_installed',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def check_google_meet_installed(self, **kwargs):
        """
            Return whether the cyllo_google_meet module is installed and configured.

            Used by the Activity node dialog to decide whether to show the
            Google Meet section and whether the OAuth credentials are ready.
        """
        installed = request.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'cyllo_google_meet'),
            ('state', '=', 'installed'),
        ]) > 0
        params = request.env['ir.config_parameter'].sudo()
        configured = all([
            params.get_param('cyllo_google.client_id'),
            params.get_param('cyllo_google.client_secret'),
            params.get_param('cyllo_google.refresh_token'),
        ])
        return {
            'installed': installed,
            'configured': bool(installed and configured),
        }

    @http.route(
        '/cyllo_workflow/check_zoom_installed',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def check_zoom_installed(self, **kwargs):
        """
            Return whether the cyllo_zoom module is installed and configured.

            Used by the Activity node dialog to decide whether to show the
            Zoom Meet section and whether the access token is ready.
        """
        installed = request.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'cyllo_zoom'),
            ('state', '=', 'installed'),
        ]) > 0
        token = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_zoom.zoom_token',
        )
        return {
            'installed': installed,
            'configured': bool(installed and token),
        }
