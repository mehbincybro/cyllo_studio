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


class FieldServiceTemplate(models.Model):
    """In this class we are defining the fields required for  the model
    field.service.template"""
    _name = "field.service.template"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Field Service Template"

    name = fields.Char(required=True, tracking=True, help="Name of checklist")
    description = fields.Text(tracking=True,
                              help="Description about the checklist")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company,
                                 help="Current company name")
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id,
                                  help="Currency of company")
    service_checklist_ids = fields.One2many("field.service.template.line",
                                            'field_service_template_id',
                                            string="Service Checklists",
                                            help="Service request checklists ")
