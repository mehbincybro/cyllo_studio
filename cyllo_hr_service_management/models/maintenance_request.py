# -*- coding: utf-8 -*-
from odoo import fields, models


class MaintenanceRequest(models.Model):
    """Inherited model for extending maintenance requests."""
    _inherit = 'maintenance.request'

    service_id = fields.Many2one('hr.service', help="Related service linked to the maintenance request.")
