# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_quality_check = fields.Boolean(default=False, copy=False)
    is_quality_check_created = fields.Boolean(default=False, copy=False)
    quality_control_point_ids = fields.Many2many('quality.control.point', copy=False)
    quality_check_ids = fields.Many2many('quality.check', copy=False)
    qc_count = fields.Integer(compute='_compute_quality_checks', copy=False)

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
                if point.product_category_ids.filtered(lambda c: c.id == all_category_id.id):
                    self.is_quality_check = True
                    quality_control_points.append(point.id)
                elif self.move_ids_without_package.filtered(
                        lambda c: (c.product_id.categ_id.id in point.product_category_ids.ids) or (
                                c.product_id.categ_id.parent_id.id in point.product_category_ids.ids)):
                    self.is_quality_check = True
                    quality_control_points.append(point.id)
            elif point.product_ids and self.move_ids_without_package.filtered(
                    lambda p: p.product_id.id in point.product_ids.ids):
                self.is_quality_check = True
                quality_control_points.append(point.id)
            self.quality_control_point_ids = [fields.Command.link(point_id) for point_id in quality_control_points]
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
        quality_check.quality_check_line_ids = [fields.Command.create({
            'quality_control_id': quality_check.quality_control_id.id,
            'inspection_action_id': action.inspection_action_id.id,
            'inspection_type_id': action.inspection_type_id.id,
            'instruction': action.instruction,
            'value': action.value,
        }) for action in qcp.quality_inspection_ids]
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
                    products_list = self.move_ids_without_package.mapped('product_id').ids
                elif qcp.product_category_ids:
                    all_category_id = self.env.ref('product.product_category_all').id
                    if qcp.product_category_ids.filtered(lambda c: c.id == all_category_id):
                        products_list = self.move_ids_without_package.mapped('product_id').ids
                    product_in_move = self.move_ids_without_package.filtered(
                        lambda c: (c.product_id.categ_id.id in qcp.product_category_ids.ids) or (
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
                            quality_check = self.create_quality_checks(move, qcp)
                            qc_ids.append(quality_check.id)
            self.quality_check_ids = [fields.Command.link(qc) for qc in qc_ids]
            self.is_quality_check_created = True

    @api.depends('quality_check_ids')
    def _compute_quality_checks(self):
        for qc in self:
            qc.qc_count = len(qc.quality_check_ids)

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
