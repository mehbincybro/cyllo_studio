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
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsurancePlanCoverage(models.Model):
    _name = 'insurance.plan.coverage'
    _description = 'Insurance Plan Coverage'

    plan_id = fields.Many2one('insurance.plan', required=True, ondelete='cascade')
    coverage_id = fields.Many2one('insurance.coverage', required=True)
    coverage_amount = fields.Monetary(required=True)
    # deductible = fields.Monetary(default=0)
    coverage_type = fields.Selection(selection=[('covered', 'Covered'), ('addons', 'Addons')],
                                     default='covered', required=True)
    currency_id = fields.Many2one(related='plan_id.currency_id', store=True)

    @api.constrains('plan_id', 'coverage_id')
    def _check_duplicate_coverage(self):
        for rec in self:
            if not rec.plan_id or not rec.coverage_id:
                continue

            duplicates = self.search([
                ('plan_id', '=', rec.plan_id.id),
                ('coverage_id', '=', rec.coverage_id.id),
                ('id', '!=', rec.id)
            ])

            if duplicates:
                raise ValidationError(
                    "This coverage is already added to this plan."
                )


