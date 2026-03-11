from odoo import fields, models


class HelpDeskStage(models.Model):
    _name = "helpdesk.stage"
    _description = "HelpDesk Stage"

    name = fields.Char(string="Stage", ondelete='restrict',
                       help="Add more stages")
    sequence = fields.Integer(string="Sequence", default=1,
                              help="Order of stage")
    is_closed = fields.Boolean(string="Is Closed Stage", help="Tick if it is closed stage")
    fold = fields.Boolean(string="Fold", help="Stage folded in kanban")
