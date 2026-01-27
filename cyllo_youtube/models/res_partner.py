# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ResPartner(models.Model):
    """
    Inherits the base res.partner model and adds Tasks information in
    the partner form.
    """
    _inherit = 'res.partner'

    feed_id = fields.Many2one('social.media.feed', string='Related Feed', help="The feed where this contact created.")
    unique_yt_number = fields.Char(string='Feed', help="Unique identifier for the partner's feed on YouTube.")
    youtube_account_id = fields.Many2one('youtube.account', string='Related Youtube Account',
                                         help="Account related to partner")
