# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    invoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        domain="[('partner_id', '=', customer_id), ('move_type', 'in', ('out_invoice', 'out_refund'))]",
        help="Select an existing invoice related to the customer.",
    )
    invoice_line_ids = fields.Many2many(
        'account.move.line',
        string="Invoice line Items",
        help="Items belonging to the selected invoice.",
    )
    customer_invoice_count = fields.Integer(
        compute='_compute_customer_invoice_count',
        string='Customer Invoices',
    )
    refund_ids = fields.One2many(
        'account.move',
        'helpdesk_ticket_id',
        string="Refund/Credit Notes",
        domain=[('move_type', '=', 'out_refund')],
    )
    refund_count = fields.Integer(
        compute='_compute_refund_count',
        string="Refund Count",
    )

    @api.depends('refund_ids')
    def _compute_refund_count(self):
        for ticket in self:
            ticket.refund_count = len(ticket.refund_ids)

    def _compute_customer_invoice_count(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.customer_invoice_count = 0
                continue
            commercial_partner = ticket.customer_id.commercial_partner_id
            ticket.customer_invoice_count = self.env['account.move'].search_count([
                ('partner_id', 'child_of', commercial_partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund'))
            ])

    def action_view_customer_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type")
        action['domain'] = [
            ('partner_id', 'child_of',
             self.customer_id.commercial_partner_id.id),
            ('move_type', 'in', ('out_invoice', 'out_refund'))
        ]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        action['view_mode'] = 'tree'
        action['views'] = [
            (self.env.ref('account.view_out_invoice_tree').id, 'tree')]
        return action

    def action_create_refund(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("Please select an invoice first."))

        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_view_account_move_reversal")
        action['context'] = {
            'active_model': 'account.move',
            'active_ids': [self.invoice_id.id],
        }
        self.message_post(body=_("Refund/Credit Note creation initiated."))
        return action
