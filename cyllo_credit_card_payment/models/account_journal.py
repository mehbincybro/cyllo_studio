# -*- coding: utf-8 -*-
from odoo import models, Command


class AccountJournal(models.Model):
    """Inherits account.journal."""
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        """Adding new outbound payment method for the type bank"""
        res = super()._default_outbound_payment_methods()
        if self.type == 'bank':
            res |= self.env.ref('cyllo_credit_card_payment.account_payment_method_credit')
        return res

    def _compute_available_payment_method_ids(self):
        """Adding new outbound payment method to available payment methods"""
        res = super()._compute_available_payment_method_ids()
        for rec in self:
            credit_payment_method = self.env['account.payment.method'].search([('code', '=', 'credit_payment')],
                                                                              limit=1)
            if rec.type == 'bank':
                rec.available_payment_method_ids = [Command.link(int(credit_payment_method.id))]
        return res
