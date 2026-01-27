# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLead(models.Model):
    """This class extends the 'crm.lead' model in Odoo to include a new field
    for storing the unique Facebook ID of a partner."""
    _inherit = 'crm.lead'

    mail_message_id = fields.Many2one('mail.message', string='Related Mail Message',
                                      help="Message related to this lead")
