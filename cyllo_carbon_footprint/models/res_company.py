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
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    carbon_cap = fields.Float(
        string='Carbon Cap',
        help='Maximum allowed carbon emissions'
    )
    carbon_unit = fields.Selection([
        ('kg', 'kg CO2e'),
        ('t', 't CO2e'),
    ], string='Unit', default='t')
    carbon_duration = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', '6 Months'),
        ('yearly', 'Yearly'),
    ], string='Duration', default='yearly')

    water_cap = fields.Float(
        string='Allocated Water',
        help='Maximum allowed water usage'
    )
    water_unit = fields.Selection([
        ('L', 'L'),
        ('KL', 'KL'),
        ('tonnes', 'tonnes'),
    ], string='Unit', default='L')
    water_duration = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', '6 Months'),
        ('yearly', 'Yearly'),
    ], string='Duration', default='yearly')

    mrp_integration = fields.Boolean(
        string='MRP Integration',
        default=True,
        help='Automatically calculate carbon emissions based on manufacturing order operations'
    )
    fleet_integration = fields.Boolean(
        string='Fleet Integration',
        default=False,
        help='Integrate fleet with green metrics'
    )