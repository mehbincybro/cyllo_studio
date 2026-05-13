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
from odoo import api, fields, models
from lxml import etree


class IrButtons(models.Model):
    _name = 'ir.buttons'
    _description = 'Ir Model Buttons'

    name = fields.Char('Name', required=True)
    string = fields.Char('String')
    view_id = fields.Many2one('ir.ui.view', string='View')
    model_id = fields.Many2one('ir.model', string='Model')

    @api.depends('string', 'name')
    def _compute_display_name(self):
        for button in self:
            name = button.name
            if button.string and button.name:
                name = f"{button.string}({name})"
            button.display_name = name

    @api.model
    def action_sync_buttons(self, model=None):
        """
        Scan all views, extract all object buttons,
        and store them in ir.buttons.
        """
        domain = [('model', '=', model.model)] if model else []
        views = self.env['ir.ui.view'].search(domain)

        for view in views:
            try:
                arch = etree.fromstring(view.arch_db)

                for btn in arch.xpath('//button'):
                    btn_type = btn.get('type')
                    btn_name = btn.get('name')
                    btn_string = btn.get('string')

                    # Only "object" type buttons need approval logic
                    if btn_type == 'object' and btn_name and btn_string:

                        existing = self.search([
                            ("name", "=", btn_name),
                            ("view_id", "=", view.id),
                        ], limit=1)

                        if not existing:
                            self.create({
                                'name': btn_name,
                                'string': btn_string,
                                'view_id': view.id,
                                'model_id': view.model_id.id,
                            })

            except Exception:
                continue
