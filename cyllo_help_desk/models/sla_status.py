# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import datetime
from odoo import fields, models


class SLAStatus(models.Model):
    _name = "sla.status"
    _description = "Helpdesk SLA Status"

    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket", help="Helpdesk tickets")
    state = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string="Status")

    def status_update(self):
        all_tickets = self.env['helpdesk.ticket'].search([('sla_flag', '=', True)])
        for ticket in all_tickets:
            work_hours = ticket.team_id.working_hour_id or ticket.company_id.resource_calendar_id
            if not work_hours:
                continue
            sorted_records = sorted(ticket.sla_ids,
                                    key=lambda x: x['within_hour'])
            for record in sorted_records:
                # Calculating the time difference between created datetime and
                # current datetime
                created_date = datetime.strptime(str(ticket.create_date),
                                                 "%Y-%m-%d %H:%M:%S.%f")
                # Calculating the SLA deadline
                average_work_hours = work_hours.hours_per_day or 8
                deadline = record.within_hour / average_work_hours
                deadline_in_hours = deadline * average_work_hours
                deadline_date = work_hours.plan_hours(deadline_in_hours,
                                                      created_date,
                                                      compute_leaves=True)
                if record.target_stage.sequence >= ticket.stage_id.sequence and deadline_date >= datetime.now():
                    if record.target_stage.sequence >= ticket.stage_id.sequence:
                        self.create(
                            {'id': record.id, 'ticket_id': ticket.id,
                             'state': 'pass'})
                else:
                    if record.target_stage.sequence == ticket.sequence or (
                            record.target_stage.sequence >= ticket.stage_id.sequence and deadline_date <= datetime.now()):
                        self.create(
                            {'id': record.id, 'ticket_id': ticket.id,
                             'state': 'fail'})
                        ticket.sla_failed = True

