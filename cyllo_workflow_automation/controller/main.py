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
import mimetypes
import inspect
import secrets

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

    @http.route(
        '/cyllo_workflow/test_run',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def test_run_workflow(self, work_auto_id, **kwargs):
        """
            Validate a workflow in dry-run mode and return node-level results.
        """
        automation = request.env['work.auto'].browse(int(work_auto_id))
        if not automation.exists():
            return {
                'ok': False,
                'error': 'Workflow not found.',
            }
        try:
            payload = automation.dry_run()
        except Exception as exc:
            return {
                'ok': False,
                'error': str(exc),
            }
        return {
            'ok': True,
            **payload,
        }

    # ── Secret URL — Inbound Public Trigger ───────────────────────────────────

    @http.route(
        '/cyllo_webhook/trigger/<string:token>',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
    )
    def inbound_webhook_trigger(self, token, **kwargs):
        """
        Public endpoint that external systems call to trigger a webhook node's
        configured response actions.

        The ``token`` path segment is matched against ``node.struct.
        webhook_secret_token``.  An HTTP 404 is returned when no matching
        record is found so that token enumeration is not practical.

        Supported request formats
        --------------------------
        - **POST** with ``Content-Type: application/json`` — body parsed as
          JSON dict and passed as ``payload``.
        - **POST** with form data — form fields used as ``payload`` dict.
        - **GET** — query-string parameters used as ``payload`` dict.

        Args:
            token (str): The URL-safe secret token embedded in the route path.
            **kwargs (dict): Query-string / form parameters.

        Returns:
            werkzeug.wrappers.Response: JSON response body.
                - Success: ``{"ok": true, "message": "Webhook executed."}``
                - Not found: HTTP 404 ``{"ok": false, "error": "Not found."}``
                - Error:     HTTP 500 ``{"ok": false, "error": "<message>"}``
        """
        env = request.env

        # ── Resolve node by token ─────────────────────────────────────────
        node = env['node.struct'].sudo().search(
            [('webhook_secret_token', '=', token)], limit=1
        )
        if not node:
            return request.make_json_response(
                {'ok': False, 'error': 'Not found.'},
                status=404,
            )

        # ── Parse inbound payload ─────────────────────────────────────────
        payload = {}
        if request.httprequest.method == 'POST':
            content_type = request.httprequest.content_type or ''
            if 'application/json' in content_type:
                try:
                    raw_body = request.httprequest.get_data(as_text=True)
                    payload = json.loads(raw_body) if raw_body else {}
                except Exception:
                    payload = {}
            else:
                payload = dict(kwargs)
        else:
            payload = dict(kwargs)

        # ── Execute configured response actions ───────────────────────────
        actions = node.webhook_actions
        if not isinstance(actions, list):
            actions = []

        try:
            env['webhook.response.processor'].sudo().process_response_actions(
                response_data=payload,
                actions=actions,
                record=None,
                context_vars={},
            )
        except Exception as exc:
            return request.make_json_response(
                {'ok': False, 'error': str(exc)},
                status=500,
            )

        return request.make_json_response(
            {'ok': True, 'message': 'Webhook executed.'},
            status=200,
        )

    # ── Secret URL — Internal RPC Endpoints ───────────────────────────────────

    @http.route(
        '/cyllo_workflow/webhook_secret_url/<int:node_id>',
        type='json',
        auth='user',
        methods=['GET', 'POST'],
        csrf=False,
    )
    def get_webhook_secret_url(self, node_id, **kwargs):
        """
        Return the current Secret URL for a given ``node.struct`` record.

        The URL is assembled at read time from the live ``web.base.url`` system
        parameter so it always reflects the current server address even when
        the base URL has been changed since the token was generated.

        Args:
            node_id (int): The database ID of the ``node.struct`` record.
            **kwargs: Unused; present for Odoo JSON-RPC compatibility.

        Returns:
            dict:
                - ``url`` (str):   The full Secret URL, or ``""`` if the node
                  has no token yet.
                - ``token`` (str): The raw secret token value.
        """
        node = request.env['node.struct'].sudo().browse(node_id)
        if not node.exists():
            return {'url': '', 'token': ''}

        # Lazy Generation: if an existing record doesn't have a token, generate it now.
        token = node.webhook_secret_token or ''
        if not token:
            token = secrets.token_urlsafe(32)
            node.webhook_secret_token = token

        base_url = (
            request.env['ir.config_parameter']
            .sudo()
            .get_param('web.base.url', default='')
            .rstrip('/')
        )
        secret_url = f"{base_url}/cyllo_webhook/trigger/{token}"
        print(secret_url,token)
        return {'url': secret_url, 'token': token}

    @http.route(
        '/cyllo_workflow/regenerate_webhook_token',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def regenerate_webhook_token(self, node_struct_id, **kwargs):
        """
        Regenerate the secret token for a ``node.struct`` webhook record.

        This endpoint is called by the frontend "Regenerate" button *after* the
        user has confirmed the confirmation dialog.  The old Secret URL becomes
        invalid immediately upon this call.

        Args:
            node_struct_id (int): The database ID of the ``node.struct`` record
                whose token should be regenerated.
            **kwargs: Unused; present for Odoo JSON-RPC compatibility.

        Returns:
            dict:
                - ``ok``    (bool): ``True`` on success.
                - ``url``   (str):  The new full Secret URL.
                - ``token`` (str):  The new raw token value.
                - ``error`` (str):  Present only on failure; contains the
                  error message.
        """
        node = request.env['node.struct'].sudo().browse(int(node_struct_id))
        if not node.exists():
            return {'ok': False, 'error': 'node.struct record not found.'}

        try:
            result = node.action_regenerate_webhook_token()
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

        return {
            'ok': True,
            'url': result['url'],
            'token': result['token'],
        }
