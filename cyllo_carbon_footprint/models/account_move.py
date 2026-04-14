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

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_credit_transfer = fields.Boolean(string="Is Credit Transfer", default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_credit_transfer'):
                # Filter invoice_line_ids to only keep products with is_credit_product=True
                if 'invoice_line_ids' in vals:
                    cleaned_lines = []
                    for cmd in vals['invoice_line_ids']:
                        if cmd[0] in (0, 1):
                            product_id = cmd[2].get('product_id')
                            if product_id:
                                product = self.env['product.product'].browse(product_id)
                                if product.is_credit_product:
                                    cleaned_lines.append(cmd)
                        elif cmd[0] == 4:
                            line = self.env['account.move.line'].browse(cmd[1])
                            if line.product_id.is_credit_product:
                                cleaned_lines.append(cmd)
                    vals['invoice_line_ids'] = cleaned_lines
        return super(AccountMove, self).create(vals_list)

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for move in self:
            if move.is_credit_transfer:
                # Strictly remove any line that is NOT a credit product
                other_lines = move.invoice_line_ids.filtered(lambda l: not l.product_id.is_credit_product)
                if other_lines:
                    other_lines.unlink()
        return res

    def action_post(self):
        # Additional validation on post for Sell moves
        for move in self:
            if move.is_credit_transfer and move.move_type == 'out_invoice':
                qty = sum(move.invoice_line_ids.mapped('quantity'))
                available = self._get_available_credits(move.company_id.id)
                if available < qty:
                    raise UserError(_("Not enough available credits to sell. Current balance: %s") % available)
        
        return super(AccountMove, self).action_post()

    def _get_available_credits(self, company_id=None):
        """ Calculate available credits dynamically from posted moves """
        if not company_id:
            company_id = self.env.company.id

        # We sum all products with is_credit_product=True
        credit_products = self.env['product.product'].search([('is_credit_product', '=', True)])
        if not credit_products:
            return 0.0
            
        buy_lines = self.env['account.move.line'].search([
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.company_id', '=', company_id),
            ('product_id', 'in', credit_products.ids)
        ])
        sell_lines = self.env['account.move.line'].search([
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.company_id', '=', company_id),
            ('product_id', 'in', credit_products.ids)
        ])
        
        return sum(buy_lines.mapped('quantity')) - sum(sell_lines.mapped('quantity'))

    credit_product_id = fields.Many2one('product.product', compute='_compute_credit_product_id')

    def _compute_credit_product_id(self):
        # Fallback for UI if needed, though we use the boolean domain now
        credit_product = self.env['product.product'].search([('is_credit_product', '=', True)], limit=1)
        for rec in self:
            rec.credit_product_id = credit_product.id
