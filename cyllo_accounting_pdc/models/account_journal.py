# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    """Inherits account.journal for adding payment methods for pdc"""
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        """Adding new outbound payment method for the type bank"""
        res = super()._default_outbound_payment_methods()
        if self.type == 'bank':
            res |= self.env.ref('cyllo_accounting_pdc.account_payment_method_pdc_outbound')
        return res

    def _default_inbound_payment_methods(self):
        """Adding new inbound payment method for the type bank"""
        res = super()._default_inbound_payment_methods()
        if self.type == 'bank':
            res |= self.env.ref('cyllo_accounting_pdc.account_payment_method_pdc_inbound')
        return res

    def _compute_available_payment_method_ids(self):
        """Adding new payment methods to available payment methods"""
        res = super()._compute_available_payment_method_ids()
        for rec in self:
            credit_payment_methods = self.env['account.payment.method'].search([('code', '=', 'pdc_payment')])
            if rec.type == 'bank':
                for method in credit_payment_methods:
                    rec.available_payment_method_ids = [fields.Command.link(method.id)]
        return res
