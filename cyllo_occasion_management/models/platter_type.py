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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PlatterType(models.Model):
    """Model to define platter types with food items and catering members."""
    _name = 'platter.type'
    _description = 'Platter Type'

    name = fields.Char(string="Name", required=True)
    amount_per_person = fields.Float(string="Amount Per Person")
    catering_member_ids = fields.One2many('platter.member.line', 'platter_id', string="Catering Members")
    platter_food_line_ids = fields.One2many('platter.food.line', 'platter_id', string="Foods and Beverages")
    total_food_amount = fields.Float(string="Total Food Amount", compute='_compute_total_food_amount', readonly=True)

    @api.depends('platter_food_line_ids.food_ids')
    def _compute_total_food_amount(self):
        """Compute total amount based on selected food items in platter."""
        for record in self:
            total = 0
            for line in record.platter_food_line_ids:
                total += sum(line.food_ids.mapped('lst_price'))
            record.total_food_amount = total

class PlatterMemberLine(models.Model):
    """Model to manage catering members assigned to a platter category."""
    _name = 'platter.member.line'
    _description = 'Platter Member Line'

    platter_id = fields.Many2one('platter.type', string="Platter Type")
    category_id = fields.Many2one('catering.category', string="Catering Category", required=True)
    employee_ids = fields.Many2many('hr.employee', string="Employees", compute='_compute_employee_ids', store=True, readonly=False)
    available_employee_ids = fields.Many2many('hr.employee', compute='_compute_available_employee_ids')
    count = fields.Integer(string="Count", compute='_compute_count', store=True, readonly=False)

    _sql_constraints = [
        ('unique_category', 'unique(platter_id, category_id)', 'A category can only be added once per platter.')
    ]

    @api.constrains('count', 'employee_ids')
    def _check_count(self):
        """Ensure employee count does not exceed defined count."""
        for record in self:
            if record.count < len(record.employee_ids):
                raise ValidationError(_("The count cannot be less than the number of selected employees for category %s.") % record.category_id.name)

    @api.depends('employee_ids')
    def _compute_count(self):
        """Compute count based on number of selected employees."""
        for line in self:
            line.count = len(line.employee_ids)

    @api.depends('category_id')
    def _compute_available_employee_ids(self):
        """Compute available employees based on selected catering category for domain filtering."""
        for record in self:
            record.available_employee_ids = record.category_id.employee_ids

    @api.depends('category_id')
    def _compute_employee_ids(self):
        """Auto-fill employees based on selected catering category."""
        for line in self:
            if line.category_id:
                line.employee_ids = line.category_id.employee_ids
            else:
                line.employee_ids = [(5, 0, 0)]

class PlatterFoodLine(models.Model):
    """Model to manage food items grouped by category within a platter."""
    _name = 'platter.food.line'
    _description = 'Platter Food Line'

    platter_id = fields.Many2one('platter.type', string="Platter Type")
    category_id = fields.Many2one('catering.food.category', string="Food Category", required=True)
    food_ids = fields.Many2many('product.product', string="Foods", domain="[('is_catering_product', '=', True), ('catering_food_category_ids', 'in', category_id)]")

    _sql_constraints = [
        ('unique_category', 'unique(platter_id, category_id)', 'A food category can only be added once per platter.')
    ]
