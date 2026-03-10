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

    @api.depends(
        'quality_check_ids',
        'quality_check_ids.quality_check_line_ids.is_checked',
        'status',
        'asset_id',
    )
    def _compute_quality_check_done(self):
        for rec in self:
            if rec.status != 'rent':
                rec.quality_check_done = True
                continue

            if not rec.asset_id:
                rec.quality_check_done = False
                continue

            control_point = self.env['quality.control.point'].search([
                ('qc_check_for', '=', 'asset'),
                ('asset_ids', 'in', rec.asset_id.ids),
                ('asset_operation_type', 'in', ['rent', 'both'])
            ], limit=1)
            if not control_point:
                rec.quality_check_done = False
                continue

            qc = rec.quality_check_ids.filtered(lambda check: rec.asset_id in check.asset_ids)[:1]
            if not qc:
                rec.quality_check_done = False
                continue

            if qc.quality_check_line_ids and all(line.is_checked for line in qc.quality_check_line_ids):
                rec.quality_check_done = True
            elif not qc.quality_check_line_ids:
                rec.quality_check_done = True
            else:
                rec.quality_check_done = False

    def action_validate_quality(self):
        """Creates or opens quality checks for this rental return."""
        self.ensure_one()
        if self.status != 'rent':
            raise UserError(_("You can only validate quality for active rentals."))

        if not self.asset_id:
            raise UserError(_("Please select an asset before validating quality."))

        control_point = self.env['quality.control.point'].search([
            ('qc_check_for', '=', 'asset'),
            ('asset_ids', 'in', self.asset_id.ids),
            ('asset_operation_type', 'in', ['rent', 'both'])
        ], limit=1)
        if not control_point:
            raise UserError(
                _("No Quality Control Point defined for Rent operation on asset: %s")
                % self.asset_id.display_name
            )

        existing_qc = self.env['quality.check'].search([
            ('asset_rental_id', '=', self.id),
            ('asset_ids', 'in', self.asset_id.ids),
        ], limit=1)
        if not existing_qc:
            self.env['quality.check'].create({
                'name': f"Rental Check - {self.asset_id.display_name}",
                'quality_control_id': control_point.id,
                'control_type': 'asset',
                'asset_operation_type': 'rent',
                'asset_ids': [(6, 0, [self.asset_id.id])],
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
                'default_asset_ids': [(6, 0, [self.asset_id.id])],
                'default_asset_operation_type': 'rent',
                'default_control_type': 'asset',
            },
        }

    def action_return_asset(self):
        res = super().action_return_asset()

        for rec in self:
            quality_checks = self.env['quality.check'].search([
                ('asset_rental_id', '=', rec.id),
                ('asset_ids', 'in', rec.asset_id.ids),
            ])

            for qc in quality_checks:
                failed_lines = qc.quality_check_line_ids.filtered(lambda l: l.status == 'fail')
                if not failed_lines:
                    continue

                self.env['maintenance.request'].create({
                    'name': f"Repair Request for {rec.asset_id.name} (Rental Return)",
                    'asset_id': rec.asset_id.id,
                    'maintenance_type': 'corrective',
                    'user_id': self.env.user.id,
                    'description': "\n".join(
                        [f"Quality Check Failed: {qc.name}"] +
                        [f"- {line.inspection_type_id.name}" for line in failed_lines]
                    ),
                })
                rec.asset_id.is_repair = True

        return res
