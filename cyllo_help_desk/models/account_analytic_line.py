from odoo import fields, models


class AccountAnalyticLine(models.Model):
    """ Class to add a timesheet for the employee """
    _inherit = "account.analytic.line"

    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket Id",
                                help="Helpdesk ticket Id")
