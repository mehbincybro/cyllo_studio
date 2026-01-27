# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class LangSwitch(http.Controller):
    """The LangSwitch class is used to change the current user's language.
    Methods:
        switch_user_lang(self, **kw):
            Getting value of the selected language and change the language in the backend.
    """
    @http.route('/lang_switch', auth='public', type='json', csrf=False)
    def switch_user_lang(self, **kw):
        """Summary: Getting value of the selected language and change the language in the backend.
        Args: kw(dict):It consists of the code of the selected language."""
        module = request.env['ir.module.module'].search([('state', '=', 'installed')])
        module._update_translations(kw['lang'], True)
        request.env.user.lang = kw['lang']
