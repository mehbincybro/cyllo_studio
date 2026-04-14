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
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    coupon_ids = fields.Many2many('loyalty.card', string='Coupons')
    coupon_count = fields.Integer(compute='_compute_coupon_count')

    @api.depends('coupon_ids')
    def _compute_coupon_count(self):
        for ticket in self:
            ticket.coupon_count = len(ticket.coupon_ids)

    def action_create_coupon(self):
        self.ensure_one()
        program = self.env['loyalty.program'].search(
            [('program_type', '=', 'coupons')], limit=1)
        if not program:
            raise UserError(
                _("No coupon program is configured. Create a coupon loyalty program first."))

        action = self.env["ir.actions.actions"]._for_xml_id(
            "loyalty.loyalty_generate_wizard_action")
        action['context'] = {
            'active_id': program.id,
            'default_program_id': program.id,
            'default_mode': 'selected' if self.customer_id else 'anonymous',
            'default_customer_ids': [
                (6, 0, [self.customer_id.id])] if self.customer_id else [],
            'default_coupon_qty': 1,
            'default_helpdesk_ticket_id': self.id,
        }
        self.message_post(body=_("Coupon generation initiated."))
        return action

    def action_view_coupons(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "loyalty.loyalty_card_action")
        action['view_mode'] = 'list,form'
        action['domain'] = [('id', 'in', self.coupon_ids.ids)]
        return action
