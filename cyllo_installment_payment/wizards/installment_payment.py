# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class InstallmentPayment(models.TransientModel):
    """Wizard for Installment Payment"""
    _name = 'installment.payment'
    _description = 'Installment Payment'

    communication = fields.Char(string="Memo", help="Reference")
    pay_amount = fields.Float(string="Installment Pay Amount", help="Installment amount to pay")
    currency_id = fields.Many2one(comodel_name="res.currency")
    partner_id = fields.Many2one(comodel_name="res.partner")
    date = fields.Datetime(string="Payment Date")
    company_id = fields.Many2one("res.company")
    journal_id = fields.Many2one("account.journal", compute="_compute_journal_id", store=True, readonly=False,
                                 precompute=True, check_company=True, help="Journal for the payment")
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method', store=True,
                                             compute='_compute_payment_method_line_id',
                                             help="Payment method line for the payment")

    def default_get(self, fields_list):
        """Default values to the wizards"""
        res = super(InstallmentPayment, self).default_get(fields_list)
        res["currency_id"] = self.env.user.company_id.currency_id.id
        res["company_id"] = self.env.user.company_id.id
        installment_id = self.env["account.installment"].browse(self._context.get("active_id"))
        if installment_id:
            res["communication"] = installment_id.move_id.name
            res["pay_amount"] = installment_id.pay_amount
            res["partner_id"] = installment_id.move_id.partner_id.id
            res["currency_id"] = installment_id.move_id.currency_id.id if installment_id.move_id.currency_id \
                else self.env.user.company_id.currency_id.id
            res["company_id"] = installment_id.move_id.company_id.id if installment_id.move_id.company_id \
                else self.env.user.company_id.id
            res["date"] = installment_id.payment_date
        return res

    @api.depends('company_id')
    def _compute_journal_id(self):
        """Compute the journal"""
        for wizard in self:
            wizard.journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(wizard.company_id),
                ('type', 'in', ('bank', 'cash'))], limit=1)

    @api.depends('journal_id')
    def _compute_payment_method_line_id(self):
        """Compute the payment method line based on the journal"""
        for wizard in self:
            if wizard.journal_id:
                if self._context.get("type") == 'sale':
                    available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines('inbound')
                else:
                    available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines('outbound')
            else:
                available_payment_method_lines = False

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False

    def action_validate_payment(self):
        """Button: Create Payment , Creates new payment with wizards values"""
        installment_id = self.env["account.installment"].browse(self._context.get("active_id"))
        payment = self.env['account.payment'].create({
            'partner_id': installment_id.move_id.partner_id.commercial_partner_id.id,
            'company_id': self.company_id.id if self.company_id else self.env.user.company_id.id,
            'date': self.date,
            'amount': self.pay_amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'ref': _("%s - Installment Payment", installment_id.move_id.name) if not installment_id.is_advance else _(
                "%s - Advance Payment", installment_id.move_id.name),
        })
        payment.action_post()
        move_lines = payment.line_ids
        for line in move_lines:
            installment_id.move_id.js_assign_outstanding_line(line.id)
        installment_id.write({'state': 'paid'})
