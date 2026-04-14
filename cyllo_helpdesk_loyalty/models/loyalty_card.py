# -*- coding: utf-8 -*-
from odoo import fields, models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered('helpdesk_ticket_id'):
            record.helpdesk_ticket_id.coupon_ids = [(4, record.id)]
        return records


class LoyaltyGenerateWizard(models.TransientModel):
    _inherit = 'loyalty.generate.wizard'

    def _get_coupon_values(self, partner):
        values = super()._get_coupon_values(partner)
        ticket_id = self.env.context.get('default_helpdesk_ticket_id')
        if ticket_id:
            values['helpdesk_ticket_id'] = ticket_id
        return values
