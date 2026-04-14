# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    task_ids = fields.One2many('project.task', 'helpdesk_ticket_id',
                               string='Field Service Tasks')
    task_count = fields.Integer(compute='_compute_task_count')

    @api.depends('task_ids')
    def _compute_task_count(self):
        for ticket in self:
            ticket.task_count = len(ticket.task_ids)
