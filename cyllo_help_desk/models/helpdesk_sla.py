from odoo import fields, models


class HelpDeskSLAPolicy(models.Model):
    _name = "helpdesk.sla"
    _description = "HelpDesk SLA Policy"

    name = fields.Char(string="Name", help="Name for SLA policy")
    description = fields.Html(string="Description",
                              help="Description for SLA policy")
    team_id = fields.Many2one('helpdesk.team', string="Team",
                              help="Helpdesk team")
    category_ids = fields.Many2many('helpdesk.category', string="Category",
                                    help="Helpdesk categories")
    tag_ids = fields.Many2many('helpdesk.tag', string="Tag",
                               help="Helpdesk tags")
    customer_ids = fields.Many2many('res.partner', string="Customer",
                                    help="Customers who affect this SLA policy")
    target_stage = fields.Many2one('helpdesk.stage', default=lambda self: self.env.ref(
                                   'cyllo_help_desk.solved_ticket').id, string="Target stage", required=True,
                                   help="The stage in which the ticket reach to satisfy this SLA")
    within_hour = fields.Float(string="Within",
                               help="Maximum number of working hours that a ticket should take to reach the target stage")

