# -*- coding: utf-8 -*-
from odoo import fields, models


class QualityControlPoint(models.Model):
    _inherit = 'quality.control.point'

    qc_check_for = fields.Selection(selection_add=[('asset', 'Asset')], ondelete={'asset': 'cascade'})
    asset_id = fields.Many2one('asset.asset', string="Asset")
    asset_operation_type = fields.Selection([
        ('lease', 'Lease'),
        ('rent', 'Rent'),
        ('both', 'Both')
    ], string="Asset Operation Type")
    operation_type_ids = fields.Many2many(required=False)
