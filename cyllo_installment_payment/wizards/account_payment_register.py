# -*- coding: utf-8 -*-
from odoo import models


class AccountPaymentRegister(models.TransientModel):
    """Inherit the register payment wizards """
    _inherit = 'account.payment.register'

    def _create_payments(self):
        """When create payment updates installments"""
        res = super(AccountPaymentRegister, self)._create_payments()
        for payment in res:
            for move in payment.reconciled_invoice_ids:
                if move.installment_payment:
                    installment_ids = self.env['account.installment'].search(
                        [('move_id', '=', move.id), ('state', '=', 'draft')], order='sequence asc')
                    if installment_ids:
                        if move.payment_state == 'paid':
                            installment_ids.write({'state': 'paid'})
                        else:
                            paid_amount = payment.amount
                            for installment in installment_ids:
                                if paid_amount == 0:
                                    break
                                elif paid_amount >= installment.pay_amount:
                                    paid_amount -= installment.pay_amount
                                    installment.write({'state': 'paid'})
                                else:
                                    installment_pay_amount = installment.pay_amount - paid_amount
                                    installment.write({'pay_amount': installment_pay_amount})
                                    paid_amount = 0
        return res
