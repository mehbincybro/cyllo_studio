from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)


class AccountMove(models.Model):
    _inherit = 'account.move'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered('helpdesk_ticket_id'):
            record.helpdesk_ticket_id.picking_ids = [(4, record.id)]
        return records


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
