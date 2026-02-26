# -*- coding: utf-8 -*-
from odoo import api, fields, models


class QualityAlert(models.Model):
    _name = 'quality.alert'
    _description = 'Quality Alerts'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='', readonly=True)
    quality_check_id = fields.Many2one('quality.check')
    quality_check_line_id = fields.Many2one('quality.check.line')
    product_id = fields.Many2one('product.product')
    product_template_id = fields.Many2one('product.template', string='Variants')
    picking_id = fields.Many2one('stock.picking')
    stock_lot_id = fields.Many2one('stock.lot', string='Lot')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    quality_team_id = fields.Many2one('quality.team', string='Team')
    description = fields.Html()
    corrective_action = fields.Html()
    preventive_action = fields.Html()
    stage_id = fields.Many2one('quality.alert.stage', group_expand='read_group_stage_ids',
                               default=lambda self: self.env.ref('cyllo_quality.quality_alert_stage_quarantine').id)
    date = fields.Date(default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')])
    color = fields.Integer(string='Color Index')

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('name', '') == '':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'quality.alert') or ''
        return super(QualityAlert, self).create(vals)

    @api.model
    def read_group_stage_ids(self, stage_id, domain, order):
        return self.env['quality.alert.stage'].search([])

