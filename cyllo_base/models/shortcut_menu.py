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


class AddToShortcut(models.Model):
    _name = 'shortcut.menu'
    _description = 'Shortcut Menus'

    name = fields.Char('Name')
    res_model = fields.Many2one('ir.model', 'Model')
    window_action_id = fields.Many2one('ir.actions.act_window')
    client_action_id = fields.Many2one('ir.actions.client')
    server_action_id = fields.Many2one('ir.actions.server')
    menu_id = fields.Many2one('ir.ui.menu')
    xml_id = fields.Char(
        string='External ID', related='window_action_id.xml_id', store=True)
    model = fields.Char(related='window_action_id.res_model')
    path = fields.Char('Path')
    view_type = fields.Char('View Type')
