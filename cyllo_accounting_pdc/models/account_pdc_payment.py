# -*- coding: utf-8 -*-
from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, formatLang


class AccountPdcPayment(models.Model):
    """New model for Pdc payment"""
    _name = "account.pdc.payment"
    _inherits = {'account.move': 'move_id'}
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "PDC Payments"
    _order = "date desc, name desc"
    _check_company_auto = True

    move_id = fields.Many2one(comodel_name='account.move', string='Journal Entry', readonly=True, ondelete='cascade',
                              check_company=True)
    payment_type = fields.Selection([('outbound', 'Send'), ('inbound', 'Receive')], default='inbound',
                                    required=True, tracking=True)
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_currency_id', store=True,
                                  readonly=False, precompute=True, help="The payment's currency.")
    payment_reference = fields.Char(copy=False, tracking=True, help="Reference of the document used to issue "
                                                                    "this payment. Eg. check number, file name, etc.")
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], default='customer',
                                    tracking=True, required=True)
    payment_status = fields.Selection(selection=[('draft', 'Draft'), ('registered', 'Registered'),
                                                 ('bounced', 'Bounced'), ('posted', 'Accepted'),
                                                 ('cancelled', 'cancelled'),], default='draft')
    partner_id = fields.Many2one(comodel_name='res.partner', string="Customer/Vendor", ondelete='restrict',
                                 domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
                                 tracking=True, check_company=True)
    bank_name = fields.Char(string="Bank", required=True, help="Name of the bank")
    cheque_reference = fields.Char(required=True, help="Reference of the cheque")
    due_date = fields.Date(required=True, default=fields.Date.context_today)
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             readonly=True, store=True, copy=False,
                                             compute='_compute_payment_method_line_id',
                                             domain="[('id', 'in', available_payment_method_line_ids)]",
                                             help="PDC payment method set as default")
    destination_account_id = fields.Many2one(
        comodel_name='account.account', store=True, readonly=False, compute='_compute_destination_account_id',
        domain="[('account_type', 'in', ('asset_receivable', 'liability_payable'))]", check_company=True)
    outstanding_account_id = fields.Many2one(comodel_name='account.account', store=True,
                                             compute='_compute_outstanding_account_id', check_company=True)
    pdc_account_id = fields.Many2one(comodel_name='account.account', string="PDC Account", store=True,
                                     compute='_compute_pdc_account_id', check_company=True)
    pdc_move_count = fields.Integer(string="# Journal Entries", compute="_compute_pdc_move_count")

    def _compute_pdc_move_count(self):
        """Compute PDC move count"""
        for rec in self:
            rec.pdc_move_count = self.env['account.move'].search_count(
                [('pdc_payment_id', '=', rec.id)])

    @api.depends('journal_id', 'partner_id', 'partner_type')
    def _compute_destination_account_id(self):
        """Finds the destination account"""
        self.destination_account_id = False
        for pay in self:
            if pay.partner_type == 'customer':
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(
                        pay.company_id).property_account_receivable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(
                            pay.company_id),
                        ('account_type', '=', 'asset_receivable'),
                        ('deprecated', '=', False)], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(
                        pay.company_id).property_account_payable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(
                            pay.company_id),
                        ('account_type', '=', 'liability_payable'),
                        ('deprecated', '=', False),], limit=1)

    @api.depends('journal_id', 'partner_id', 'partner_type')
    def _compute_pdc_account_id(self):
        """Finds the PDC account"""
        for pay in self:
            pay.pdc_account_id = False
            pdc_account = self.env['account.account'].search([
                *self.env['account.account']._check_company_domain(
                    pay.company_id), ('account_type', '=', 'asset_current'),
                ('name', '=', 'PDC Payment'), ('deprecated', '=', False)],
                limit=1)
            if pdc_account:
                pay.pdc_account_id = pdc_account

    @api.depends('journal_id', 'payment_type', 'payment_method_line_id')
    def _compute_outstanding_account_id(self):
        """Finds the outstanding account"""
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_debit_account_id)
            elif pay.payment_type == 'outbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_credit_account_id)
            else:
                pay.outstanding_account_id = False

    @api.depends('payment_type', 'journal_id', 'currency_id')
    def _compute_payment_method_line_id(self):
        """ Compute the 'payment_method_line_id' field.
        This field is not computed in '_compute_payment_method_line_fields'
         because it's a stored editable one.
        """
        for rec in self:
            if rec.journal_id:
                available_payment_method_lines = rec.journal_id._get_available_payment_method_lines(
                    rec.payment_type).filtered(lambda x: x.code == 'pdc_payment')
            else:
                available_payment_method_lines = False
            # Select the first available one by default.
            if available_payment_method_lines:
                rec.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                rec.payment_method_line_id = False

    @api.depends('journal_id')
    def _compute_currency_id(self):
        """Find currency"""
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    def action_post(self):
        """ draft -> posted """
        self.ensure_one()
        self.move_id._post(soft=False)
        self.write({'payment_status': 'registered'})

    def action_done(self):
        """Button: Done"""
        self.ensure_one()
        move_vals = {
            'date': self.date,
            'invoice_date_due': self.due_date,
            'journal_id': self.journal_id.id,
            'line_ids': [fields.Command.create(line_vals) for line_vals in
                         self.with_context(done=True)._prepare_move_line_default_vals(write_off_line_vals=None)],
            'ref': _("Cheque %s Accepted", self.cheque_reference),
            'name': '/',
            'pdc_payment_id': self.id,
            'move_type': 'entry',
        }
        deposit_move = self.env['account.move'].create(move_vals)
        deposit_move._post()
        self.write({'payment_status': 'posted'})

    def action_deposit(self):
        """Button: Deposit"""
        self.ensure_one()
        move_vals = {
            'date': self.date,
            'invoice_date_due': self.due_date,
            'journal_id': self.journal_id.id,
            'line_ids': [fields.Command.create(line_vals) for line_vals in
                         self._prepare_move_line_default_vals(write_off_line_vals=None)],
            'ref': _("Cheque %s Deposited", self.cheque_reference),
            'name': '/',
            'pdc_payment_id': self.id,
            'move_type': 'entry',
        }
        deposit_move = self.env['account.move'].create(move_vals)
        deposit_move._post()
        self.write({'payment_status': 'registered'})

    def action_draft(self):
        """Button: Draft"""
        self.ensure_one()
        self.move_id.button_draft()
        self.write({'payment_status': 'draft'})

    def action_cancel(self):
        """Button: Cancel"""
        self.move_id.button_cancel()
        self.write({'payment_status': 'cancelled'})

    def _seek_for_lines(self):
        """ Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines."""
        self.ensure_one()
        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']
        for line in self.move_id.line_ids:
            if line.account_id in self._get_valid_liquidity_accounts():
                liquidity_lines += line
            elif line.account_id.account_type in ('asset_receivable', 'liability_payable') or line.account_id == self.company_id.transfer_account_id:
                counterpart_lines += line
            else:
                writeoff_lines += line
        return liquidity_lines, counterpart_lines, writeoff_lines

    def _get_valid_liquidity_accounts(self):
        """Get validit liquidity accounts"""
        return (
            self.journal_id.default_account_id,
            self.payment_method_line_id.payment_account_id,
            self.journal_id.company_id.account_journal_payment_debit_account_id,
            self.journal_id.company_id.account_journal_payment_credit_account_id,
            self.journal_id.inbound_payment_method_line_ids.payment_account_id,
            self.journal_id.outbound_payment_method_line_ids.payment_account_id,
        )

    def _get_aml_default_display_map(self):
        """Get default display"""
        return {
            ('outbound', 'customer'): _("Customer Reimbursement"),
            ('inbound', 'customer'): _("Customer Payment"),
            ('outbound', 'supplier'): _("Vendor Payment"),
            ('inbound', 'supplier'): _("Vendor Reimbursement"),
        }

    def _get_aml_default_display_name_list(self):
        """ Hook allowing custom values when constructing the default label to
         set on the journal items."""
        self.ensure_one()
        display_map = self._get_aml_default_display_map()
        values = [
            ('label', display_map[(self.payment_type, self.partner_type)]),
            ('sep', ' '),
            ('amount', formatLang(self.env, self.amount, currency_obj=self.currency_id)),
        ]
        if self.partner_id:
            values += [
                ('sep', ' - '),
                ('partner', self.partner_id.display_name),
            ]
        values += [
            ('sep', ' - '),
            ('date', format_date(self.env, fields.Date.to_string(self.date))),
        ]
        return values

    def _get_liquidity_aml_display_name_list(self):
        """ Hook allowing custom values when constructing the label to set on
        the liquidity line."""
        self.ensure_one()
        if self.payment_reference:
            return [('reference', self.payment_reference)]
        else:
            return self._get_aml_default_display_name_list()

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Prepare the dictionary to create the default account.move.lines
        for the current payment."""
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}
        if not self.pdc_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding"
                " payments/receipts account set either on the company or the"
                " %s payment method in the %s journal.",
                self.payment_method_line_id.name, self.journal_id.display_name)
            )
        # Compute amounts.
        write_off_line_vals_list = write_off_line_vals or []
        write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
        write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)
        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
        else:
            liquidity_amount_currency = 0.0
        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id
        # Compute a default label to set on the journal items.
        liquidity_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
        counterpart_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
        if self._context.get('bounce'):
            line_vals_list = [
                # Liquidity line.
                {
                    'name': counterpart_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                    'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.pdc_account_id.id,
                },
                {
                    'name': liquidity_line_name,
                    'date_maturity': self.date,
                    'amount_currency': liquidity_amount_currency,
                    'currency_id': currency_id,
                    'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                    'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.destination_account_id.id,
                },
            ]
        elif self._context.get('done'):
            account_deposit = self.env['account.account'].search([
                *self.env['account.account']._check_company_domain(
                    self.company_id), ('account_type', '=', 'asset_cash')],
                limit=1)
            line_vals_list = [
                # Liquidity line.
                {
                    'name': counterpart_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                    'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.pdc_account_id.id,
                },
                {
                    'name': liquidity_line_name,
                    'date_maturity': self.date,
                    'amount_currency': liquidity_amount_currency,
                    'currency_id': currency_id,
                    'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                    'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': account_deposit.id,
                },
            ]
        else:
            line_vals_list = [
                # Liquidity line.
                {
                    'name': liquidity_line_name,
                    'date_maturity': self.date,
                    'amount_currency': liquidity_amount_currency,
                    'currency_id': currency_id,
                    'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                    'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.pdc_account_id.id,
                },
                # Receivable / Payable.
                {
                    'name': counterpart_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                    'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.destination_account_id.id,
                },
            ]
        return line_vals_list + write_off_line_vals_list

    @api.constrains('payment_method_line_id')
    def _check_payment_method_line_id(self):
        """ Ensure the 'payment_method_line_id' field is not null.
        Can't be done using the regular 'required=True' because the field is a
        computed editable stored one.
        """
        for pay in self:
            if not pay.payment_method_line_id:
                raise ValidationError(_(
                    "Please define a payment method line on your payment."))

    def new(self, values=None, origin=None, ref=None):
        """Method: new()"""
        payment = super().new(values, origin, ref)
        if not payment.journal_id and not payment.default_get(['journal_id']):  # might not be computed because declared by inheritance
            payment.move_id.pdc_payment_id = payment
            payment.move_id.with_context(pdc_payment=True)._compute_journal_id()
        return payment

    @api.model_create_multi
    def create(self, vals_list):
        """Override create()"""
        write_off_line_vals_list = []
        for vals in vals_list:
            write_off_line_vals_list.append(vals.pop(
                'write_off_line_vals', None))
            vals['move_type'] = 'entry'
        payments = super().create([{
            'name': False,
            'journal_id': self.move_id.with_context(is_payment=True)._search_default_journal().id,
            **vals,
        } for vals in vals_list])
        for i, pay in enumerate(payments):
            write_off_line_vals = write_off_line_vals_list[i]
            to_write = {'pdc_payment_id': pay.id, 'invoice_date_due': pay.due_date}
            for k, v in vals_list[i].items():
                if k in self._fields and self._fields[k].store and k in pay.move_id._fields and pay.move_id._fields[k].store:
                    to_write[k] = v
            if 'line_ids' not in vals_list[i]:
                to_write['line_ids'] = [fields.Command.create(line_vals) for line_vals in
                                        pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)]
            pay.move_id.write(to_write)
            self.env.add_to_compute(self.env['account.move']._fields['name'], pay.move_id)
        payments.invalidate_recordset(fnames=['name'])
        return payments

    def write(self, vals):
        """Override write()"""
        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    def unlink(self):
        """Override unlink()"""
        moves = self.with_context(force_delete=True).move_id
        res = super().unlink()
        moves.unlink()
        return res

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        """Fields to synchronize"""
        return (
            'date', 'amount', 'payment_type', 'partner_type',
            'payment_reference', 'currency_id', 'partner_id',
            'destination_account_id', 'partner_bank_id', 'journal_id'
        )

    def _synchronize_to_moves(self, changed_fields):
        """ Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on
        account.payment.
        """
        if self._context.get('skip_account_move_synchronization'):
            return
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return
        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            write_off_line_vals = []
            if liquidity_lines and counterpart_lines and writeoff_lines:
                write_off_line_vals.append({
                    'name': writeoff_lines[0].name,
                    'account_id': writeoff_lines[0].account_id.id,
                    'partner_id': writeoff_lines[0].partner_id.id,
                    'currency_id': writeoff_lines[0].currency_id.id,
                    'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
                    'balance': sum(writeoff_lines.mapped('balance')),
                })
            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
            line_ids_commands = [
                Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
            ]
            for line in writeoff_lines:
                line_ids_commands.append(fields.Command.delete(line.id))
            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append(fields.Command.create(extra_line_vals))
            pay.move_id\
                .with_context(skip_invoice_sync=True)\
                .write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                })

    def action_open_journal_entry(self):
        """ Redirect the user to this payment journal."""
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'tree,form',
            'domain': [('pdc_payment_id', '=', self.id)]
        }

    def _get_payment_receipt_report_values(self):
        """ Get the extra values when rendering the PDC Payment Receipt PDF
        report"""
        self.ensure_one()
        return {
            'display_invoices': True,
        }
