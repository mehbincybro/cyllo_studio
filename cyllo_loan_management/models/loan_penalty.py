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
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class LoanPenalty(models.Model):
    _name = 'loan.penalty'
    _description = 'Loan Penalty Configuration'

    name = fields.Char(string='Name', required=True)
    days_from = fields.Integer(string='From (Days)', required=True, default=1)
    days_to = fields.Integer(string='To (Days)', required=True, default=0, help="0 means Infinity")
    penalty_type = fields.Selection([
        ('percentage', '% of Due'),
        ('fixed', 'Fixed Amount'),
        ('both', 'Fixed + % of Due')
    ], string='Calculation Type', required=True, default='percentage')
    amount_fixed = fields.Float(string='Fixed Amount')
    amount_percentage = fields.Float(string='Percentage (%)')

    @api.constrains('days_from', 'days_to')
    def _check_days(self):
        for record in self:
            if record.days_from <= 0:
                raise ValidationError(_("The 'From (Days)' field must be greater than 0."))
            if record.days_to != 0 and record.days_to < record.days_from:
                raise ValidationError(_("The 'To (Days)' field must be greater than or equal to 'From (Days)', or 0 for infinity."))
