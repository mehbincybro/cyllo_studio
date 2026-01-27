# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLead(models.Model):
    """Inherits the base crm.lead model and adds Tasks information in the lead form."""
    _inherit = 'crm.lead'

    unique_fb_comment_number = fields.Char(string='Unique Facebook Comment Id',
                                           help="Unique identifier for the lead on Facebook.")
    fb_user_number = fields.Char(string='Unique Facebook Id', help="Unique identifier for the partner on Facebook.")
