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
from odoo import fields, models, _


class TourPackageCategory(models.Model):
    _name = 'tour.package.category'
    _description = 'Tour Package Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    image = fields.Image(string='Image')
    active = fields.Boolean(default=True)
    package_count = fields.Integer(compute='_compute_package_count',
                                   string='Packages')

    def _compute_package_count(self):
        for category in self:
            category.package_count = self.env['tour.package'].search_count(
                [('category_id', '=', category.id)])

