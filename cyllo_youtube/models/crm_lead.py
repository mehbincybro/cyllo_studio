# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLead(models.Model):
    """
    Inherits the base crm.lead model and adds Tasks information in
    the lead form.
    """
    _inherit = 'crm.lead'

    unique_yt_comment_number = fields.Char(string='Unique YouTube Comment Id',
                                           help="Unique identifier for the lead on YouTube.")
    youtube_user_number = fields.Char(string='Unique YouTube Id',
                                      help="Unique identifier for the partner on YouTube.")
