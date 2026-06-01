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
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProjectTask(models.Model):
    _inherit = 'project.task'

    product_line_ids = fields.One2many(
        'sale.order.line', 'project_task_product_id', 
        string='Products'
    )
    products_count = fields.Integer(
        compute='_compute_products_count', 
        string='Products Count'
    )
    products_amount = fields.Monetary(
        compute='_compute_products_amount', 
        string='Products Amount',
        currency_field='currency_id'
    )
    product_sale_order_id = fields.Many2one('sale.order', string="Product Sales Order", copy=False)
    currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_product_currency_id',
        string='Currency'
    )
    allow_task_products = fields.Boolean(
        related='project_id.allow_task_products'
    )
    allow_extra_quotations = fields.Boolean(
        related='project_id.allow_extra_quotations'
    )
    extra_quotation_ids = fields.One2many(
        'sale.order', 'task_id',
        string="Extra Quotations",
        domain=[('is_task_extra_quotation', '=', True)],
    )
    extra_quotation_count = fields.Integer(
        compute='_compute_extra_quotation_count',
        string="Quotation Count",
    )
    display_sale_order_button = fields.Boolean(
        compute='_compute_display_sale_order_button'
    )

    @api.depends('sale_order_id', 'product_sale_order_id')
    def _compute_display_sale_order_button(self):
        for task in self:
            task.display_sale_order_button = bool(task.sale_order_id or task.product_sale_order_id)

    @api.depends('sale_order_id.currency_id', 'product_sale_order_id.currency_id', 'project_id.currency_id')
    def _compute_product_currency_id(self):
        for task in self:
            task.currency_id = task.sale_order_id.currency_id or task.product_sale_order_id.currency_id or task.project_id.currency_id or task.company_id.currency_id

    @api.depends('product_line_ids')
    def _compute_products_count(self):
        for task in self:
            task.products_count = len(task.product_line_ids)

    @api.depends('product_line_ids.price_subtotal')
    def _compute_products_amount(self):
        for task in self:
            task.products_amount = sum(task.product_line_ids.mapped('price_subtotal'))

    @api.depends('extra_quotation_ids')
    def _compute_extra_quotation_count(self):
        for task in self:
            task.extra_quotation_count = len(task._get_task_extra_quotations())

    def action_view_task_products(self):
        self.ensure_one()
        return {
            'name': _('Add Products to Quotation / Sales Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.product.catalog.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
            },
        }

    def _get_product_catalog_sale_orders(self):
        self.ensure_one()
        return (self.sale_order_id | self.product_sale_order_id | self._get_task_extra_quotations()).filtered(
            lambda order: order.state != 'cancel'
        )

    def _get_product_catalog_orders_by_type(self, order_type):
        self.ensure_one()
        if order_type == 'quotation':
            return self._get_task_extra_quotations().filtered(lambda order: order.state in ('draft', 'sent'))
        if order_type == 'sale_order':
            return (self.sale_order_id | self.product_sale_order_id).filtered(
                lambda order: order.state != 'cancel'
            )
        return self.env['sale.order']

    def _get_task_extra_quotations(self):
        self.ensure_one()
        return self.env['sale.order'].search([
            ('task_id', '=', self.id),
            ('is_task_extra_quotation', '=', True),
        ])

    def _get_product_catalog_sale_order_values(self, partner):
        self.ensure_one()
        return {
            'partner_id': partner.id,
            'task_id': self.id,
            'analytic_account_id': self.project_id.analytic_account_id.id if self.project_id.analytic_account_id else False,
        }

    def action_view_task_sale_order(self):
        self.ensure_one()
        sale_order = self.sale_order_id or self.product_sale_order_id
        if not sale_order:
            return {'type': 'ir.actions.act_window_close'}
        
        return {
            'name': _('Sales Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'views': [[False, 'form']],
            'view_mode': 'form',
            'res_id': sale_order.id,
        }

    def action_task_new_quotation(self):
        self.ensure_one()
        partner = self.partner_id or self.project_id.partner_id
        if not partner:
            raise UserError(_("Please set a Customer on the task or project before creating a quotation."))

        sale_order = self.env['sale.order'].create({
            **self._get_product_catalog_sale_order_values(partner),
            'is_task_extra_quotation': True,
        })

        return {
            'name': _('Sales Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
        }

    def action_view_extra_quotations(self):
        self.ensure_one()
        quotations = self._get_task_extra_quotations()
        action = {
            'name': _('Quotations'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', quotations.ids)],
            'context': {
                'default_partner_id': (self.partner_id or self.project_id.partner_id).id,
                'default_task_id': self.id,
            },
        }
        if len(quotations) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = quotations.id
        return action
