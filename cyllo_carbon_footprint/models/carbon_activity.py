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


class CarbonActivity(models.Model):
    _name = 'carbon.activity'
    _description = 'Carbon Activity'
    _order = 'date, name'

    name = fields.Char(required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    calculation_id = fields.Many2one('carbon.calc', ondelete='set null')
    source_id = fields.Many2one('carbon.source', required=True, ondelete='restrict')
    scope_id = fields.Many2one('carbon.scope', ondelete='restrict')
    quantity = fields.Float(required=True)
    uom_name = fields.Many2one('carbon.unit', string='Unit')
    factor_id = fields.Many2one(
        'carbon.factor',
        ondelete='restrict',
        domain="[('source_id', '=', source_id)]",
    )
    gas_id = fields.Many2one('carbon.gas', ondelete='restrict')
    factor_value = fields.Float()
    emission_total = fields.Float(string='Emissions', compute='_compute_emissions', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    cost_total = fields.Monetary(string='Cost')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', required=True)
    note = fields.Text()

    @api.onchange('source_id')
    def _onchange_source_id(self):
        if self.source_id:
            self.uom_name = self.source_id.activity_unit
            self.scope_id = self.source_id.scope_id

    @api.onchange('factor_id')
    def _onchange_factor_id(self):
        if self.factor_id:
            self.gas_id = self.factor_id.gas_id
            self.factor_value = self.factor_id.factor_value
            self.uom_name = self.factor_id.unit_name

    @api.constrains('quantity', 'factor_value')
    def _check_values(self):
        for rec in self:
            if rec.quantity < 0 or rec.factor_value < 0:
                raise ValidationError('Quantity and factor must be non-negative.')

    @api.depends('quantity', 'factor_value')
    def _compute_emissions(self):
        for rec in self:
            if rec.quantity and rec.factor_value:
                rec.emission_total = rec.quantity * rec.factor_value
            else:
                rec.emission_total = 0.0

    def action_apply_rules(self):
        rules = self.env['carbon.assign.rule'].search([
            ('model_id.model', '=', 'carbon.activity'),
            ('active', '=', True),
        ], order='priority, id')
        for rec in self:
            if rec.factor_id:
                continue
            for rule in rules:
                if rule._match(rec):
                    rec.source_id = rule.source_id
                    if rule.factor_id:
                        rec.factor_id = rule.factor_id
                        rec.gas_id = rule.factor_id.gas_id
                        rec.factor_value = rule.factor_id.factor_value
                    break

    def action_compute(self):
        for rec in self:
            if not rec.factor_value:
                raise ValidationError('Factor value is required to compute emissions.')
            rec.state = 'done'
