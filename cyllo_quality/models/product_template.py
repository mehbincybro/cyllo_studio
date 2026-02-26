from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qcp_count = fields.Integer(compute='_compute_quality_control_points')
    quality_control_point_ids = fields.Many2many('quality.control.point', compute='_compute_quality_control_points')

    def _compute_quality_control_points(self):
        for product in self:
            all_category_id = self.env.ref('product.product_category_all').id
            quality_control_points = self.env['quality.control.point'].search(
                ['|', '|', '|', ('product_ids', 'in', product.product_variant_id.id),
                 ('product_ids', 'in', product.product_variant_id.categ_id.id),
                 ('product_category_ids', 'in', product.product_variant_id.categ_id.parent_id.id),
                 ('product_category_ids', '=', all_category_id)])
            product.qcp_count = len(quality_control_points)
            product.quality_control_point_ids = [fields.Command.link(qc.id) for qc in quality_control_points]

    def action_view_quality_points(self):
        return {
            'name': 'Quality Control Points',
            'view_mode': 'tree,form',
            'res_model': 'quality.control.point',
            'domain': [('id', 'in', self.quality_control_point_ids.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
