# -*- coding: utf-8 -*-
from odoo import fields, models


class DiscussChannel(models.Model):
    """This class extends the 'discuss.channel' model in Odoo to include a new
     field for storing the Facebook Page ID."""
    _inherit = 'discuss.channel'

    fb_page_number = fields.Char(string="Facebook Page Id", help="Id of Facebook page")
