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

class IrModelTabs(models.Model):
    _name = 'ir.model.tabs'
    _description = 'Ir Model Tabs'

    name = fields.Char('Name',required=True)
    string = fields.Char('String')
    view_id = fields.Many2one('ir.ui.view',string='View')
    model_id = fields.Many2one('ir.model',string='Model')

    @api.depends('string', 'name')
    def _compute_display_name(self):
        for tab in self:
            name = tab.name
            if tab.string and tab.name:
                name = f"{tab.string}({name})"
            tab.display_name = name

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('string', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)
