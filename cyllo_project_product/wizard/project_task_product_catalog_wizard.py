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


class ProjectTaskProductCatalogWizard(models.TransientModel):
    _name = 'project.task.product.catalog.wizard'
    _description = 'Choose Sale Order for Task Products'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        compute='_compute_partner_id',
        readonly=True,
    )
    action_type = fields.Selection(
        [
            ('quotation', 'Add to Existing Quotation'),
            ('sale_order', 'Add to Existing Sales Order'),
            ('new_quotation', 'Create New Quotation'),
            ('new_sale_order', 'Create New Sales Order'),
        ],
        string='Product Destination',
        required=True,
        default='quotation',
    )
    limited_action_type = fields.Selection(
        [
            ('quotation', 'Add to Existing Quotation'),
            ('sale_order', 'Add to Existing Sales Order'),
            ('new_quotation', 'Create New Quotation'),
        ],
        string='Product Destination',
        default='quotation',
    )
    available_sale_order_ids = fields.Many2many(
        'sale.order',
        string='Available Quotations / Sales Orders',
        compute='_compute_available_sale_order_ids',
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Quotation / Sales Order',
        domain="[('id', 'in', available_sale_order_ids)]",
    )
    can_create_sale_order = fields.Boolean(
        compute='_compute_can_create_sale_order',
    )

    @api.depends('task_id.partner_id', 'task_id.project_id.partner_id')
    def _compute_partner_id(self):
        for wizard in self:
            wizard.partner_id = wizard.task_id.partner_id or wizard.task_id.project_id.partner_id

    @api.depends('task_id.sale_order_id', 'task_id.product_sale_order_id')
    def _compute_can_create_sale_order(self):
        for wizard in self:
            wizard.can_create_sale_order = not (wizard.task_id.sale_order_id or wizard.task_id.product_sale_order_id)

    @api.depends('task_id', 'action_type')
    def _compute_available_sale_order_ids(self):
        for wizard in self:
            wizard.available_sale_order_ids = wizard.task_id._get_product_catalog_orders_by_type(wizard.action_type)

    @api.onchange('action_type', 'available_sale_order_ids')
    def _onchange_action_type(self):
        if self.action_type != 'new_sale_order':
            self.limited_action_type = self.action_type
        self.sale_order_id = False
        if self.action_type in ('quotation', 'sale_order') and self.available_sale_order_ids:
            self.sale_order_id = self.available_sale_order_ids[:1]

    @api.onchange('limited_action_type')
    def _onchange_limited_action_type(self):
        if self.limited_action_type:
            self.action_type = self.limited_action_type

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        task = self.env['project.task'].browse(self.env.context.get('default_task_id'))
        if task:
            values['task_id'] = task.id
            quotation_orders = task._get_product_catalog_orders_by_type('quotation')
            sale_orders = task._get_product_catalog_orders_by_type('sale_order')
            if quotation_orders:
                values['sale_order_id'] = quotation_orders[:1].id
                values['action_type'] = 'quotation'
            elif sale_orders:
                values['sale_order_id'] = sale_orders[:1].id
                values['action_type'] = 'sale_order'
            elif task.sale_order_id or task.product_sale_order_id:
                values['action_type'] = 'new_quotation'
                values['limited_action_type'] = 'new_quotation'
            else:
                values['action_type'] = 'new_sale_order'
            if values.get('action_type') != 'new_sale_order':
                values['limited_action_type'] = values['action_type']
        return values

    def action_open_product_catalog(self):
        self.ensure_one()
        task = self.task_id
        partner = task.partner_id or task.project_id.partner_id
        if not partner:
            raise UserError(_("Please set a Customer on the task or project before adding products."))

        if self.action_type == 'new_sale_order' and (task.sale_order_id or task.product_sale_order_id):
            raise UserError(_("A Sales Order already exists for this task. Please use Add to Existing Sales Order."))

        if self.action_type in ('quotation', 'sale_order'):
            sale_order = self.sale_order_id
            if not sale_order:
                raise UserError(_("Please select an existing Quotation or Sales Order, or choose a create option."))
            if sale_order.state == 'cancel':
                raise UserError(_("You cannot add products to a cancelled Sales Order."))
        else:
            sale_order_values = task._get_product_catalog_sale_order_values(partner)
            if self.action_type == 'new_quotation':
                sale_order_values['is_task_extra_quotation'] = True
            sale_order = self.env['sale.order'].create(sale_order_values)

        if self.action_type in ('sale_order', 'new_sale_order') and not task.product_sale_order_id:
            task.product_sale_order_id = sale_order.id

        return sale_order.with_context(
            {},
            order_id=sale_order.id,
            default_project_task_product_id=task.id,
        ).action_add_from_catalog()
