# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AccountPaymentRegister(models.TransientModel):
    """Inherit the register payment wizard """
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        """Adding more features to the wizard"""
        payments = self._create_payments()
        if self._context.get('dont_redirect_to_payments'):
            return True
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
            if payments.partner_id:
                if payments.reconciled_invoice_ids:
                    payments.move_ids = [fields.Command.set(payments.reconciled_invoice_ids.ids)]
                if payments.reconciled_bill_ids:
                    payments.move_ids = [fields.Command.set(payments.reconciled_bill_ids.ids)]
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
            for payment in payments:
                if payment.partner_id:
                    if payment.reconciled_invoice_ids:
                        payment.move_ids = [fields.Command.set(payment.reconciled_invoice_ids.ids)]
                    if payment.reconciled_bill_ids:
                        payment.move_ids = [fields.Command.set(payment.reconciled_bill_ids.ids)]
        return action
