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
from odoo.exceptions import ValidationError


class CarbonEmissionFactor(models.Model):
    _name = 'carbon.factor'
    _description = 'Emission Factor'
    _order = 'name'

    name = fields.Char(required=True)
    source_id = fields.Many2one('carbon.source', required=True, ondelete='restrict')
    gas_id = fields.Many2one('carbon.gas', required=True, ondelete='restrict')
    factor_value = fields.Float(required=True)
    unit_name = fields.Many2one('carbon.unit', string='Unit')
    region = fields.Char()
    provider = fields.Char()
    valid_from = fields.Date()
    valid_to = fields.Date()
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.constrains('valid_from', 'valid_to')
    def _check_valid_dates(self):
        for rec in self:
            if rec.valid_from and rec.valid_to and rec.valid_to < rec.valid_from:
                raise ValidationError('Valid To must be after Valid From.')
