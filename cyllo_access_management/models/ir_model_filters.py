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
from odoo import api,fields,models

class IrModelFilters(models.Model):
    _name = 'ir.model.filters'
    _description = 'Ir Model Filters'

    name = fields.Char('Name',required=True)
    string = fields.Char('String')
    is_group_by = fields.Boolean('Is Group By')
    view_id = fields.Many2one('ir.ui.view',string='View')
    model_id = fields.Many2one('ir.model',string='Model')

    @api.depends('string', 'name')
    def _compute_display_name(self):
        for filter in self:
            name = filter.name
            if filter.string and filter.name:
                name = f"{filter.string}({name})"
            filter.display_name = name
