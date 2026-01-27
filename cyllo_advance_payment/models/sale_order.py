# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    """Inherit sale.order for adding advance payment option"""
    _inherit = "sale.order"

    advance_payment_ids = fields.One2many(comodel_name="account.payment", inverse_name="sale_id",
                                          help="Advance payments related to this sale order")
    total_advance_amount = fields.Float(compute="_compute_total_advance_amount", store=True,
                                        help="The total advance amount had been paid")

    @api.depends('advance_payment_ids', 'advance_payment_ids.amount')
    def _compute_total_advance_amount(self):
        """Compute total advance payment amount"""
        for rec in self:
            rec.total_advance_amount = 0
            if rec.advance_payment_ids:
                rec.total_advance_amount = sum(rec.advance_payment_ids.mapped('amount'))

    def action_advance_payment(self):
        """ Open Advance Payment Wizard"""
        return {
            "name": _("Advance Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "advance.payment",
            "type": "ir.actions.act_window",
            "context": {"type": 'sale'},
            "target": "new"
        }
