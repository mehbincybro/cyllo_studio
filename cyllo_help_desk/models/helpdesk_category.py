from odoo import fields, models


class HelpDeskCategory(models.Model):
    _name = "helpdesk.category"
    _description = "HelpDesk Category"

    name = fields.Char(string="Category", ondelete='restrict',
                       help="Ticket category")
    parent_id = fields.Many2one('helpdesk.category', string="Parent",
                                help="Parent of the category")
    description = fields.Html(string="Description",
                              help="Category description")
    sla_id = fields.Many2one('helpdesk.sla', string="SLA policy id")
