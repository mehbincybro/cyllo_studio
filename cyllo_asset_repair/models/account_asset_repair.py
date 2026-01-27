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
from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.exceptions import UserError


class AccountAssetRepair(models.Model):
    """Inherit the model asset repair for adding new fields"""
    _inherit = 'account.asset.repair'

    def get_repair_user(self):
        """Function for user domain"""
        repair_user = self.env.ref('cyllo_asset_repair.group_cyllo_asset_repair')
        return [('id', 'in', repair_user.users.ids)]

    reference = fields.Char(default='New', readonly=True)
    issue = fields.Char(copy=False, required=True)
    asset_type_id = fields.Many2one("asset.type", related='asset_id.asset_type_id')
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True, copy=False)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', copy=False)
    user_id = fields.Many2one('res.users', string='Responsible User', copy=False, domain=get_repair_user)
    date = fields.Date(default=fields.Date.context_today, copy=False)
    scheduled_date = fields.Date(copy=False, required=True)
    repair_line_ids = fields.One2many('asset.repair.line', 'repair_id', copy=False)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Currency of company')
    is_invoice = fields.Boolean(string='Invoiced', copy=False)
    is_scrap = fields.Boolean()
    active = fields.Boolean(default=True)
    under_warranty = fields.Boolean(string="Under Warranty", related='asset_id.under_warranty')
    warranty_percentage = fields.Float(string="Warranty Deduction in %", default=100)

    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        """Function for checking the scheduled date"""
        purchase_date = self.asset_id.date
        if self.scheduled_date and self.scheduled_date <= purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}. The schedule Date should be greater than the Purchase Date'))

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Function for updating the user"""
        if self.asset_id.is_reserve:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'reserve')])
            self.employee_id = reserved_asset.employee_id.id
        elif self.asset_id.is_lease:
            leased_asset = self.env['asset.lease'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'lease')])
            self.employee_id = self.env['hr.employee'].search(
                [('work_contact_id', '=', leased_asset.customer_id.id)]).id
        elif self.asset_id.is_assign:
            assigned_asset = self.env['asset.assign'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'assign')])
            self.employee_id = assigned_asset.employee_id.id
        elif self.asset_id.is_rental:
            rental_asset = self.env['asset.rental'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'rent')])
            self.employee_id = self.env['hr.employee'].search(
                [('work_contact_id', '=', rental_asset.customer_id.id)]).id
        else:
            self.employee_id = self.env['hr.employee'].search(
                [('work_contact_id', '=', self.env.user.partner_id.id)]).id

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'account.asset.repair') or ''
        return super(AccountAssetRepair, self).create(vals)

    @api.model
    def default_get(self, fields_list):
        """To add repair product on creation time"""
        defaults = super().default_get(fields_list)
        service_product = self.env.ref('cyllo_asset_repair.product_product_repair_service', raise_if_not_found=False)
        if service_product:
            defaults.setdefault('repair_line_ids', [Command.create({
                'product_id': service_product.id,
                'product_qty': 1,
                'repair_action': "add",
            })])
        return defaults

    def unlink(self):
        """Function for unlink the record"""
        for rec in self:
            if rec.status in ['confirm', 'repair']:
                raise UserError(_(f'You cannot delete the record that is in {rec.status} state.'))
            else:
                rec.asset_id.is_repair = False
                return super().unlink()

    def action_confirm(self):
        """Button action for confirming the request"""
        self.status = 'confirm'
        self.asset_id.is_repair = True

    def action_start_repair(self):
        """Button action for starting the repair"""
        if self.asset_id.is_lease == True or self.asset_id.is_rental == True:
            raise UserError(_("The asset is leased or rented... please return it before you continue"))
        else:
            self.status = 'repairing'

    def action_complete_repair(self):
        """Button action for complete the repair"""
        self.status = 'repaired'
        self.asset_id.is_repair = False
        remove_product = self.repair_line_ids.filtered(lambda r: r.repair_action == 'remove')
        if remove_product:
            scrap = self.env['stock.scrap'].create({
                'product_id': remove_product.product_id.id,
                'product_uom_id': remove_product.product_uom_id.id,
                'scrap_qty': remove_product.product_qty,
            })
            scrap.do_scrap()
        if self.asset_id.is_reserve == True:
            self.asset_id.status = 'reserved'
        elif self.asset_id.is_assign == True:
            self.asset_id.status = 'assigned'
        elif self.asset_id.is_confirm == True:
            self.asset_id.status = 'running'
        else:
            self.asset_id.status = 'draft'

    def action_scraped(self):
        """Button action for scrapping the repair asset"""
        self.status = 'scrap'
        self.is_scrap = True
        self.asset_id.is_repair = False
        if self.asset_id.is_entry:
            action_scrap = self.env['asset.sell.dispose'].sudo().create({
                'asset_asset_id': self.asset_id.id,
                'asset_action': 'dispose',
                'loss_account_id': self.asset_item_id.asset_loss_account_id.id,
                'date': fields.Date.today(),
                'note': "Scrapped after repair",
                'disposal_type': 'scrap',
            })
            action_scrap.action_dispose()
        else:
            self.env['asset.sell.dispose'].sudo().create({
                'asset_asset_id': self.asset_id.id,
                'asset_action': 'dispose',
                'date': fields.Date.today(),
                'note': "Scrapped after repair",
                'disposal_type': 'scrap',
            })

    def action_create_invoice(self):
        """Button action for creating the invoice for the repair"""
        repair_invoice = self.env['account.move'].create({
            'ref': self.asset_id.name,
            'partner_id': self.employee_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'repair_id': self.id,
            'invoice_line_ids': [fields.Command.create({
                'product_id': lines.product_id.id,
                'name': self.asset_id.asset_item_id.name,
                'move_type': 'out_invoice',
                'quantity': lines.product_qty,
                'price_unit': lines.unit_price,
                'price_subtotal': lines.price_subtotal
            }) for lines in self.repair_line_ids if lines.repair_action != 'remove']
        })
        self.is_invoice = True

    def action_view_invoice(self):
        """Function for viewing the invoice"""
        repair_invoice = self.env['account.move'].search(
            [('ref', '=', self.asset_id.name), ('repair_id', '=', self.id)])
        return {
            'name': 'Invoice',
            'view_mode': 'form',
            'res_id': repair_invoice.id,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }