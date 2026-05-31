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


class TourPackageExclusion(models.Model):
    _name = 'tour.package.exclusion'
    _description = 'Tour Package Exclusion'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Exclusion', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    package_id = fields.Many2one('tour.package', string='Package',
                                 required=True, ondelete='cascade')
    icon = fields.Selection([
        ('fa-times-circle', 'Cross (Standard Excluded)'),
        ('fa-bed', 'Accommodation (Bed)'),
        ('fa-plane', 'Flight (Plane)'),
        ('fa-bus', 'Bus / Land Transport'),
        ('fa-car', 'Car / Private Cab'),
        ('fa-cutlery', 'Meals / Food'),
        ('fa-users', 'Group / Tour Guide'),
        ('fa-ticket', 'Entrance Ticket'),
        ('fa-camera', 'Sightseeing / Activities'),
        ('fa-shield', 'Travel Insurance'),
        ('fa-suitcase', 'Luggage / Baggage'),
        ('fa-wifi', 'Free Wi-Fi'),
        ('fa-coffee', 'Breakfast / Beverages'),
        ('fa-map', 'Map / Directions'),
        ('fa-compass', 'Adventure / Navigation'),
        ('fa-globe', 'Visa / International'),
        ('fa-gift', 'Souvenir / Welcome Gift'),
        ('fa-percent', 'Discount / Offer'),
        ('fa-question-circle', 'Other / Miscellaneous'),
    ], string='Icon', default='fa-times-circle',
        help="Select a visual icon representing this exclusion. This icon is displayed next to the item on the PDF itinerary report and customer-facing website to indicate it is not included.")

