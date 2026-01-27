# -*- coding: utf-8 -*-
from odoo import fields, models


class Website(models.Model):
    """ Inherited model for res.partner with additional fields and methods."""
    _inherit = 'website'

    is_active_sms = fields.Boolean(string='OTP Login', company_dependent=True, help="Enable login through OTP")
    gateway_id = fields.Many2one("sms.gateway.config", string="Provider", company_dependent=True,
                                 domain="[('is_active','=',True)]", required=True)
