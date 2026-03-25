from odoo import fields, models


class MailShortcode(models.Model):
    _inherit = 'mail.shortcode'
    _rec_name = 'source'


class HelpdeskCannedResponse(models.Model):
    _name = "helpdesk.canned.response"
    _description = "Helpdesk Canned Response"
    _inherits = {"mail.shortcode": "shortcode_id"}

    shortcode_id = fields.Many2one(
        "mail.shortcode",
        required=True,
        ondelete="cascade",
        auto_join=True,
    )
