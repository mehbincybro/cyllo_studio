# -*- coding: utf-8 -*-
def install_cyllo_base(env):
    """Fetching and installing cyllo_base"""
    env['ir.module.module'].search([('name', '=', 'cyllo_base')]).button_install()
