# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

from odoo import models, fields, api
from datetime import datetime


class RepairOrder(models.Model):
    """Extension of Repair Order to track operators and exact repair durations."""
    _inherit = 'repair.order'

    operator_ids = fields.Many2many(
        comodel_name='hr.employee',
        string="Operators"
    )
    repair_start_time = fields.Datetime(
        string="Repair Start Time",
        copy=False
    )
    repair_end_time = fields.Datetime(
        string="Repair End Time",
        copy=False
    )
    actual_duration = fields.Float(
        string="Actual Duration (Hours)",
        compute="_compute_actual_duration"
    )

    @api.depends('repair_start_time', 'repair_end_time')
    def _compute_actual_duration(self):
        """Calculates the duration between start and end times in hours."""
        for rec in self:
            if rec.repair_start_time and rec.repair_end_time:
                delta = rec.repair_end_time - rec.repair_start_time
                rec.actual_duration = delta.total_seconds() / 3600.0
            else:
                rec.actual_duration = 0.0

    def action_repair_start(self):
        """Overrides native start action to inject start time tracking."""
        res = super().action_repair_start()
        self.write({'repair_start_time': datetime.now()})
        return res

    def action_repair_end(self):
        """Overrides native end action to inject end time tracking."""
        res = super().action_repair_end()
        self.write({'repair_end_time': datetime.now()})
        return res

    def action_show_repair_notes(self):
        """Returns an action to open the repair notes in a custom popup view."""
        self.ensure_one()
        notes_view_id = self.env.ref('cyllo_shopfloor_repair.view_repair_floor_notes_popup').id
        return {
            'name': f'Repair Notes: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(notes_view_id, 'form')],
            'target': 'new',
        }
