# -*- coding: utf-8 -*-
import odoo
from odoo.http import request
from odoo.modules.registry import Registry
from odoo.http import Session


def authenticate_without_passwd(self, dbname, login):
    """This function creates an authentication methode without a password"""
    registry = Registry(dbname)
    pre_uid = request.env['res.users'].sudo().search([('login', '=', login)]).id
    self.uid = None
    self.pre_login = login
    self.pre_uid = pre_uid
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, pre_uid, {})
        user = env['res.users'].browse(pre_uid)
        if not user._mfa_url():
            self.finalize(env)
    if request and request.session is self and request.db == dbname:
        request.env = odoo.api.Environment(request.env.cr, self.uid,
                                           self.context)
        request.update_context(**self.context)
    return pre_uid


Session.authenticate_without_passwd = authenticate_without_passwd
