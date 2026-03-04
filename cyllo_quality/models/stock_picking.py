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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_quality_check = fields.Boolean(default=False, copy=False)
    is_quality_check_created = fields.Boolean(default=False, copy=False)
    quality_control_point_ids = fields.Many2many('quality.control.point',
                                                 copy=False)
    quality_check_ids = fields.Many2many('quality.check', copy=False)
    qc_count = fields.Integer(compute='_compute_quality_checks', copy=False)
    qc_checked_count = fields.Integer(compute='_compute_quality_checks', copy=False)

    def action_confirm(self):
        quality_points = self.env['quality.control.point'].search(
            [('operation_type_ids', 'in', self.picking_type_id.id)])
        quality_control_points = []
        for point in quality_points:
            if not point.product_category_ids and not point.product_ids:
                self.is_quality_check = True
                quality_control_points.append(point.id)
            elif point.product_category_ids:
                all_category_id = self.env.ref('product.product_category_all')
                if point.product_category_ids.filtered(
                        lambda c: c.id == all_category_id.id):
                    self.is_quality_check = True
                    quality_control_points.append(point.id)
                elif self.move_ids_without_package.filtered(
                        lambda c: (
                                          c.product_id.categ_id.id in point.product_category_ids.ids) or (
                                          c.product_id.categ_id.parent_id.id in point.product_category_ids.ids)):
                    self.is_quality_check = True
                    quality_control_points.append(point.id)
            elif point.product_ids and self.move_ids_without_package.filtered(
                    lambda p: p.product_id.id in point.product_ids.ids):
                self.is_quality_check = True
                quality_control_points.append(point.id)
            self.quality_control_point_ids = [fields.Command.link(point_id) for
                                              point_id in
                                              quality_control_points]
        return super(StockPicking, self).action_confirm()

    def create_quality_checks(self, move, qcp):
        uom = False
        if move:
            if qcp.control_type == 'quantity':
                qty = (move.quantity * qcp.control_quantity) / 100
                uom = move.product_uom.id
            else:
                qty = move.quantity
        else:
            qty = 0
        quality_check = self.env['quality.check'].create({
            'name': self.name,
            'quality_control_id': qcp.id,
            'product_id': move.product_id.id if move else False,
            'picking_id': self.id,
            'control_type': qcp.control_type,
            'quantity': qty,
        })
        return quality_check

    def action_quality_check(self):
        if not self.is_quality_check_created:
            quality_controls = {}
            qc_ids = []
            move = False
            for qcp in self.quality_control_point_ids:
                if qcp.id not in quality_controls:
                    quality_controls[qcp.id] = {}
                products_list = []
                if not qcp.product_ids and not qcp.product_category_ids:
                    products_list = self.move_ids_without_package.mapped(
                        'product_id').ids
                elif qcp.product_category_ids:
                    all_category_id = self.env.ref(
                        'product.product_category_all').id
                    if qcp.product_category_ids.filtered(
                            lambda c: c.id == all_category_id):
                        products_list = self.move_ids_without_package.mapped(
                            'product_id').ids
                    product_in_move = self.move_ids_without_package.filtered(
                        lambda c: (
                                              c.product_id.categ_id.id in qcp.product_category_ids.ids) or (
                                          c.product_id.categ_id.parent_id.id in qcp.product_category_ids.ids))
                    if product_in_move:
                        products_list = product_in_move.mapped('product_id').ids
                elif qcp.product_ids:
                    product_in_move = self.move_ids_without_package.filtered(
                        lambda p: p.product_id.id in qcp.product_ids.ids)
                    if product_in_move:
                        products_list = product_in_move.mapped('product_id').ids
                if qcp.control_type == 'operation':
                    quality_check = self.create_quality_checks(move, qcp)
                    qc_ids.append(quality_check.id)
                elif qcp.control_type == 'product' or qcp.control_type == 'quantity':
                    for move_line in self.move_ids_without_package:
                        move = move_line
                        if move.product_id.id in products_list:
                            if move.quantity <= 0:
                                raise UserError(
                                    _("You cannot perform a quality check if the quantity is zero. Please set the product quantity first."))
                            quality_check = self.create_quality_checks(move,
                                                                       qcp)
                            qc_ids.append(quality_check.id)
            self.quality_check_ids = [fields.Command.link(qc) for qc in qc_ids]
            self.is_quality_check_created = True
    @api.depends('quality_check_ids', 'quality_check_ids.quality_check_line_ids.is_checked', 'quality_control_point_ids')
    def _compute_quality_checks(self):
        for picking in self:
            if picking.quality_check_ids:
                all_lines = picking.quality_check_ids.quality_check_line_ids
                picking.qc_count = len(all_lines)
                picking.qc_checked_count = len(all_lines.filtered('is_checked'))
            else:
                # Potential count display
                count = 0
                for qcp in picking.quality_control_point_ids:
                    num_actions = len(qcp.quality_inspection_ids)
                    if qcp.control_type == 'operation':
                        count += num_actions
                    else:
                        # product or quantity - count moves matching qcp
                        products_ids = qcp.product_ids.ids
                        products_list = []
                        if not qcp.product_ids and not qcp.product_category_ids:
                            products_list = picking.move_ids_without_package.mapped('product_id').ids
                        elif qcp.product_category_ids:
                            all_category_id = self.env.ref('product.product_category_all').id
                            product_in_move = picking.move_ids_without_package.filtered(
                                lambda c: (c.product_id.categ_id.id in qcp.product_category_ids.ids) or
                                          (c.product_id.categ_id.parent_id.id in qcp.product_category_ids.ids) or 
                                          (all_category_id in qcp.product_category_ids.ids))
                            products_list = product_in_move.mapped('product_id').ids
                        elif qcp.product_ids:
                            product_in_move = picking.move_ids_without_package.filtered(
                                lambda p: p.product_id.id in products_ids)
                            products_list = product_in_move.mapped('product_id').ids
                        
                        count += len(products_list) * num_actions
                picking.qc_count = count
                picking.qc_checked_count = 0

            if picking.qc_count > 0 and picking.qc_count == picking.qc_checked_count:
                picking.is_quality_check = False

    def action_view_quality_check(self):
        return {
            'name': 'Quality Checks',
            'view_mode': 'tree,form',
            'res_model': 'quality.check',
            'domain': [('id', 'in', self.quality_check_ids.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def button_validate(self):
        if self.quality_control_point_ids and not self.quality_check_ids:
            raise UserError(_("You need to done the quality check"))
        return super().button_validate()
