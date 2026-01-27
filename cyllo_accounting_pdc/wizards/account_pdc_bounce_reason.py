# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AccountPdcBounceReason(models.TransientModel):
    """Wizard for PDC bounce reason"""
    _name = 'account.pdc.bounce.reason'
    _description = 'PDC Bounce Reason'

    reason = fields.Char(string="Reason Displayed on Journal Entry? ", required=True, help="reason for bounce")
    bank_name = fields.Char(string="Bank", required=True, help="Name of the bank")
    cheque_reference = fields.Char(required=True, help="Reference of the cheque")
    pdc_payment_id = fields.Many2one(comodel_name='account.pdc.payment')

    def default_get(self, fields_list):
        """Default values to the wizard"""
        res = super(AccountPdcBounceReason, self).default_get(fields_list)
        pdc_payment_id = self.env["account.pdc.payment"].browse(self._context.get("active_id"))
        if pdc_payment_id:
            res.update({
                "pdc_payment_id": pdc_payment_id.id,
                "bank_name": pdc_payment_id.bank_name,
                "cheque_reference": pdc_payment_id.cheque_reference
            })
        return res

    def action_bounce(self):
        """ Button: Confirm"""
        if self.pdc_payment_id:
            self.env['account.move'].create({
                'date': self.pdc_payment_id.date,
                'invoice_date_due': self.pdc_payment_id.due_date,
                'journal_id': self.pdc_payment_id.journal_id.id,
                'line_ids': [fields.Command.create(line_vals) for line_vals in
                             self.pdc_payment_id.with_context(bounce=True)._prepare_move_line_default_vals(
                                 write_off_line_vals=None)],
                'ref': _("Cheque %s Bounced,  %s", self.cheque_reference, self.reason),
                'name': '/',
                'pdc_payment_id': self.pdc_payment_id.id,
                'move_type': 'entry',
            })._post()
            self.pdc_payment_id.write({'payment_status': 'bounced'})

