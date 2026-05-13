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
from odoo.tools.safe_eval import safe_eval


class CarbonAssignationRule(models.Model):
    _name = 'carbon.assign.rule'
    _description = 'Emission Assignation Rule'
    _order = 'priority, name'

    name = fields.Char(required=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    domain = fields.Char(help='Domain string applied to target records.')
    source_id = fields.Many2one('carbon.source', required=True, ondelete='restrict')
    factor_id = fields.Many2one('carbon.factor', ondelete='restrict')
    method = fields.Selection([
        ('factor', 'Factor'),
        ('direct', 'Direct'),
    ], default='factor', required=True)
    priority = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.constrains('method', 'factor_id')
    def _check_factor_required(self):
        for rec in self:
            if rec.method == 'factor' and not rec.factor_id:
                raise ValidationError('Factor is required for Factor method.')

    def _get_domain(self):
        self.ensure_one()
        if not self.domain:
            return []
        try:
            return safe_eval(self.domain)
        except Exception:
            return []

    def _match(self, record):
        self.ensure_one()
        domain = self._get_domain()
        return record.filtered_domain(domain)
