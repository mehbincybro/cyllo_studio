# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models, fields

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payments(self):
        payments = super()._create_payments()
        loan_id = self.env.context.get('loan_id')
        loan_repayment_id = self.env.context.get('loan_repayment_id')
        
        if loan_id:
            loan_ids = loan_id.ids if hasattr(loan_id, 'ids') else loan_id
            loan = self.env['loan.loan'].browse(loan_ids)
            for l in loan:
                l.payment_ids = [(4, p.id) for p in payments]
            
        if loan_repayment_id:
            rep_ids = loan_repayment_id.ids if hasattr(loan_repayment_id, 'ids') else loan_repayment_id
            repayments = self.env['loan.repayment'].browse(rep_ids)
            for repayment in repayments:
                repayment.write({
                    'state': 'paid',
                    'amount_paid': repayment.total_amount,
                    'payment_date': fields.Date.today(),
                })
            for loan in repayments.mapped('loan_id'):
                if hasattr(loan, '_check_running_state'):
                    loan._check_running_state()
            
        return payments
