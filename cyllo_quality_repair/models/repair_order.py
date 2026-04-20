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
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    is_quality_check = fields.Boolean(compute='_compute_quality_checks', store=True, copy=False)
    is_quality_check_created = fields.Boolean(default=False, copy=False)
    quality_control_point_ids = fields.Many2many('quality.control.point', copy=False)
    quality_check_ids = fields.Many2many('quality.check', copy=False)
    qc_count = fields.Integer(compute='_compute_quality_checks', copy=False)
    qc_checked_count = fields.Integer(compute='_compute_quality_checks', copy=False)

    def action_validate(self):
        quality_points = self.env['quality.control.point'].search(
            [('operation_type_ids', 'in', self.picking_type_id.id)])
        quality_control_points = []
        for point in quality_points:
            if not point.product_category_ids and not point.product_ids:
                quality_control_points.append(point.id)
            elif point.product_category_ids:
                all_category_id = self.env.ref('product.product_category_all')
                if point.product_category_ids.filtered(lambda c: c.id == all_category_id.id):
                    quality_control_points.append(point.id)
                elif self.product_id.categ_id.id in point.product_category_ids.ids or self.product_id.categ_id.parent_id.id in point.product_category_ids.ids:
                    quality_control_points.append(point.id)
            elif point.product_ids and self.product_id.id in point.product_ids.ids:
                quality_control_points.append(point.id)
        self.quality_control_point_ids = [fields.Command.link(point_id) for point_id in quality_control_points]
        return super(RepairOrder, self).action_validate()

    def action_quality_check(self):
        if self.product_qty == 0:
            raise UserError(
                _("You cannot perform a quality check if the quantity is zero."))
        if not self.is_quality_check_created:
            qc_ids = []
            for qcp in self.quality_control_point_ids:
                qcp_product = False
                if not qcp.product_ids and not qcp.product_category_ids:
                    qcp_product = self.product_id.id
                elif qcp.product_category_ids:
                    all_category_id = self.env.ref('product.product_category_all').id
                    if qcp.product_category_ids.filtered(lambda c: c.id == all_category_id):
                        qcp_product = self.product_id.id
                    elif self.product_id.categ_id.id in qcp.product_category_ids.ids or self.product_id.categ_id.parent_id.id in qcp.product_category_ids.ids:
                        qcp_product = self.product_id.id
                elif qcp.product_ids and self.product_id.id in qcp.product_ids.ids:
                    qcp_product = self.product_id.id
                
                if self.product_id.id == qcp_product:
                    if qcp.control_type == 'quantity':
                        qty = (self.product_qty * qcp.control_quantity) / 100
                    else:
                        qty = self.product_qty
                    quality_check = self.env['quality.check'].create({
                        'name': self.name,
                        'quality_control_id': qcp.id,
                        'product_id': self.product_id.id,
                        'repair_id': self.id,
                        'control_type': qcp.control_type,
                        'quantity': qty,
                        'uom_id': self.product_uom.id
                    })
                    qc_ids.append(quality_check.id)
            if not qc_ids:
                raise UserError(_("No Quality Checks could be generated. Please verify your Quality Control Point configuration (Operations, Products, and Categories)."))
            self.quality_check_ids = [fields.Command.link(qc) for qc in qc_ids]
            self.is_quality_check_created = True
        return self.action_view_quality_check()

    @api.depends('quality_check_ids', 'quality_check_ids.quality_check_line_ids.is_checked', 'quality_control_point_ids')
    def _compute_quality_checks(self):
        for repair in self:
            if repair.quality_check_ids:
                all_lines = repair.quality_check_ids.quality_check_line_ids
                repair.qc_count = len(all_lines)
                repair.qc_checked_count = len(all_lines.filtered('is_checked'))
            else:
                count = sum(len(qcp.quality_inspection_ids) for qcp in repair.quality_control_point_ids)
                repair.qc_count = count
                repair.qc_checked_count = 0

            if repair.quality_control_point_ids:
                repair.is_quality_check = (repair.qc_count == 0 or repair.qc_count != repair.qc_checked_count)
            else:
                repair.is_quality_check = False

    def action_view_quality_check(self):
        return {
            'name': 'Quality Checks',
            'view_mode': 'tree,form',
            'res_model': 'quality.check',
            'domain': [('id', 'in', self.quality_check_ids.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_repair_end(self):
        if self.is_quality_check:
            pending = self.qc_count - self.qc_checked_count
            if pending > 0:
                raise UserError(_("You must complete %s pending quality checks before ending the repair.") % pending)
            else:
                raise UserError(_("You must generate and complete quality checks before ending the repair."))
        return super(RepairOrder, self).action_repair_end()
