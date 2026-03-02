# -*- coding: utf-8 -*-
from odoo import api, fields, models


class QualityCheck(models.Model):
    _name = 'quality.check'
    _description = 'Quality Check'
    _rec_name = 'reference'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    reference = fields.Char(default='', readonly=True, tracking=True)
    name = fields.Char(tracking=True)
    quality_control_id = fields.Many2one('quality.control.point', string='Quality Control Point', tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible', related='quality_control_id.user_id', tracking=True, store=True, readonly=False, default=lambda self: self.env.user)
    quality_team_id = fields.Many2one('quality.team', string='Team', tracking=True)
    qc_alert_count = fields.Integer(compute='_compute_qc_alert')
    mo_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    picking_id = fields.Many2one('stock.picking', string='Picking')
    control_type = fields.Selection([
        ('operation', 'Operation'),
        ('product', 'Product'),
        ('quantity', 'Quantity')
    ], default='product', required=True, tracking=True)
    quantity = fields.Integer(string='Quantity')
    uom_id = fields.Many2one('uom.uom', readonly=True)
    product_ids = fields.Many2many('product.product', compute='_compute_products', store=True)
    product_id = fields.Many2one('product.product', domain="[('id', 'in', product_ids)]")
    quality_check_line_ids = fields.One2many('quality.check.line', 'quality_check_id', store=True,
                                             compute='_compute_quality_check_line_ids')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, tracking=True)
    active = fields.Boolean(default=True, tracking=True, copy=False)

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', '') == '':
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'quality.check') or ''
        return super(QualityCheck, self).create(vals)

    @api.depends('quality_control_id')
    def _compute_products(self):
        for record in self:
            record.product_ids = record.quality_control_id.product_ids.ids

    @api.depends('quality_control_id')
    def _compute_quality_check_line_ids(self):
        for record in self:
            for qc in record.quality_control_id.quality_inspection_ids:
                print(qc.value,qc, qc.value)
            record.quality_check_line_ids = [fields.Command.clear()]
            record.quality_check_line_ids = [fields.Command.create({
                'quality_check_id': record.id,
                'quality_inspection_id': qc.id,
                'quality_control_id': qc.quality_control_id.id,
                'inspection_action_id': qc.inspection_action_id.id,
                'inspection_type_id': qc.inspection_type_id.id,
                'instruction': qc.instruction,
                'unit_value': {
                    "unit": {
                        "id": qc.value['unit'].get('id'),
                        "name": qc.value['unit'].get('name')
                    },
                    "value": qc.value.get('value')
                },
            }) for qc in record.quality_control_id.quality_inspection_ids]

    def _compute_qc_alert(self):
        for qc in self:
            qc.qc_alert_count = self.env['quality.alert'].search_count([('quality_check_id', '=', qc.id)])

    def action_view_quality_alert(self):
        quality_alert = self.env['quality.alert'].search([('quality_check_id', '=', self.id)])
        return {
            'name': 'Quality Checks',
            'view_mode': 'tree,form,kanban',
            'res_model': 'quality.alert',
            'domain': [('id', 'in', quality_alert.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def get_quality_check_actions(self):
        quality_control = self.read(['quality_check_line_ids', 'quality_control_id', 'control_type', 'product_id', 'user_id', 'quality_team_id', 'quantity'])
        for qc_rec in self:
            qc = next((rec for rec in quality_control if rec["id"] == qc_rec.id), None)
            if not qc:
                quality_control.append(qc)
            qc['quality_check_line_ids'] = qc_rec['quality_check_line_ids'].read()
        return quality_control
