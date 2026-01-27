# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectTask(models.Model):
    """ Class to add a ticket field in invoice to connect Support service
    and project task """
    _inherit = 'project.task'

    ticket_id = fields.Many2one('support.service.ticket', string="Support Service Ticket")
