# -*- coding: utf-8 -*-
from odoo import fields, models


class CountryCode(models.Model):
    """Model to store country codes."""
    _name = 'country.code'
    _description = 'Country Code'
    _rec_name = 'country'

    country = fields.Char(string="Country With code", help="Name of country")
    code = fields.Char(string="Phone Number code", help="Country code")
