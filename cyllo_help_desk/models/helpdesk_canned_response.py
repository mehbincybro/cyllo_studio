# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskCannedResponse(models.Model):
    _name = 'helpdesk.canned.response'
    _inherit = 'mail.shortcode'
    _description = 'Helpdesk Canned Response'

    # Direct implementation using mail.shortcode fields to avoid validation errors
    source = fields.Char(string='Shortcut', required=True, help="Type this shortcut with a ':' prefix in chatter to use the response.")
    substitution = fields.Html(string='Substitution', required=True, help="The content that will replace the shortcut.")
    shortcode_type = fields.Selection([('substitution', 'Substitution'), ('image', 'Image')], default='substitution', required=True)
    
    # name is used for display in many2one, etc.
    name = fields.Char(related='source', readonly=False, store=True)
