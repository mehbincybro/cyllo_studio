# -*- coding: utf-8 -*-
from odoo import fields, models


class UploadVideoWizard(models.TransientModel):
    """
    Model representing a wizard for uploading a video to YouTube.
    """
    _name = 'upload.video.wizard'
    _description = 'Upload Video'

    video_path = fields.Char(string="Upload video", help="Upload the video which we want to uplaod to youtube")
    youtube_post_id = fields.Many2one('social.media.post', string="Related Youtube Post", help="Linked Youtube Post")
