# -*- coding: utf-8 -*-
import base64
from odoo import tools


def _pre_init_favicon(env):
    """
    A pre init hook for setting the favicon icon
    :param env:
    :return:
    """
    with tools.file_open('cyllo_website_branding/static/img/cyllo-logo.svg', 'rb') as f:
        favicon_binary = base64.b64encode(f.read())
        for record in env['website'].search([]):
            record.write({
                'favicon': favicon_binary
            })
