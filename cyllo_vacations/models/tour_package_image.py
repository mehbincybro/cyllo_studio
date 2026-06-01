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


class TourPackageImage(models.Model):
    _name = 'tour.package.image'
    _description = 'Tour Package Additional Images'
    _order = 'sequence, id'

    name = fields.Char(string='Name', translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    image_1920 = fields.Image(string='Image', required=True, max_width=1920,
                              max_height=1920)
    package_id = fields.Many2one('tour.package', string='Package',
                                 required=True, ondelete='cascade')
