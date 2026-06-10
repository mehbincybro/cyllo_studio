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

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """
        Automatically create intercompany vendor bills when customer invoices
        are posted.

        For invoices originating from intercompany Sale Orders, the system
        locates the linked Purchase Order in the other company and creates
        the corresponding vendor bill if one does not already exist.
        Duplicate bill creation is prevented through origin checks.
        """
        res = super().action_post()
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_stock.intercompany_transactions'
        )
        create_bills = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_stock.create_vendor_bills'
        )
        if not enabled or not create_bills:
            return res
        invoices = self.filtered(lambda m: m.move_type == 'out_invoice')
        for invoice in invoices:
            sale_order = invoice.invoice_line_ids.sale_line_ids.order_id[:1]
            if not sale_order:
                continue
            purchase_order = sale_order.sudo().intercompany_purchase_order_id
            if not purchase_order:
                continue
            existing_bills = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('invoice_origin', '=', purchase_order.name),
                ('company_id', '=', purchase_order.company_id.id),
            ], limit=1)
            if existing_bills:
                continue
            purchase_order.with_company(
                purchase_order.company_id
            ).sudo().action_create_invoice()

        return res
