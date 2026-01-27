# -*- coding: utf-8 -*-
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import html_keep_url, is_html_empty

RENTAL_ORDER_STATE = [('draft', "Draft"), ('rented', "Rented"), ('ready_to_return', "Ready to Return"),
                      ('partial_return', "Partially Returned"), ('return', "Returned")]


class RentalOrder(models.Model):
    """ Rental Order """
    _name = 'rental.order'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Rental Order"
    _order = 'date_order desc, id desc'
    _check_company_auto = True

    # === FIELDS === #
    name = fields.Char(string="Order Reference", copy=False, readonly=True, index='trigram',
                       default=lambda self: _('New'), help="Unique reference for the rental order.")
    company_id = fields.Many2one(
        comodel_name='res.company', required=True, index=True, default=lambda self: self.env.company,
        help="The company associated with the rental order.")
    partner_id = fields.Many2one(comodel_name='res.partner', string="Customer", required=True, change_default=True,
                                 index=True, tracking=1, domain="[('company_id', 'in',  (False, company_id))]",
                                 help="The customer for whom the rental order is created.")
    currency_id = fields.Many2one(comodel_name='res.currency', default=lambda self: self.env.company.currency_id,
                                  ondelete='restrict', help="The currency used for the rental order.")
    note = fields.Html(string="Terms and conditions", compute='_compute_note', store=True, readonly=False,
                       precompute=True)
    terms_type = fields.Selection(related='company_id.terms_type')
    state = fields.Selection(selection=RENTAL_ORDER_STATE, string="Status", readonly=True, copy=False, index=True,
                             tracking=3, default='draft', help="The current status of the rental order.")
    date_order = fields.Datetime(string="Date", readonly=True, index=True, default=fields.Datetime.now,
                                 help="The date when the rental order is created.")
    user_id = fields.Many2one('res.users', string='Responsible Person', default=lambda self: self.env.user,
                              help="The salesperson responsible for the rental order.")
    order_line_ids = fields.One2many(comodel_name='rental.order.line', inverse_name='order_id',
                                     string="Rental Order Lines", copy=True, auto_join=True,
                                     help="The rental order lines associated with this order.")
    amount_total = fields.Monetary(string="Total", compute='_compute_amount_total', store=True,
                                   help="The total amount including taxes and additional charges.")
    amount_untaxed = fields.Monetary(string="Untaxed Amount", store=True, compute='_compute_amount_total',
                                     help="The total amount without taxes.")
    amount_tax = fields.Monetary(string="Taxes", store=True, compute='_compute_amount_total',
                                 help="The total tax amount for the rental order.")
    amount_paid = fields.Float(help="The amount already paid for the rental order.")
    partner_shipping_id = fields.Many2one(comodel_name='res.partner', string="Delivery Address", precompute=True,
                                          compute='_compute_partner_shipping_id', store=True, readonly=False,
                                          domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                          help="The address where the rented items will be delivered.")
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string="Invoice Address",
                                         compute='_compute_partner_invoice_id', store=True, readonly=False,
                                         required=True, precompute=True,
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                         help="The address for invoicing the rental order.")
    transaction_ids = fields.Many2many(string="Transactions", comodel_name='payment.transaction',
                                       relation='rental_order_transaction_rel', column1='rental_order_id',
                                       column2='transaction_id', copy=False, readonly=True,
                                       help="The payment transactions associated with the rental order.")
    is_picked_up = fields.Boolean(copy=False, help="Indicates whether the rented items have been picked up.")
    is_returned = fields.Boolean(help="Indicates whether the rented items have been returned.")
    payment_ids = fields.Many2many('account.move', readonly=True, copy=False,
                                   help="The payment record related to the rental order.")
    picking_ids = fields.Many2many('stock.picking', readonly=True, copy=False, default=False,
                                   help="The stock picking associated with the rental order.")
    is_invoiced = fields.Boolean(copy=False, help="Indicates whether the rental order has been invoiced.")
    can_be_returned = fields.Boolean(copy=False,
                                     help="Indicates whether the items in the rental order can be returned.")
    website_id = fields.Many2one('website', ondelete='cascade', check_company=True, help="Choose website")
    return_picking_ids = fields.Many2many('stock.picking', compute="_compute_return_picking_ids",
                                          copy=False, help="Return of the model", relation='return_picking_model_rel')
    is_extra_cost = fields.Boolean(string="Extra Charges", copy=False, help="Enable this to add extra charges")
    create_inv_for_extra_cost = fields.Boolean(string="Create Invoice for Extra Charge", copy=False)
    is_portal_extra = fields.Boolean(string="Portal Extra Time", help="Portal extra time")
    extra_time_invoice_ids = fields.Many2many('account.move', relation="m2m_move_extra_time_invoice_rel",
                                              string="Overtime Invoice", copy=False,
                                              help="Invoices which are created for overtime")
    return_count = fields.Integer('Returns Count', compute='_compute_return_count')
    picking_count = fields.Integer('Deliveries Count', compute='_compute_picking_count')

    def _compute_return_picking_ids(self):
        """Compute the return picking IDs"""
        for rec in self:
            rec.return_picking_ids = rec.picking_ids.mapped('return_ids').ids

    @api.depends('return_picking_ids')
    def _compute_return_count(self):
        """Compute return count"""
        for order in self:
            order.return_count = len(order.return_picking_ids)

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        """Compute the number of picking"""
        for order in self:
            order.picking_count = len(order.picking_ids)

    @api.depends('order_line_ids.price_subtotal', 'order_line_ids.price_tax', 'order_line_ids.price_total')
    def _compute_amount_total(self):
        """ Compute the total amount of Rental Order """
        for order in self:
            order_lines = order.order_line_ids.filtered(lambda x: not x.display_type)
            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes(
                    [line._convert_to_tax_base_line_dict() for line in order_lines])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))
            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        """ Compute partner shipping id """
        for order in self:
            order.partner_shipping_id = order.partner_id.address_get(
                ['delivery'])['delivery'] if order.partner_id else False

    @api.depends('partner_id')
    def _compute_partner_invoice_id(self):
        """ Compute partner invoice id """
        for order in self:
            order.partner_invoice_id = order.partner_id.address_get(
                ['invoice'])['invoice'] if order.partner_id else False

    @api.depends('partner_id')
    def _compute_note(self):
        use_invoice_terms = self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms')
        if not use_invoice_terms:
            return
        for order in self:
            order = order.with_company(order.company_id)
            if order.terms_type == 'html' and self.env.company.invoice_terms_html:
                baseurl = html_keep_url(order._get_note_url() + '/terms')
                context = {'lang': order.partner_id.lang or self.env.user.lang}
                order.note = _('Terms & Conditions: %s', baseurl)
                del context
            elif not is_html_empty(self.env.company.invoice_terms):
                order.note = order.with_context(lang=order.partner_id.lang).env.company.invoice_terms

    def action_pay_extra(self):
        """Returns the invoice values and the particular actions"""
        if self.extra_time_invoice_ids:
            if (sum(self.extra_time_invoice_ids.mapped('amount_untaxed_signed'))) == sum(self.order_line_ids.filtered(
                    lambda line: line.is_extra_product).mapped('price_subtotal')):
                raise ValidationError(_('Already created the invoice for the price' + str(sum(
                    self.extra_time_invoice_ids.mapped('amount_untaxed_signed')))))
            else:
                invoice_vals_list = [{
                    'move_type': 'out_invoice',
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                    'partner_id': self.partner_invoice_id.id,
                    'partner_shipping_id': self.partner_shipping_id.id,
                    'invoice_origin': self.name,
                    'invoice_line_ids': [Command.create({
                        'display_type': 'product', 'sequence': 0,
                        'name': line.product_id.display_name,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'quantity': 1,
                        'price_unit': line.price_subtotal - sum(self.payment_ids.invoice_line_ids.filtered(
                            lambda rec: rec.product_id.id == line.product_id.id).mapped('price_subtotal')),
                        'tax_ids': [Command.set(line.tax_ids.ids)],
                        'rental_order_ids': [Command.link(self.id)],
                    }) for line in self.order_line_ids.filtered(
                        lambda line: line.is_extra_product and line.price_subtotal - sum(
                            self.payment_ids.invoice_line_ids.filtered(
                                lambda rec: rec.product_id.id == line.product_id.id).mapped('price_subtotal')))]
                }]
                moves = self.env['account.move'].sudo().create(invoice_vals_list)
                self.write({'create_inv_for_extra_cost': False})
                self.payment_ids = [Command.link(moves.id)]
                self.extra_time_invoice_ids = [Command.link(moves.id)]
                for line in self.order_line_ids:
                    line.qty_invoiced = line.product_uom_qty
                return {
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'name': moves.name,
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'res_id': moves.id
                }

        else:
            invoice_vals_list = [{
                'move_type': 'out_invoice', 'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'partner_id': self.partner_invoice_id.id,
                'partner_shipping_id': self.partner_shipping_id.id,
                'invoice_origin': self.name,
                'invoice_line_ids': [Command.create(
                    {'display_type': 'product', 'sequence': 0,
                     'name': line.product_id.display_name,
                     'product_id': line.product_id.id,
                     'product_uom_id': line.product_uom_id.id,
                     'quantity': line.product_uom_qty,
                     'price_unit': line.price_unit,
                     'tax_ids': [Command.set(line.tax_ids.ids)],
                     'rental_order_ids': [Command.link(self.id)],
                     }) for line in self.order_line_ids.filtered(
                    lambda line: line.is_extra_product)]
            }]
            moves = self.env['account.move'].sudo().create(invoice_vals_list)
            self.write({'create_inv_for_extra_cost': False})
            self.payment_ids = [Command.link(moves.id)]
            self.extra_time_invoice_ids = [Command.link(moves.id)]
            for line in self.order_line_ids:
                line.qty_invoiced = line.product_uom_qty
            return {
                'type': 'ir.actions.act_window',
                'target': 'current',
                'name': moves.name,
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': moves.id
            }

    def action_pay_now(self):
        """Create an invoice and mark it as paid"""
        if all(line.product_id.invoice_policy == 'order' for line in self.order_line_ids):
            invoice_vals_list = [{
                'move_type': 'out_invoice', 'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'partner_id': self.partner_invoice_id.id,
                'partner_shipping_id': self.partner_shipping_id.id,
                'invoice_origin': self.name,
                'invoice_line_ids': [Command.create(
                    {'display_type': 'product', 'sequence': 0,
                     'name': line.product_id.display_name,
                     'product_id': line.product_id.id,
                     'product_uom_id': line.product_uom_id.id,
                     'quantity': line.product_uom_qty,
                     'price_unit': line.price_unit,
                     'tax_ids': [Command.set(line.tax_ids.ids)],
                     'rental_order_ids': [Command.link(self.id)],
                     }) for line in self.order_line_ids.filtered(lambda line: not line.is_extra_product)]
            }]
            moves = self.env['account.move'].sudo().create(invoice_vals_list)
            self.write({'is_invoiced': True, })
            self.payment_ids = [Command.link(moves.id)]
            for line in self.order_line_ids:
                line.qty_invoiced = line.product_uom_qty
            return {
                'type': 'ir.actions.act_window',
                'target': 'current',
                'name': moves.name,
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': moves.id
            }
        else:
            if any(line.product_id.invoice_policy == 'order' for line in
                   self.order_line_ids):
                if self.payment_ids:
                    lines = self.order_line_ids.filtered(
                        lambda line: line.product_id.invoice_policy == 'delivery' and not line.is_extra_product)
                    invoice_vals_list = [{
                        'move_type': 'out_invoice',
                        'currency_id': self.currency_id.id,
                        'company_id': self.company_id.id,
                        'partner_id': self.partner_invoice_id.id,
                        'partner_shipping_id': self.partner_shipping_id.id,
                        'invoice_origin': self.name,
                        'invoice_line_ids': [Command.create(
                            {'display_type': 'product', 'sequence': 0,
                             'name': line.product_id.display_name,
                             'product_id': line.product_id.id,
                             'product_uom_id': line.product_uom_id.id,
                             'quantity': line.qty_delivered - line.qty_invoiced,
                             'price_unit': line.price_unit,
                             'tax_ids': [Command.set(line.tax_ids.ids)],
                             'rental_order_ids': [Command.link(self.id)],
                             }) for line in lines.filtered(lambda line: line.qty_delivered - line.qty_invoiced)]
                    }]
                    if invoice_vals_list[0]['invoice_line_ids']:
                        moves = self.env['account.move'].sudo().create(invoice_vals_list)
                        self.payment_ids = [Command.link(moves.id)]
                        for line in lines:
                            line.qty_invoiced += line.qty_delivered - line.qty_invoiced
                        if all(line.qty_invoiced == line.product_uom_qty for line in self.order_line_ids):
                            self.write({'is_invoiced': True})
                        return {
                            'type': 'ir.actions.act_window',
                            'target': 'current',
                            'name': moves.name,
                            'view_mode': 'form',
                            'res_model': 'account.move',
                            'res_id': moves.id
                        }
                    else:
                        raise ValidationError(_('Please deliver the remaining products.'))
                else:
                    lines = self.order_line_ids.filtered(
                        lambda line: line.product_id.invoice_policy == 'order' and not line.is_extra_product)
                    invoice_vals_list = [{
                        'move_type': 'out_invoice',
                        'currency_id': self.currency_id.id,
                        'company_id': self.company_id.id,
                        'partner_id': self.partner_invoice_id.id,
                        'partner_shipping_id': self.partner_shipping_id.id,
                        'invoice_origin': self.name,
                        'invoice_line_ids': [Command.create(
                            {'display_type': 'product', 'sequence': 0,
                             'name': line.product_id.display_name,
                             'product_id': line.product_id.id,
                             'product_uom_id': line.product_uom_id.id,
                             'quantity': line.product_uom_qty,
                             'price_unit': line.price_unit,
                             'tax_ids': [Command.set(line.tax_ids.ids)],
                             'rental_order_ids': [Command.link(self.id)],
                             }) for line in lines]
                    }]
                    moves = self.env['account.move'].sudo().create(
                        invoice_vals_list)
                    self.payment_ids = [Command.link(moves.id)]
                    for line in lines:
                        line.qty_invoiced = line.product_uom_qty
                    return {
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'name': moves.name,
                        'view_mode': 'form',
                        'res_model': 'account.move',
                        'res_id': moves.id
                    }
            else:
                if sum(self.order_line_ids.mapped('qty_delivered')) == 0:
                    raise ValidationError(_('Please deliver the products first.'))
                else:
                    lines = self.order_line_ids.filtered(
                        lambda line: line.qty_delivered and line.qty_delivered - line.qty_invoiced
                                     and not line.is_extra_product)
                    invoice_vals_list = [{
                        'move_type': 'out_invoice',
                        'currency_id': self.currency_id.id,
                        'company_id': self.company_id.id,
                        'partner_id': self.partner_invoice_id.id,
                        'partner_shipping_id': self.partner_shipping_id.id,
                        'invoice_origin': self.name,
                        'invoice_line_ids': [Command.create(
                            {'display_type': 'product', 'sequence': 0,
                             'name': line.product_id.display_name,
                             'product_id': line.product_id.id,
                             'product_uom_id': line.product_uom_id.id,
                             'quantity': line.qty_delivered - line.qty_invoiced,
                             'price_unit': line.price_unit,
                             'tax_ids': [Command.set(line.tax_ids.ids)],
                             'rental_order_ids': [Command.link(self.id)],
                             }) for line in lines]
                    }]
                    if invoice_vals_list[0]['invoice_line_ids']:
                        moves = self.env['account.move'].sudo().create(
                            invoice_vals_list)
                        self.payment_ids = [Command.link(moves.id)]
                        for line in lines:
                            line.qty_invoiced += line.qty_delivered - line.qty_invoiced
                        if all(line.qty_invoiced == line.product_uom_qty for line in self.order_line_ids):
                            self.write({'is_invoiced': True, })
                        return {
                            'type': 'ir.actions.act_window',
                            'target': 'current',
                            'name': moves.name,
                            'view_mode': 'form',
                            'res_model': 'account.move',
                            'res_id': moves.id
                        }
                    else:
                        raise ValidationError(_('Please deliver the remaining products.'))

    @api.model
    def _get_note_url(self):
        """Get base URL"""
        return self.env.company.get_base_url()

    @api.model_create_multi
    def create(self, vals_list):
        """" Sequence for rental orders """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rental.order') or _('New')
            res = super(RentalOrder, self).create(vals)
        return res

    def action_confirm(self):
        """ Confirm the rental order """
        self.write({'state': 'rented'})

    def action_print_token(self):
        """ Printing Rental Tokens """
        return (self.env.ref('cyllo_rental_base.report_action_rental_token').report_action(self))

    def check_product_availability(self, location, product_id):
        """Function to check availability"""
        stock_quant = self.env['stock.quant'].search([('location_id', '=', location.id),
                                                      ('product_id', '=', product_id.id)]).ids
        if len(stock_quant) < 1:
            return False
        else:
            return True

    def action_pickup(self):
        """Function for product pickup"""
        wizard = self.env['rental.delivery'].create({
            'rental_id': self.id,
            'rental_line_ids': [Command.create({
                'product_id': line.product_id.id,
                'quantity': line.product_uom_qty - line.qty_delivered,
                'product_uom_id': line.product_uom_id.id,
                'product_location_id': line.product_location_id.id,
                'line_id': line.id
            }) for line in self.order_line_ids.filtered(lambda line: line.qty_delivered < line.product_uom_qty)]
        })
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Delivery Order',
            'view_mode': 'form',
            'res_model': 'rental.delivery',
            'res_id': wizard.id,
        }

    def action_see_returns(self):
        """Function for the see_returns"""
        return {
            'name': _('Returns'),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [('id', 'in', self.return_picking_ids.ids)],
        }

    def action_see_deliveries(self):
        """Function for the see_deliveries"""
        return {
            'name': _('Deliveries'),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [('id', 'in', self.picking_ids.ids)],
        }

    def action_add_extra_charge(self):
        """Function for adding extra charges for extra time"""
        products = self.order_line_ids.mapped('product_id').ids
        for line in self.order_line_ids:
            if line.product_id.extra_hourly_price and line.product_id.delay_product_id and line.product_id.is_rental:
                time_difference = fields.Datetime.now() - line.return_date
                total_seconds = time_difference.total_seconds()
                hours = total_seconds // 3600
                if hours > line.product_id.apply_after:
                    self.create_inv_for_extra_cost = True
                    if not line.product_id.delay_product_id.id in products:
                        self.write({
                            'order_line_ids': [Command.create({
                                'product_id': line.product_id.delay_product_id.id,
                                'product_uom_qty': line.product_uom_qty,
                                'is_extra_product': True,
                                'qty_delivered': line.product_uom_qty,
                                'price_unit': line.product_id.extra_hourly_price * hours,
                                'company_id': line.company_id.id,
                                'pickup_date': fields.Datetime.now(),
                                'return_date': fields.Datetime.now(),
                            })]
                        })
                    else:
                        order_line = self.order_line_ids.filtered(
                            lambda order_line: order_line.product_id == line.product_id.delay_product_id)
                        order_line.write({'price_unit': line.product_id.extra_hourly_price * hours})
            elif line.product_id.is_extra_cost:
                if not line.product_id.delay_product_id and not line.product_id.extra_hourly_price:
                    raise ValidationError(_('Delay product or price not added'))

    def action_ready_to_return(self):
        """ Returning the rental orders """
        self.action_add_extra_charge()
        if sum(self.order_line_ids.mapped('product_uom_qty')) == sum(
                self.return_picking_ids.move_ids.mapped('product_uom_qty')):
            self.write({'state': 'ready_to_return'})
        else:
            return {
                'type': 'ir.actions.act_window',
                'target': 'new',
                'name': 'Reverse Transfer',
                'view_mode': 'form',
                'res_model': 'stock.return.picking',
                'context': {
                    'default_picking_ids': self.picking_ids.ids
                }
            }

    def action_return(self):
        """Change state to 'return'"""
        for picking in self.return_picking_ids:
            if picking.state != 'done':
                picking.button_validate()
        self.write({'state': 'return', 'is_returned': True})

    def action_get_invoice(self):
        """" To view invoices created """
        self.ensure_one()
        return {
            'name': 'invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.payment_ids.ids)],
            'context': "{'create': False}",
            'target': 'current'
        }

    def _is_public_order(self):
        """Check if the order is associated with the public user of the current website."""
        self.ensure_one()
        return self.partner_id.id == request.website.user_id.sudo().partner_id.id

    def get_portal_last_transaction(self):
        """ Last transaction from portal """
        self.ensure_one()
        return self.transaction_ids.sudo()._get_last()

    def _compute_access_url(self):
        """ Return the access url"""
        super()._compute_access_url()
        for request in self:
            request.access_url = f'/my/rentals/record/{request.id}'

    # providing name for report in the portal
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Rental Order-%s' % self.name


class RentalOrderLine(models.Model):
    """ Rental order lines """
    _name = 'rental.order.line'
    _description = "Rental Order Line"
    _rec_names_search = ['name', 'order_id.name']
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    order_id = fields.Many2one('rental.order')
    sequence = fields.Integer(default=10)
    rental_type = fields.Selection(selection=[('product', 'Product')], default='product')
    company_id = fields.Many2one(related='order_id.company_id', store=True, index=True, precompute=True,
                                 help="The company associated with the rental order.")
    is_extra_product = fields.Boolean(string="Extra Product", default=False, help="Product for the extra charges")
    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True,
                                  precompute=True, help="The currency used for the rental order.")
    state = fields.Selection(related='order_id.state', string="Order Status", copy=False, store=True, precompute=True,
                             help="The current status of the rental order.")
    display_type = fields.Selection(selection=[('line_section', "Section"), ('line_note', "Note")], default=False,
                                    help="The type of display for the rental order line.")
    product_id = fields.Many2one('product.product')
    product_ids = fields.Many2many('product.product', string="Products", compute="_compute_product_ids",
                                   help="Products which are available")
    product_tracking = fields.Selection(([]), related='product_id.tracking', store=True,
                                        help="Product tracking details")
    lot_ids = fields.Many2many(
        'stock.lot', string="Lot/Serial Number", help="Choose lot or serial number",
        domain="[('product_id','=',product_id),('location_id','=',product_location_id), ('product_qty','!=',0)]")
    name = fields.Text(string="Description", help="Description of the rental order line.")
    tax_ids = fields.Many2many('account.tax', string="Taxes", context={'active_test': False},
                               check_company=True, compute="_compute_tax_ids", store=True, readonly=False,
                               help="Taxes applied to the rental order line.")
    price_unit = fields.Float(string="Unit Price", digits='Product Price',
                              help="The unit price of the rental order line.")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', string="UoM Category",
                                              help="Unit of Measure (UoM) category of the product.")
    product_uom_qty = fields.Float(string="Quantity", digits='Product Unit of Measure', default=1, required=True,
                                   help="The quantity of the product in the rental order line.")
    product_uom_id = fields.Many2one('uom.uom', string="Unit of Measure",
                                     compute='_compute_product_uom_id', store=True, readonly=False, precompute=True,
                                     ondelete='restrict', domain="[('category_id', '=', product_uom_category_id)]",
                                     help="The unit of measure for the product in the rental order line.")
    discount = fields.Float(string="Discount (%)", digits='Discount', help="Discount applied to the rental order line.")
    price_subtotal = fields.Monetary(string="Subtotal", compute='_compute_price_subtotal', store=True, precompute=True,
                                     help="Subtotal amount for the rental order line.")
    price_tax = fields.Float(string="Total Tax", compute='_compute_price_subtotal', store=True, precompute=True,
                             help="Total tax amount for the rental order line.")
    price_total = fields.Monetary(string="Total", compute='_compute_price_subtotal', store=True, precompute=True,
                                  help="Total amount for the rental order line.")
    pickup_date = fields.Datetime(required=True, help="Date and time when the product is picked up.")
    return_date = fields.Datetime(required=True, help="Date and time when the product is returned.")
    duration = fields.Char(compute='_compute_duration', store=True, help="Duration of the rental order line.")
    extra_hours = fields.Float(help="Extra hours added to the rental order line.")
    delay_amount = fields.Float(string="Extra fine",
                                help="Additional amount charged for delays in returning the product.")
    rental_price_reduce_taxexcl = fields.Monetary(
        string="Price Reduce Tax excl",  compute='_compute_rental_price_reduce_taxexcl', store=True, precompute=True,
        help="Reduced price excluding tax for the rental order line.")
    rental_price_reduce_taxinc = fields.Monetary(
        string="Price Reduce Tax incl", compute='_compute_rental_price_reduce_taxinc', store=True, precompute=True,
        help="Reduced price including tax for the rental order line.")
    is_picked = fields.Boolean(copy=False, help="Indicates whether the product in the rental order line has been "
                                                "picked.")
    is_returned = fields.Boolean(help="Indicates whether the product in the rental order line has been returned.")
    is_invoiced = fields.Boolean(help="Indicates whether the product in the rental order line has been invoiced.")
    product_location_id = fields.Many2one('stock.location', help="Location of the product")
    pickup_id = fields.Many2one('stock.picking', string="Picking Id", help="Stock picking id")
    qty_delivered = fields.Float(string="Delivered", copy=False)
    qty_invoiced = fields.Float(string="Invoiced", copy=False)

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        """ Compute product uom """
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends('product_id')
    def _compute_tax_ids(self):
        """Function for computing tax"""
        company_domain = self.env['account.tax']._check_company_domain(self.company_id)
        for line in self:
            filtered_taxes_id = line.product_id.taxes_id.filtered_domain(company_domain)
            if filtered_taxes_id:
                line.tax_ids = filtered_taxes_id.ids
            else:
                line.tax_ids = []

    @api.depends('price_subtotal', 'product_uom_qty')
    def _compute_rental_price_reduce_taxexcl(self):
        """Function for computing rental_price_reduce_taxexcl"""
        for line in self:
            line.rental_price_reduce_taxexcl = (
                    line.price_subtotal / line.product_uom_qty) if line.product_uom_qty else 0.0

    @api.depends('price_total', 'product_uom_qty')
    def _compute_rental_price_reduce_taxinc(self):
        """Function for computing rental_price_reduce_taxinc"""
        for line in self:
            line.rental_price_reduce_taxinc = (
                    line.price_total / line.product_uom_qty) if line.product_uom_qty else 0.0

    @api.depends('pickup_date', 'return_date', 'product_id')
    def _compute_duration(self):
        """ Computing the duration """
        for rec in self:
            if rec.product_id.is_rental:
                if not rec.pickup_date or not rec.return_date:
                    rec.duration = 0
                    rec.price_unit = 0
                elif rec.return_date < rec.pickup_date:
                    raise ValidationError(_("End date should be greater than Start date"))
                else:
                    timedelta = rec.return_date - rec.pickup_date
                    total_seconds = timedelta.total_seconds()
                    years, days = divmod(timedelta.days, 365)
                    months = days // 30
                    days %= 30
                    hours = total_seconds // 3600
                    available_prices = {}
                    for period in ['hours', 'days', 'months', 'years']:
                        period_cost = self.product_id.rental_charging_ids.filtered(
                            lambda b: b.rental_period == period).mapped('price')
                        if period_cost:
                            available_prices[period] = period_cost[0]
                    yearly_cost = 0
                    monthly_cost = 0
                    daily_cost = 0
                    hourly_cost = 0
                    remaining_hours = hours - (years * 365 * 24) - (months * 30 * 24) - (days * 24)
                    if available_prices:
                        if years > 0:
                            if 'years' in available_prices:
                                yearly_cost = years * available_prices['years']
                            elif 'months' in available_prices:
                                yearly_cost = years * 12 * available_prices['months']
                            elif 'days' in available_prices:
                                yearly_cost = years * 365 * available_prices['days']
                            else:
                                yearly_cost = years * 8760 * available_prices['hours']
                        if months > 0 and monthly_cost:
                            if 'months' in available_prices:
                                monthly_cost = months * available_prices['months']
                            elif 'days' in available_prices:
                                monthly_cost = months * 30 * available_prices['days']
                            elif 'hours' in available_prices:
                                monthly_cost = months * 7200 * available_prices['hours']
                            else:
                                monthly_cost = (months / 12) * available_prices['years']
                        if days > 0:
                            if 'days' in available_prices:
                                daily_cost = days * available_prices['days']
                            elif 'hours' in available_prices:
                                daily_cost = days * 24 * available_prices['hours']
                            elif 'months' in available_prices:
                                daily_cost = (days / 30) * available_prices['months']
                            else:
                                daily_cost = (days / 365) * available_prices['years']
                        # Calculate the remaining hours' cost
                        if remaining_hours > 0:
                            if 'hours' in available_prices:
                                hourly_cost = remaining_hours * available_prices['hours']
                            elif 'days' in available_prices:
                                hourly_cost = (remaining_hours / 24) * available_prices['days']
                            elif 'months' in available_prices:
                                hourly_cost = (remaining_hours / 7200) * available_prices['months']
                            else:
                                hourly_cost = (remaining_hours / 8760) * available_prices['years']
                    total_price = yearly_cost + monthly_cost + daily_cost + hourly_cost
                    duration_parts = [
                        f"{years} years" if years else None,
                        f"{months} months" if months else None,
                        f"{days} days" if days else None,
                        f"{remaining_hours} hours" if remaining_hours else None
                    ]
                    duration_parts = [part for part in duration_parts if part]  # Remove None values
                    rec.duration = ', '.join(duration_parts)
                    rec.price_unit = total_price

    @api.depends('discount', 'price_unit', 'tax_ids', 'product_uom_qty')
    def _compute_price_subtotal(self):
        """ Compute the amounts of the RO line. """
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']
            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax
            })

    @api.depends('product_id')
    def _compute_product_ids(self):
        """ Product available for renting"""
        products = self.env['product.product'].search([('is_rental', '=', True)]).filtered(
            lambda product: product.current_rented_quantity < product.qty_available)
        for rec in self:
            rec.write({'product_ids': [Command.set(products.ids)]})

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Function for getting the product location"""
        self.product_location_id = self.product_id.rental_location_id.id

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        """Function for the lot ids"""
        if self.lot_ids:
            self.product_uom_qty = len(self.lot_ids.ids)

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        """Function for updating price_un it"""
        if self.product_id.min_quantity and self.product_id.min_qty_amt:
            if self.product_uom_qty >= self.product_id.min_quantity:
                self.price_unit = self.product_id.min_qty_amt

    def _convert_to_tax_base_line_dict(self, **kwargs):
        """ Convert the current record to a dictionary to use the
        generic taxes computation method defined on account.tax.
        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.price_unit,
            quantity=self.product_uom_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
            **kwargs,
        )
