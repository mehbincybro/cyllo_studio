# -*- coding: utf-8 -*-
from odoo import fields, models


class YoutubeChannel(models.Model):
    """
    Model representing a Social Media YouTube Channel.
    """
    _name = "youtube.channel"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media YouTube Channel"

    name = fields.Char(string='Name Channel', required=True, help="Unique id of channel")
    youtube_account_id = fields.Many2one('youtube.account', string="Related Account", help="Related youtube account")
    youtube_number = fields.Char(string='Id of Channel', required=True, help="Unique id of channel")
    youtube_etag = fields.Char(string='Tag of Channel', required=True, help="Unique Tag of channel")
    customUrl = fields.Char(string='Url of Channel', required=True, help="Unique Url of channel")
    channel_image = fields.Binary(string="Image Channel", help="Image of channel")
    is_active = fields.Boolean(string="Active", help="Represent channel is active or not")
