# -*- coding: utf-8 -*-
import base64
from odoo.addons.web.controllers.webmanifest import WebManifest

from odoo import http
from odoo.http import request
from odoo.tools import file_open


class CylloWebManifest(WebManifest):
    """Subclass of WebManifest for managing Cyllo web manifest."""

    def _icon_path(self):
        """Return the path to the Cyllo icon."""
        return 'cyllo_branding/static/src/img/cyllo-logo-png.png'

    @http.route('/web/offline', type='http', auth='public', methods=['GET'])
    def offline(self):
        """Returns the offline page delivered by the service worker"""
        return request.render('web.webclient_offline', {
            'cyllo_icon': base64.b64encode(file_open(self._icon_path(), 'rb').read())
        })
