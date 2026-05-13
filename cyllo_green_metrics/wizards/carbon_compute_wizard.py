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
from odoo import fields, models


class CarbonComputeWizard(models.TransientModel):
    _name = 'carbon.compute.wizard'
    _description = 'Compute Emissions Wizard'

    calculation_id = fields.Many2one('carbon.calc', required=True, ondelete='cascade')
    apply_rules = fields.Boolean(default=True)
    mark_done = fields.Boolean(default=True)

    def action_run(self):
        self.ensure_one()
        activities = self.calculation_id.activity_ids
        if self.apply_rules:
            activities.action_apply_rules()
        activities.action_compute()
        if self.mark_done:
            self.calculation_id.action_mark_done()
        return {'type': 'ir.actions.act_window_close'}
