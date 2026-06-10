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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class TourPackageOption(models.Model):
    _name = 'tour.package.option'
    _description = 'Tour Package Option'
    _order = 'sequence, id'

    name = fields.Char(string='Option Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    package_id = fields.Many2one('tour.package', string='Tour Package', required=True, ondelete='cascade')
    description = fields.Text(string='Description', translate=True)
    option_type = fields.Selection([
        ('hotel', 'Hotel/Accommodation'),
        ('room', 'Room Type'),
        ('transportation', 'Transportation'),
        ('meal', 'Meal Plan'),
        ('attraction', 'Attraction/Activity'),
        ('other', 'Other'),
    ], string='Option Type', default='other', required=True)
    is_required = fields.Boolean(string='Is Required', default=False, help="If checked, the customer must select an option from this category.")
    line_ids = fields.One2many('tour.package.option.line', 'option_id', string='Choices')
    default_line_id = fields.Many2one(
        'tour.package.option.line',
        string='Default Choice',
        compute='_compute_default_line_id',
    )

    @api.depends('line_ids.is_default', 'line_ids.sequence')
    def _compute_default_line_id(self):
        for option in self:
            option.default_line_id = option.line_ids.filtered('is_default')[:1] or option.line_ids[:1]

    @api.constrains('is_required', 'line_ids')
    def _check_required_has_choices(self):
        for option in self:
            if option.is_required and not option.line_ids:
                raise ValidationError(_('Required customization options must have at least one choice.'))
