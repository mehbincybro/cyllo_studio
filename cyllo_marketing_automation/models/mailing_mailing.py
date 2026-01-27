# -*- coding: utf-8 -*-
from odoo import fields, models


class MailingMailing(models.Model):
    """
        This model inherits from the base 'mailing.mailing' model and extends
        or overrides its functionality as needed.
    """
    _inherit = "mailing.mailing"

    cy_automation_template = fields.Boolean(string='Automation Template', help='Is marketing automation template')
