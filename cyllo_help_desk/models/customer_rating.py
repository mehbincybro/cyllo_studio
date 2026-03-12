from odoo import api, fields, models


class CustomerRating(models.Model):
    _inherit = "rating.rating"

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string="Helpdesk Ticket",
        compute="_compute_helpdesk_ticket_id",
        store=True,
        readonly=True,
    )
    helpdesk_team_id = fields.Many2one(
        'helpdesk.team',
        string="Helpdesk Team",
        related='helpdesk_ticket_id.team_id',
        store=True,
        readonly=True,
    )
    helpdesk_user_id = fields.Many2one(
        'res.users',
        string="Assigned User",
        related='helpdesk_ticket_id.user_id',
        store=True,
        readonly=True,
    )
    helpdesk_stage_id = fields.Many2one(
        'helpdesk.stage',
        string="Ticket Stage",
        related='helpdesk_ticket_id.stage_id',
        store=True,
        readonly=True,
    )

    @api.depends('res_model', 'res_id')
    def _compute_helpdesk_ticket_id(self):
        for rating in self:
            if rating.res_model == 'helpdesk.ticket' and rating.res_id:
                rating.helpdesk_ticket_id = rating.res_id
            else:
                rating.helpdesk_ticket_id = False

