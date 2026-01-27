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
from odoo import models


class HrEmployee(models.Model):
    """
       Extend the functionality of the hr.employee model.
       This class inherits from the hr.employee model to add custom functionality.
       """
    _inherit = 'hr.employee'

    def action_open_record(self):
        """
              Action to open an employee record in a new window.

              This method returns an action to open the employee record in a new window.
              It sets the appropriate model, resource ID, view ID, and target for the action.

              Returns:
                  dict: A dictionary describing the action to be executed.
              """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.env.context.get('id', False),
            'view_id': self.env.ref('hr.view_employee_form').id,
            'target': 'new',
            'views': [(False, 'form')],
        }
