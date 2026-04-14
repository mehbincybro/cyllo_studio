# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    carbon_line_ids = fields.One2many('mrp.workcenter.carbon', 'operation_id', string='Green Metrics')
