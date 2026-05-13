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
from odoo import api, fields, models


class MrpWorkcenterCarbon(models.Model):
    _name = 'mrp.workcenter.carbon'
    _description = 'Manufacturing Operation Carbon Line'

    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation', ondelete='cascade', required=True)
    source_id = fields.Many2one('carbon.source', string='Name', required=True)
    unit_id = fields.Many2one('carbon.unit', string='Unit', related='source_id.activity_unit', readonly=False, store=True)

    @api.onchange('source_id')
    def _onchange_source_id(self):
        if self.source_id:
            self.unit_id = self.source_id.activity_unit
        else:
            self.unit_id = False
