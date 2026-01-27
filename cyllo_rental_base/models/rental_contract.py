# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError


class RentalContract(models.Model):
    """ Rental lease/contract """
    _name = 'rental.contract'
    _description = 'Rental Lease/Contract'
    _inherit = 'mail.thread'
    _check_company_auto = True

    name = fields.Char(string='Contract Name', readonly=True, default=lambda self: _('New'),
                       help='The name of the rental contract')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', required=True, tracking=True,
                                 domain="[('company_id', 'in', (False, ""company_id))]",
                                 help='The customer associated with this rental contract')
    contract_line_ids = fields.One2many(comodel_name='contract.lines', inverse_name='contract_id', string='Products',
                                        required=True, help='The products associated with this rental contract')
    quantity = fields.Integer(help='The quantity of the products in the rental contract')
    contract_start_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True,
                                      help='The start date of the rental contract')
    contract_end_date = fields.Date(
        string='Contract Ending Date', required=True, tracking=True, help='The end date of the rental contract',
        default=lambda self: (datetime.today() + timedelta(days=365)).replace(year=datetime.today().year + 1))
    state = fields.Selection(selection=[('draft', 'Draft'), ('in_contract', 'In Contract'), ('expired', 'Expired'),
                                        ('closed', 'Closed')], default='draft', readonly=True,
                             help='The current state of the rental contract')
    amount = fields.Monetary(help='The amount associated with the rental contract')
    company_id = fields.Many2one(comodel_name='res.company', required=True, index=True,
                                 default=lambda self: self.env.company,
                                 help='The company associated with this rental contract')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  help='The currency used for transactions related to this rental contract')
    contract_template_id = fields.Many2one('rental.contract.template',
                                           help="Choose the template for the contract")
    contract_price = fields.Monetary(related="contract_template_id.price", store=True, readonly=False)
    invoice_ids = fields.Many2many('account.move', string="Invoices",
                                   help="All invoice created based on this contract")
    is_paid = fields.Boolean(string="Paid", help="Enables if its paid")

    @api.onchange('contract_template_id')
    def _onchange_contract_template_id(self):
        """Onchange function for adding values to the contract line from contract template"""
        self.contract_line_ids = self.contract_template_id.contract_line_ids.ids

    def action_create_invoice(self):
        """Create invoice"""
        self.contract_start_date = fields.Date.today()
        if self.contract_start_date > self.contract_end_date:
            raise ValidationError(_('Change the contract end date,it is lesser that start date'))
        else:
            product = self.env.ref('cyllo_rental_base.product_product_rental_contract')
            invoice = self.env['account.move'].create({
                'partner_id': self.partner_id.id,
                'date': fields.Date.today(),
                'move_type': 'out_invoice',
                'invoice_line_ids': [Command.create({
                    'name': product.name,
                    'quantity': 1,
                    'price_unit': self.contract_price,
                    'product_id': product.id,
                })]
            })
            invoice.action_post()
            self.write({'invoice_ids': [fields.Command.link(invoice.id)], 'is_paid': True, 'state': 'in_contract'})

    @api.model_create_multi
    def create(self, vals_list):
        """" Sequence for rental orders """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rental.contract') or _('New')
        res = super(RentalContract, self).create(vals_list)
        return res

    def action_get_invoice(self):
        """Return to account.move"""
        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': "{'create': False}",
            'target': 'current'
        }

    def action_close(self):
        """Function for closing the contract"""
        self.write({'state': 'closed'})

    def check_contract_expired(self):
        """Function for checking contract expiration date"""
        for contract in self.search([('state', '=', 'in_contract')]):
            if contract.contract_end_date <= fields.Date.today():
                contract.write({'state': 'expired'})


class ContractLines(models.Model):
    """ Contract lines """
    _name = 'contract.lines'
    _description = 'Contract Lines'

    product_id = fields.Many2one('product.product')
    product_ids = fields.Many2many('product.product', string="Products", compute="_compute_product_ids",
                                   help="Products which are available")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0,
                                   required=True, help='The quantity of the product in the contract line')
    product_uom_id = fields.Many2one(comodel_name='uom.uom', string="Unit of Measure",
                                     compute='_compute_product_uom_id',
                                     store=True, readonly=False, precompute=True, ondelete='restrict',
                                     domain="[('category_id', '=', product_uom_category_id)]",
                                     help='The unit of measure for the product in the contract line')
    product_uom_category_id = fields.Many2one(string='UoM Category', related='product_id.uom_id.category_id',
                                              help='The category of the unit of measure for the product in the'
                                                   ' contract line')
    price_unit = fields.Float(string='Price', digits='Product Price', compute="_compute_price_unit", store=True,
                              help='The recurring price for the product in the contract line')
    currency_id = fields.Many2one(related='contract_id.currency_id', depends=['contract_id.currency_id'], store=True,
                                  precompute=True,
                                  help='The currency used for transactions related to the contract line')
    company_id = fields.Many2one(comodel_name='res.company', required=True, index=True,
                                 default=lambda self: self.env.company,
                                 help='The company associated with the contract line')
    contract_id = fields.Many2one('rental.contract',
                                  help='The rental contract associated with this contract line')
    contract_template_id = fields.Many2one('rental.contract.template', string="Rental Contract Template",
                                           help="Connection to rental contract template")
    charge_per = fields.Char(string="Price per", help="Price as per", readonly=True)
    tax_ids = fields.Many2many('account.tax', string="Taxes", context={'active_test': False},
                               check_company=True, compute="_compute_tax_ids", store=True, readonly=False,
                               help="Taxes applied to the rental order line.")

    @api.depends('product_id')
    def _compute_product_ids(self):
        """ Product available for renting"""
        products = self.env['product.product'].search([('is_rental', '=', True)]).filtered(
            lambda product: (product.current_rented_quantity < product.qty_available and
                             len(product.rental_charging_ids) >= 1))
        for rec in self:
            rec.write({'product_ids': [fields.Command.set(products.ids)]})

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        """ Compute the product uom """
        for line in self:
            if not line.product_uom_id or (line.product_id.uom_id.id != line.product_uom_id.id):
                line.product_uom_id = line.product_id.uom_id

    @api.depends('product_id')
    def _compute_price_unit(self):
        """Function for computing price and type charging"""
        for rec in self.filtered(lambda x: x.product_id):
            if rec.product_id.rental_charging_ids:
                for charge in rec.product_id.rental_charging_ids:
                    rec.price_unit = charge.price
                    rec.charge_per = charge.rental_period

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
