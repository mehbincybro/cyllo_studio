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
from odoo import api, models, fields


class IrModel(models.Model):
    """Extension of ir.model.fields for Studio-created fields."""
    _inherit = 'ir.model.fields'

    is_studio = fields.Boolean(string='Studio Field', default=False,
                               help="Notify field created through Studio")

    @api.model
    def create_new_fields(self, args):
        """Create a new custom field for a model."""
        model = self.env['ir.model'].search([('model', '=', args['model'])])
        technical_name = 'x_cy_' + args['technical_name']
        ir_model_field = self.create({
            'name': technical_name,
            'complete_name': args['label'],
            'model': args['model'],
            'model_id': model.id,
            'ttype': args['field_type'],
            'field_description': args['help'],
            'state': 'manual',
            'is_studio': True
        })

class IrUiView(models.Model):
    """Extension of ir.ui.view for Studio-created views."""
    _inherit = 'ir.ui.view'

    is_studio = fields.Boolean(string='Studio Field', default=False,
                               help="Notify field created through Studio")
