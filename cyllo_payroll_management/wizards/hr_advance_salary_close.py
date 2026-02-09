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
from odoo import models, fields, api, _

class HrAdvanceSalaryCloseWizard(models.TransientModel):
    _name = 'hr.advance.salary.close.wizard'
    _description = 'Advance Salary Close Wizard'

    advance_id = fields.Many2one('hr.advance.salary', string="Advance Request", required=True)

    def action_close(self):
        self.ensure_one()
        self.advance_id.write({'state': 'closed'})
        return {'type': 'ir.actions.act_window_close'}
