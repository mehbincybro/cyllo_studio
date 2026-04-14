# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)
