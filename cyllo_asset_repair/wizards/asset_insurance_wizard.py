from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetInsurance(models.TransientModel):
    """ Wizard model for asset insurance claiming"""
    _name = 'asset.insurance'
    _description = 'Asset Insurance'

    asset_id = fields.Many2one('asset.asset', string='Asset ID', required=True, readonly=True)
    repair_id=fields.Many2one('account.asset.repair', string='Repair ID', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    total_amount = fields.Monetary(string="Total Repair Cost", readonly=True)
    insurance_percentage = fields.Float(string="Insurance Deduction in %", default=100)

    def action_create_invoice(self):
        print("CREATE INV",self.repair_id.id)
        return self.repair_id.with_context(
            insurance_percentage=self.insurance_percentage,
            from_insurance_wizard=True
        ).action_create_invoice()

        # repair_invoice = self.env['account.move'].create({
            # 'ref': self.asset_id.name,
        #     'partner_id': self.repair_id.employee_id.id,
        #     'move_type': 'out_invoice',
        #     'state': 'draft',
        #     'repair_id': self.repair_id.id,
        #     'invoice_line_ids': [fields.Command.create({
        #         'product_id': lines.product_id.id,
        #         'name': self.asset_id.asset_item_id.name,
        #         'move_type': 'out_invoice',
        #         'quantity': lines.product_qty,
        #         'price_unit': lines.unit_price,
        #         'price_subtotal': lines.price_subtotal
        #     }) for lines in self.repair_id.repair_line_ids if lines.repair_action != 'remove']
        # })
        # print("WWWW")
        # self.repair_id.is_invoice = True

