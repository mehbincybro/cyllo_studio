# -*- coding: utf-8 -*-
from odoo import fields, models, api


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    control_type = fields.Selection(selection_add=[('asset', 'Asset')], ondelete={'asset': 'cascade'})
    asset_operation_type = fields.Selection([
        ('lease', 'Lease'),
        ('rent', 'Rent')
    ], string="Operation Type", tracking=True)
    asset_id = fields.Many2one('asset.asset', string="Asset", tracking=True)
    asset_rental_id = fields.Many2one('asset.rental', string="Rental", tracking=True)
    asset_lease_id = fields.Many2one('asset.lease', string="Lease", tracking=True)
    # partner_id = fields.Many2one('res.partner', string="Customer", compute='_compute_partner_id', store=True)

    # @api.depends('asset_rental_id', 'asset_lease_id')
    # def _compute_partner_id(self):
    #     for rec in self:
    #         if rec.asset_rental_id:
    #             rec.partner_id = rec.asset_rental_id.customer_id
    #         elif rec.asset_lease_id:
    #             rec.partner_id = rec.asset_lease_id.customer_id
    #         else:
    #             rec.partner_id = False

    def write(self, vals):
        if 'status' in vals or any(line.status for line in self.quality_check_line_ids):
             pass # Will be handled by return logic, but might be useful for manual changes
        return super().write(vals)

