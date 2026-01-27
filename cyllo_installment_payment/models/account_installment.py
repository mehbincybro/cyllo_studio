# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AccountInstallment(models.Model):
    """For Installment Details: this will show inside the
    new tab installment details in invoice."""
    _name = 'account.installment'
    _description = 'Account Installment'
    _rec_name = 'name'

    name = fields.Char('Description', required=True)
    payment_date = fields.Date('Payment Date', help='Date for paying installment')
    sequence = fields.Integer('Sequence', default=1)
    pay_amount = fields.Float(string='Payment Amount', help='Amount for payment')
    state = fields.Selection(selection=[('draft', 'Draft'), ('paid', 'Paid'), ('cancel', 'Cancelled')], string='Status',
                             readonly=True, copy=False, tracking=True, default='draft')
    move_id = fields.Many2one('account.move', string='Invoice')
    ready_to_pay = fields.Boolean('Ready to Pay', default=False)
    is_advance = fields.Boolean('Advance', default=False)

    def action_create_payment(self):
        """Open installment payment wizards"""
        action = {
            "name": _("Installment Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "installment.payment",
            "type": "ir.actions.act_window",
            "target": "new"
        }
        return action
