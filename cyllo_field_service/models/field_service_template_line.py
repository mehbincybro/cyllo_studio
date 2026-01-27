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


class FieldServiceTemplateLine(models.Model):
    """In this class we are defining the fields required for the model
    field.service.template.line
    """
    _name = "field.service.template.line"
    _description = "Field Service Checklist Line"

    product_id = fields.Many2one("product.product", required=True,
                                 help="Name of checklist",
                                 domain=[('detailed_type', '=', 'service')])
    required = fields.Boolean(help="Boolean to specify whether this checklist compulsory  or not")
    time_required = fields.Float(string="Required Time",
                                 help="Time required to complete the task")
    field_service_template_id = fields.Many2one('field.service.template',
                                                string="Service Request Template",
                                                help="Service request template")
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)
    service_cost = fields.Monetary(currency_field='currency_id', default=0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Updates the service cost based on the selected product's list price.

            This method is triggered automatically when the `product_id` field is changed.
            It updates the `service_cost` field with the `lst_price` (list price) of the selected product.
        """
        for rec in self:
            rec.service_cost = rec.product_id.lst_price
