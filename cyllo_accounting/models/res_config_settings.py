# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    """Inheriting this module to install cyllo_budget_management module
    when the budget management in settings is checked """
    _inherit = 'res.config.settings'

    module_cyllo_budget_management = fields.Boolean(string="Cyllo Budget Management")
    module_cyllo_accounting_follow_up = fields.Boolean(string="Accounting Follow Up")
    module_cyllo_accounting_pdc = fields.Boolean(string="Accounting PDC")
    module_cyllo_advance_payment = fields.Boolean(string="Advance Payment")
    module_cyllo_credit_card_payment = fields.Boolean(string="Credit Card Payment")
    module_cyllo_installment_payment = fields.Boolean(string="Installment payment")
    module_cyllo_invoice_digitization = fields.Boolean(string="Invoice Digitization")
    module_cyllo_anglo_saxon = fields.Boolean(string='Anglo-Saxon Accounting', readonly=False)
    enable_saltedge = fields.Boolean(string='Salt Edge Provider',
                                     config_parameter='saltedge.enable_saltedge',
                                     help='To enable Salt Edge Provider')
    deferred_expense_journal_id = fields.Many2one('account.journal', string="journal",
                                                  domain="[('type', '=', 'general')]")
    deferred_expense_account_id = fields.Many2one('account.account', string="Deferred account")
    deferred_expense_based_on = fields.Selection([('days', 'Days'), ('months', 'Months'),
                                                  ('full_months', 'Full Months')], string='Based on', default='days',
                                                 required=True)
    deferred_revenue_journal_id = fields.Many2one('account.journal', string="journal",
                                                  domain="[('type', '=', 'general')]")
    deferred_revenue_account_id = fields.Many2one('account.account', string="Deferred account")
    deferred_revenue_based_on = fields.Selection([('days', 'Days'), ('months', 'Months'),
                                                  ('full_months', 'Full Months')], string='Based on', default='days',
                                                 required=True)

    saltedge_app_id = fields.Char(
        string='App ID',
        config_parameter='saltedge.saltedge_app_id',
        help='To save Salt Edge App Id')
    saltedge_secret_key = fields.Char(
        string='Secret Key',
        config_parameter='saltedge.saltedge_secret_key',
        help='To save Salt Edge Secret Key')
    include_fake_providers = fields.Boolean(
        string='Include Fake providers',
        config_parameter='saltedge.include_fake_providers',
        help='Include fake accounts - For testing purpose')

    def onchange_module(self, field_value, module_name):
        # Intercept only your module
        if module_name == 'module_cyllo_accounting_pdc' and not field_value:
            if 'account.pdc.payment' in self.env.registry.models:
                pdc_exists = self.env['account.pdc.payment'].sudo().search_count([])
                if pdc_exists:
                    raise UserError(
                        _("You cannot disable Accounting PDC because PDC payments exist.")
                    )
        return super().onchange_module(field_value, module_name)
