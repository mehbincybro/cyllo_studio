from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    """Inherited model for extending maintenance requests."""
    _inherit = 'maintenance.request'

    asset_id = fields.Many2one('asset.asset')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    expense = fields.Monetary(string="Expense")
    partner_id = fields.Many2one('res.partner', string="Repair partner")
    has_invoiced = fields.Boolean(default=False)
    stage_done = fields.Boolean(related='stage_id.done', store=True)
    warranty_percentage = fields.Float(string="Warranty Deduction in %", default=100)
    has_warranty = fields.Boolean(default=False, compute="_compute_has_warranty")
    has_insurance = fields.Boolean(default=False, compute="_compute_has_insurance")

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
        else:
            self.has_insurance = False

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        if self.equipment_id:
            self.asset_id = False
            self.partner_id = False
            self.expense = False

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        if self.asset_id:
            self.equipment_id = False

    def action_create_bill(self):
        """Button action for creating the bill for the repair"""
        if self.expense==0:
            raise ValidationError(_('The expense is 0.'))
        if self.partner_id==False:
            raise ValidationError(_('The Partner field is blank.'))

        insurance_percentage = self.env.context.get('insurance_percentage', 0)
        from_wizard = self.env.context.get('from_insurance_wizard', False)
        is_reimburse = self.env.context.get('is_reimbursed', False)
        if from_wizard and insurance_percentage > 0:
            repair_invoice = self.env['account.move'].create({
                'ref': self.asset_id.name,
                'partner_id': self.partner_id.id,
                'move_type': 'in_invoice',
                'state': 'draft',
                'repair_id': self.id,
                'asset_id': False,
                'invoice_date':fields.Date.today(),
                'invoice_line_ids': [fields.Command.create({
                    'name': f"{self.asset_id.name}-Repair Bill",
                    'move_type': 'in_invoice',
                    'quantity': 1,
                    'price_unit': self.expense - (self.expense * (insurance_percentage / 100)),
                    'price_subtotal': self.expense - (self.expense * (insurance_percentage / 100)),
                })]
            })
        elif self.has_warranty and self.warranty_percentage > 0:
            repair_invoice = self.env['account.move'].create({
                'ref': self.asset_id.name,
                'partner_id': self.partner_id.id,
                'move_type': 'in_invoice',
                'state': 'draft',
                'repair_id': self.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [fields.Command.create({
                    'name': f"{self.asset_id.name}-Repair Bill",
                    'move_type': 'in_invoice',
                    'quantity': 1,
                    'price_unit': self.expense - (self.expense * (self.warranty_percentage / 100)),
                    'price_subtotal': self.expense - (self.expense * (self.warranty_percentage / 100)),
                })]
            })
        else:
            repair_bill = self.env['account.move'].create({
                'ref': self.asset_id.name,
                'partner_id': self.partner_id.id,
                'move_type': 'in_invoice',
                'state': 'draft',
                'repair_id': self.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [fields.Command.create({
                    'name': f"{self.asset_id.name}-Repair Bill",
                    'move_type': 'in_invoice',
                    'quantity': 1,
                    'price_unit': self.expense,
                    'price_subtotal': self.expense
                })]
            })
        self.has_invoiced = True


    def action_view_invoice(self):
        """Function for viewing the invoice"""
        repair_bill = self.env['account.move'].search(
            [('ref', '=', self.asset_id.name), ('repair_id', '=', self.id)])
        return {
            'name': 'Bill',
            'view_mode': 'form',
            'res_id': repair_bill.id,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
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


    def action_claim_insurance(self):
        return {
            'name': _('Claim Insurance'),
            'view_mode': 'form',
            'res_model': 'asset.insurance',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_id': self.asset_id.id,
                'default_total_amount': self.expense,
                'default_repair_id': self.id,
                'default_reimburse_after_invoice': False
            },
            'target': 'new'
        }
