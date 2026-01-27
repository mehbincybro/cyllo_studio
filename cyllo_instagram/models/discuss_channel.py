# -*- coding: utf-8 -*-
from odoo import fields, models


class DiscussChannel(models.Model):
    """This class extends the 'discuss.channel' model in Odoo to include a new field for storing the
    Instagram Page ID."""
    _inherit = 'discuss.channel'

    instagram_account_number = fields.Char(string="Instagram Account Id", help="Id of Instagram Account")
