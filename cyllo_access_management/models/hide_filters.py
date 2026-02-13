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
from odoo import api,fields, models
from odoo.exceptions import ValidationError


class HideFiltersTabs(models.Model):
    _name = 'hide.filters'
    _description = 'Hide Filters'
    _rec_name = 'model_id'

    profile_management_id = fields.Many2one('profile.management',
                                            string='Profile Management ID')
    model_id = fields.Many2one('ir.model', string='Model',
                               required=True, ondelete='cascade',
                               )
    filter_ids = fields.Many2many('ir.model.filters',
                                  'hide_filters_rel','hide_id',
                                  'filter_id',string='Hide Filters')

    group_ids = fields.Many2many('ir.model.filters',
                                 'hide_groups_rel','hide_id',
                                 'filter_id',string='Hide Groups')

    @api.constrains('filter_ids', 'group_ids')
    def _constraint_filter_ids_group_ids(self):
        for record in self:
            if not (record.filter_ids or record.group_ids):
                raise ValidationError('Provide at least one filter or group')
