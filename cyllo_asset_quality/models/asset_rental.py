# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AssetRental(models.Model):
    _inherit = 'asset.rental'

    quality_check_ids = fields.One2many(
        'quality.check',
        compute='_compute_quality_check_ids',
        string="Quality Checks"
    )
    quality_check_done = fields.Boolean(
        compute='_compute_quality_check_done',
        string="Quality Check Done"
    )

    def _compute_quality_check_ids(self):
        for rec in self:
            rec.quality_check_ids = self.env['quality.check'].search([
                ('asset_rental_id', '=', rec.id)
            ])

    @api.depends('quality_check_ids', 'quality_check_ids.quality_check_line_ids.is_checked', 'status')
    def _compute_quality_check_done(self):
        for rec in self:
            if rec.status != 'rent':
                rec.quality_check_done = True
                continue
                
            control_point = self.env['quality.control.point'].search([
                ('qc_check_for', '=', 'asset'),
                ('asset_id', '=', rec.asset_id.id),
                ('asset_operation_type', 'in', ['rent', 'both'])
            ], limit=1)
            
            if not control_point:
                rec.quality_check_done = True
                continue

            quality_checks = rec.quality_check_ids
            if not quality_checks:
                rec.quality_check_done = False
                continue
                
            qc = quality_checks[0]
            if qc.quality_check_line_ids and all(line.is_checked for line in qc.quality_check_line_ids):
                rec.quality_check_done = True
            elif not qc.quality_check_line_ids:
                 rec.quality_check_done = True
            else:
                rec.quality_check_done = False

    def action_validate_quality(self):
        """Creates or opens the quality check for this rental return."""
        self.ensure_one()
        if self.status != 'rent':
            raise UserError(_("You can only validate quality for active rentals."))

        # Search for existing active QC
        qc = self.env['quality.check'].search([
            ('asset_rental_id', '=', self.id)
        ], limit=1)

        # Create one if it doesn't exist
        if not qc:
            control_point = self.env['quality.control.point'].search([
                ('qc_check_for', '=', 'asset'),
                ('asset_id', '=', self.asset_id.id),
                ('asset_operation_type', 'in', ['rent', 'both'])
            ], limit=1) 

            if not control_point:
                 raise UserError(_("No Quality Control Point defined for this Asset and Rent operation."))

            qc = self.env['quality.check'].create({
                'name': f"Rented for '{self.customer_id.name}'" if self.customer_id else 'Rental Check',
                'quality_control_id': control_point.id,
                'control_type': 'asset',
                'asset_operation_type': 'rent',
                'asset_id': self.asset_id.id,
                'asset_rental_id': self.id,
                'user_id': self.env.user.id,
            })

        return {
            'name': _('Quality Check'),
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('asset_rental_id', '=', self.id)],
            'context': {
                'default_asset_rental_id': self.id,
                'default_asset_id': self.asset_id.id,
                'default_asset_operation_type': 'rent',
                'default_control_type': 'asset',
            },
        }

    def action_return_asset(self):
        res = super().action_return_asset()

        for rec in self:
             qc = self.env['quality.check'].search([
                 ('asset_rental_id', '=', rec.id)
             ], limit=1)

             if qc:
                 failed_lines = qc.quality_check_line_ids.filtered(lambda l: l.status == 'fail')
                 if failed_lines:
                     # Create repair request
                     self.env['maintenance.request'].create({
                         'name': f"Repair Request for {rec.asset_id.name} (Rental Return)",
                         'asset_id': rec.asset_id.id,
                         'maintenance_type': 'corrective',
                         'user_id': self.env.user.id,
                         'description': "\n".join([f"Quality Check Failed: {qc.name}"] + [f"- {l.inspection_type_id.name}" for l in failed_lines]),
                     })
                     rec.asset_id.is_repair = True
                     # Note: Removed rec.asset_id.status = 'repair' as that status doesn't exist

        return res
