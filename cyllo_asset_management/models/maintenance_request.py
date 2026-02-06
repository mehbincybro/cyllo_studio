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
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class MaintenanceRequest(models.Model):
    """Inherited model for extending maintenance and repair requests."""
    _inherit = 'maintenance.request'

    asset_id = fields.Many2one('asset.asset')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    expense = fields.Monetary(string="Expense")
    partner_id = fields.Many2one('res.partner', string="Repair partner")
    has_billed = fields.Boolean(default=False)
    stage_done = fields.Boolean(related='stage_id.done', store=True)
    has_warranty = fields.Boolean(default=False, compute="_compute_has_warranty")
    has_insurance = fields.Boolean(default=False, compute="_compute_has_insurance")
    is_reimburse = fields.Boolean(default=False, compute="_compute_has_insurance")
    invoiced_amount = fields.Monetary()

    @api.constrains('warranty_percentage')
    def _check_assign_date(self):
        """Function for checking the percentage amount"""
        if self.warranty_percentage > 100 or self.warranty_percentage < 0:
            raise UserError(
                _('Please enter a valid insurance percentage'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        asset_id = self.env.context.get('default_asset_id')
        if asset_id:
            asset = self.env['asset.asset'].browse(asset_id)
            today = fields.Date.today()
            res['has_warranty'] = bool(
                asset.under_warranty
                and asset.warranty_end_date
                and asset.warranty_end_date >= today
            )
            res['has_insurance'] = bool(
                asset.under_insurance
                and asset.insurance_end_date
                and asset.insurance_end_date >= today
            )
        return res

    @api.depends('asset_id')
    def _compute_has_warranty(self):
        """Function for checking Warranty period"""
        if self.asset_id.under_warranty and self.asset_id.warranty_end_date >= fields.Date.today():
            self.has_warranty = True
        else:
            self.has_warranty = False

    @api.depends('asset_id')
    def _compute_has_insurance(self):
        """Function for checking Warranty period"""
        if self.asset_id.under_insurance and self.asset_id.insurance_end_date >= fields.Date.today():
            self.has_insurance = True
            if self.asset_id.reimburse_after_invoice:
                self.is_reimburse = True
            else:
                self.is_reimburse = False
        else:
            self.has_insurance = False
            self.is_reimburse = False

    @api.onchange('stage_id')
    def _onchahange_stage_id(self):
        """Function for changing asset's state"""
        if self.asset_id and self.stage_done == True:
            self.asset_id.is_maintenance = False
            self.asset_id.is_repair = False

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        """Function for clearing asset and its related fields"""
        if self.equipment_id:
            self.asset_id = False
            self.partner_id = False
            self.expense = False

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Function for clearing equipment field"""
        if self.asset_id:
            self.equipment_id = False

    def action_create_bill(self):
        """Button action for creating the bill for the repair"""
        if self.expense == 0:
            raise ValidationError(_('The expense is 0.'))

        repair_bill = self.env['account.move'].create({
            'ref': self.asset_id.name,
            'partner_id': self.partner_id.id,
            'move_type': 'in_invoice',
            'state': 'draft',
            'repair_id': self.id,
            'asset_id': False,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [fields.Command.create({
                'name': f"{self.asset_id.name}-Repair Bill",
                'move_type': 'in_invoice',
                'quantity': 1,
                'price_unit': self.expense,
                'price_subtotal': self.expense
            })]
        })
        self.has_billed = True

    def action_claim_insurance(self):
        """Button action for claiming insurance for the repair"""
        self.ensure_one()
        insurance_amount = self.env.context.get('insurance_amount', 0)
        is_reimburse = self.env.context.get('is_reimbursed', False)
        if not is_reimburse and not self.has_billed:
            self.action_create_bill()
        repair_invoice = self.env['account.move'].create({
            'ref': self.asset_id.name,
            'partner_id': self.asset_id.insurance_name.partner_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'repair_id': self.id,
            'asset_id': False,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [fields.Command.create({
                'name': f"{self.asset_id.name}-Insurance claim",
                'move_type': 'out_invoice',
                'quantity': 1,
                'price_unit': insurance_amount,
                'price_subtotal': insurance_amount,
            })]
        })
        self.invoiced_amount += repair_invoice.invoice_line_ids.price_subtotal

    def action_view_invoice(self):
        """Function for viewing the invoice"""
        moves = self.env['account.move'].search(
            [('repair_id', '=', self.id), ('move_type', 'in', ['in_invoice', 'out_invoice'])])
        return {
            'name': _('Invoices / Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('repair_id', '=', self.id), ('move_type', 'in', ['in_invoice', 'out_invoice'])],
        }

    def action_scrap(self):
        """Button action for scrapping the repair asset"""
        self.asset_id.status = 'disposed'
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

    def action_claim_insurance_wizard(self):
        return {
            'name': _('Claim Insurance'),
            'view_mode': 'form',
            'res_model': 'asset.insurance',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_id': self.asset_id.id,
                'default_total_amount': self.expense,
                'default_repair_id': self.id,
                'default_reimburse_after_invoice': self.is_reimburse,
                'default_invoiced_amount': self.invoiced_amount,
                'default_expense': self.expense,
            },
            'target': 'new'
        }
