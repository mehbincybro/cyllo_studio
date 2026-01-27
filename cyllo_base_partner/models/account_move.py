# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    """Customization of the account.move model to add partner_ids field."""
    _inherit = "account.move"

    partner_ids = fields.Many2many('res.partner')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Onchange method triggered when the partner_id field changes."""
        if self.move_type == "out_invoice" or self.move_type == "out_refund":
            self.partner_ids = self.partner_id.search(
                [('is_customer', '=', True)]).ids
        elif self.move_type == "in_invoice" or self.move_type == "in_refund":
            self.partner_ids = self.partner_id.search(
                [('is_vendor', '=', True)]).ids
        else:
            self.partner_ids = self.partner_id.search([]).ids
