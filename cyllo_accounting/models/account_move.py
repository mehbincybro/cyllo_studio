# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountMove(models.Model):
    """Inheriting account.move for adding new functionalities"""
    _inherit = 'account.move'

    # -------------------- Assets --------------------------------
    residual_amount = fields.Monetary(string='Residual', help='For changing the amount residual')
    asset_id = fields.Many2one('account.asset.asset', index=True, ondelete='cascade',
                               copy=False, domain="[('company_id', '=', company_id)]")
    asset_date = fields.Date()
    asset_end_date = fields.Date('End Date', help="End Date of Asset")
    total_residual = fields.Float(compute='_compute_total_residual', store=True)
    asset_amount = fields.Float()
    asset_residual_amount = fields.Float(string='Residual Amount', compute='_compute_total_residual', store=True)
    asset_count = fields.Integer(string='Asset Moves', compute='_compute_asset_count')
    set_asset_move = fields.Boolean()
    check_increment = fields.Boolean('Check Increment move', default=False)
    asset_ids = fields.One2many('account.asset.asset', string='Assets', compute="_compute_asset_count")
    asset_type = fields.Char(compute="_compute_asset_count")
    asset_days = fields.Integer(copy=False)
    # -------------------- Multi Payments --------------------------------
    create_from_payment = fields.Boolean('Create Move From Payment', default=False)

    @api.depends('asset_id', 'asset_id.residual_value', 'asset_id.cum_residual_amount')
    def _compute_total_residual(self):
        """Calculate Asset Amounts"""
        for rec in self:
            rec.total_residual = 0
            rec.asset_residual_amount = 0
            depreciated = 0
            remaining = rec.asset_id.total_value - rec.asset_id.not_depreciable_value + rec.asset_id.gross_value
            for move in rec.asset_id.depreciation_move_ids.sorted(lambda x: (x.asset_date, x._origin.id)):
                remaining -= move.asset_amount
                depreciated += move.asset_amount
                move.asset_residual_amount = depreciated
                move.total_residual = remaining

    @api.depends('line_ids.asset_ids')
    def _compute_asset_count(self):
        """Compute assets linked to the move"""
        for record in self:
            record.asset_ids = record.line_ids.asset_ids
            record.asset_count = len(record.asset_ids)
            record.asset_type = record.asset_ids[:1].asset_type

    def action_get_asset_moves(self):
        """Smart button for the asset revenues/expenses"""
        if self.move_type == 'out_invoice':
            return {
                'name': _("Deferred Revenues"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.asset.asset',
                'view_mode': 'tree,form',
                'target': 'current',
                'views': [(self.env.ref('cyllo_accounting.view_account_asset_asset_deferred_revenue_tree').id, 'tree'),
                          (self.env.ref('cyllo_accounting.view_account_asset_asset_deferred_revenue_form').id, 'form')],
                'domain': [('id', 'in', self.asset_ids.ids), ('asset_type', '=', 'revenue')],
                'context': {'default_asset_type': 'revenue', 'create': False},
            }
        elif self.move_type == 'in_invoice':
            return {
                'name': _("Deferred Expenses"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.asset.asset',
                'view_mode': 'tree,form',
                'target': 'current',
                'views': [(self.env.ref('cyllo_accounting.view_account_asset_asset_deferred_expense_tree').id, 'tree'),
                          (self.env.ref('cyllo_accounting.view_account_asset_asset_deferred_expense_form').id, 'form')],
                'domain': [('id', 'in', self.asset_ids.ids), ('asset_type', '=', 'expense')],
                'context': {'default_asset_type': 'expense', 'create': False}
            }
        return None

    @api.onchange('amount_residual', 'payment_state')
    def _onchange_amount_residual(self):
        """Assign amount_residual to residual_amount for multi invoice payments"""
        for rec in self.filtered(lambda x: x.amount_residual):
            rec.residual_amount = rec.amount_residual

    def _prepare_moves(self, vals):
        """Create Moves based on the asset values"""
        asset_id = vals['asset_id']
        current_currency = asset_id.currency_id
        date = vals.get('date', fields.Date.context_today(self))
        amount_currency = vals['amount']
        company_currency_id = asset_id.company_id.currency_id
        dec_place = company_currency_id.decimal_places
        amount = current_currency._convert(amount_currency, company_currency_id, asset_id.company_id, date)
        return {
            'date': vals['asset_date'],
            'journal_id': asset_id.journal_id.id,
            'line_ids': [fields.Command.create({
                'name': asset_id.name,
                'account_id': asset_id.account_id.id,
                'credit': 0.0 if float_compare(amount, 0.0, precision_digits=dec_place) > 0 else -amount,
                'debit': amount if float_compare(amount, 0.0, precision_digits=dec_place) > 0 else 0.0,
                'currency_id': current_currency.id,
                'amount_currency': amount_currency,
            }), fields.Command.create({
                'name': asset_id.name,
                'account_id': asset_id.expense_account_id.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=dec_place) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=dec_place) > 0 else 0.0,
                'currency_id': current_currency.id,
                'amount_currency': -amount_currency,
            })],
            'asset_id': vals['asset_id'].id,
            'ref': _("%s: Depreciation", asset_id.name),
            'asset_date': vals['asset_date'],
            'asset_end_date': vals['asset_end_date'],
            'asset_days': vals['asset_days'],
            'asset_amount': abs(vals['amount']),
            'name': '/',
            'move_type': 'entry',
            'invoice_date_due': vals['asset_date'],
            'currency_id': current_currency.id,
            'check_increment': True if 'check_increment' in vals and vals['check_increment'] else False,
        }

    def create_asset_moves(self):
        """Creates deferred revenue or expense from invoice lines"""
        for line in self.filtered(lambda x: x.is_invoice()).line_ids:
            if line.asset and line.account_id and line.price_total > 0 and not line.asset_ids:
                if not line.name:
                    raise UserError(
                        _('There is no label in the journal items of {account}').format(
                            account=line.account_id.display_name))

                journal_id = self.env['account.journal'].search(
                    [('type', '=', 'general'), ('company_id', '=', line.company_id.id)], limit=1)
                if line.move_id.move_type == 'out_invoice':
                    account_id = self.env['account.account'].search(
                        [('account_type', '=', 'liability_current'),
                         ('company_id', '=', line.company_id.id)], limit=1)
                else:
                    account_id = self.env['account.account'].search(
                        [('account_type', 'in', ('asset_current', 'asset_prepayments')),
                         ('company_id', '=', line.company_id.id)], limit=1)
                self.env['account.asset.asset'].create({
                    'name': line.name,
                    'asset_type_id': line.asset_type_id.id if line.asset_type_id else False,
                    'journal_id': line.asset_type_id.journal_id.id if line.asset_type_id else journal_id.id,
                    'account_id': line.asset_type_id.account_id.id if line.asset_type_id else account_id.id,
                    'expense_account_id': line.asset_type_id.expense_account_id.id
                    if line.asset_type_id else line.account_id.id,
                    'company_id': line.company_id.id,
                    'date': line.move_id.invoice_date,
                    'first_recognition_date': line.move_id.invoice_date,
                    'state': 'draft',
                    'invoice_line_ids': [fields.Command.set(line.ids)],
                    'asset_type': 'revenue' if line.move_id.move_type == 'out_invoice' else 'expense',
                    'original_value': line.price_unit,
                    'total_value': line.price_unit,
                    'computation_method': line.asset_type_id.computation_method if line.asset_type_id else 'no_prorata',
                    'prorata_date': line.move_id.invoice_date
                    if line.asset_type_id and line.asset_type_id.computation_method != 'no_prorata' else False,
                })

    def _post(self, soft=True):
        """When confirming the invoice create asset"""
        posted_moves = super()._post(soft)
        posted_moves.create_asset_moves()
        return posted_moves

    def button_cancel(self):
        """Override: For cancel the assets """
        res = super(AccountMove, self).button_cancel()
        self.env['account.asset.asset'].sudo().search([('invoice_line_ids.move_id', 'in', self.ids)]).write(
            {'active': False})
        return res

    def button_draft(self):
        """Override: button_draft"""
        res = super(AccountMove, self).button_draft()
        for move in self:
            for asset in move.asset_ids:
                if asset.state != 'draft':
                    raise UserError(_('You cannot reset to draft, The related asset is already posted'))
                else:
                    asset.unlink()
        return res
