# -*- coding: utf-8 -*-
from odoo import fields, models


class HrServiceCategory(models.Model):
    """Class for managing service categories related to employee services."""
    _name = 'hr.service.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Service Category"

    name = fields.Char(help="Name of the service category.")
    description = fields.Html(help="Detailed description of the service category.")
    parent_id = fields.Many2one('hr.service.category', string="Parent Category",
                                help="Parent category to which this category belongs.")
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company,
                                 help="Company associated with the service category.")
    require_maintenance_order = fields.Boolean(
        string="Create Maintenance Order",
        help="If enabled, service requests with this category will generate a maintenance order.")
