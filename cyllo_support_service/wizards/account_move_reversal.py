# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveReversal(models.TransientModel):
    """ Class to add credit note for the sale order """
    _inherit = 'account.move.reversal'

    sale_order_id = fields.Many2one('sale.order', help="Sale order", readonly=True)
    ticket_id = fields.Many2one('support.service.ticket', string="Support Service Ticket")
    account_move_ids = fields.Many2many('account.move', 'account_moves')
    move_ids = fields.Many2many('account.move', 'account_move_reversal_move', 'reversal_id', 'move_id',
                                domain="[('state', '=', 'posted'), ('id', 'in', account_move_ids)]")

    @api.onchange('account_move_ids')
    def _onchange_account_move_ids(self):
        """
        Update the 'account_move_ids' field based on the invoice IDs of the related sale order.

        This onchange method is triggered when the 'account_move_ids' field is changed.
        It sets 'account_move_ids' to the invoice IDs of the related sale order.

        :return: None
        """
        self.account_move_ids = [(6, 0, self.sale_order_id.invoice_ids.ids)]
