from odoo import fields, models


class HelpDeskTag(models.Model):
    _name = "helpdesk.tag"
    _description = "HelpDesk Tag"

    name = fields.Char(string="Tag", ondelete='restrict',
                       help="Indicating from which the ticket generated")
    description = fields.Html(string="Description", help="Tag description")
    sla_id = fields.Many2one('helpdesk.sla', string="SLA policy id")

