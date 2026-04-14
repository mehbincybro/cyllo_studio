# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    timesheet_ids = fields.One2many('account.analytic.line', 'ticket_id',
                                    string="Timesheet",
                                    help="Time spent by the employee for this ticket")
    timesheet_bool = fields.Boolean(related='team_id.timesheet')
