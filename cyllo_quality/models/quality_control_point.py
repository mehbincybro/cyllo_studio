# -*- coding: utf-8 -*-
from odoo import api, fields, models


class QualityControlPoint(models.Model):
    _name = 'quality.control.point'
    _description = 'Quality Control Points'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='', readonly=True, tracking=True)
    operation_type_ids = fields.Many2many('stock.picking.type', string='Operations', tracking=True, required=True)
    product_category_ids = fields.Many2many('product.category', string='Product Categories', tracking=True)
    product_ids = fields.Many2many('product.product', string='Products', tracking=True)
    qc_check_for = fields.Selection([('product', 'Products'), ('category', 'Category')], string='Quality Check For',
                                    default='')
    user_id = fields.Many2one('res.users', string='Responsible', compute="_compute_user_id", store=True, readonly=False, default=lambda self: self.env.user)
    quality_team_id = fields.Many2one('quality.team', string='Team', tracking=True)
    quality_inspection_ids = fields.One2many('quality.inspection', 'quality_control_id', string='Inspection')
    active = fields.Boolean(default=True, tracking=True, copy=False)
    control_type = fields.Selection([
        ('operation', 'Operation'),
        ('product', 'Product'),
        ('quantity', 'Quantity')
    ], default='operation', required=True, tracking=True)
    control_by = fields.Selection([
        ('all', 'All'),
        ('randomly', 'Randomly'),
        ('periodically', 'Periodically')
    ], default='all', required=True, tracking=True)
    control_frequency = fields.Integer(string='Control Frequency')
    control_period = fields.Selection([('day', 'Day'), ('week', 'Week'), ('month', 'Month')], default='day')
    control_quantity = fields.Integer()

    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, tracking=True)
    qc_check_count = fields.Integer(compute='_compute_quality_checks')
    failure_location_id = fields.Many2one('stock.location', string='Failure Location')

    @api.model
    def create(self, vals):
        """Override create to add reference and send notification"""
        if vals.get('name', '') == '':
            vals['name'] = self.env['ir.sequence'].next_by_code('quality.control.point') or ''

        # Create the record
        result = super(QualityControlPoint, self).create(vals)

        # Send notification email if quality team is assigned
        if vals.get('quality_team_id'):
            if result.quality_team_id.is_mail:
                template = self.env.ref('cyllo_quality.mail_template_quality_control_notification')
                if template:
                    # Prepare context for email template
                    ctx = {
                        'team_leader': result.quality_team_id.leader_id.name,
                        'name': result.name,
                        'control_type': dict(self._fields['control_type'].selection).get(result.control_type),
                        'team': result.quality_team_id.name,
                        'control_by': dict(self._fields['control_by'].selection).get(result.control_by),
                        'operations': ', '.join(result.operation_type_ids.mapped('name')),

                    }

                    # Add conditional fields
                    if result.control_frequency:
                        ctx.update({
                            'frequency': result.control_frequency,
                            'period': dict(self._fields['control_period'].selection).get(result.control_period)
                        })

                    if result.qc_check_for == 'product':
                        ctx.update({'products': ', '.join(result.product_ids.mapped('name'))})
                    elif result.qc_check_for == 'category':
                        ctx.update({'categories': ', '.join(result.product_category_ids.mapped('name'))})

                    # Send mail with context
                    template.with_context(ctx).send_mail(result.id, force_send=True)

        return result



    @api.depends('quality_team_id')
    def _compute_user_id(self):
        for qcp in self:
            if qcp.quality_team_id.leader_id.user_id:
                qcp.user_id = qcp.quality_team_id.leader_id.user_id.id
            elif not qcp.user_id:
                qcp.user_id = self.env.user


    def _compute_quality_checks(self):
        """Compute quality checks count"""
        for qcp in self:
            qcp.qc_check_count = self.env['quality.check'].search_count([('quality_control_id', '=', qcp.id)])



    def action_view_quality_checks(self):
        """Action view quality checks"""
        quality_check = self.env['quality.check'].search([('quality_control_id', '=', self.id)])
        return {
            'name': 'Quality Checks',
            'view_mode': 'tree,form',
            'res_model': 'quality.check',
            'domain': [('id', 'in', quality_check.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }





