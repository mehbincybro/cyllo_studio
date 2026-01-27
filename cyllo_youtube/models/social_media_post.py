# -*- coding: utf-8 -*-
import requests
from odoo import _, api, fields, models
from odoo.tools.safe_eval import datetime


class SocialMediaPost(models.Model):
    """
    Inherits the social.media.post model to handle posts for different
    social media platforms.
    """
    _inherit = 'social.media.post'

    post_on_youtube = fields.Boolean(string="Post in Youtube")
    youtube_channel_id = fields.Many2one('youtube.channel', string="Youtube Channels",
                                         help="Youtube connected accounts")
    mode = fields.Selection(selection_add=[('upload', 'Upload video(Choose this mode for youtube)')], default='url')
    youtube_video_number = fields.Char(string="Youtube Id", help="Unique id of video in youtube")

    @api.onchange('post_on_youtube')
    def _onchange_post_on_youtube(self):
        """
        Function to disable other social media when YouTube is turned on
        """
        if not self.post_on_youtube:
            self.mode = 'upload'
        if hasattr(self, "post_on_facebook"):
            self.post_on_facebook = False
        if hasattr(self, "post_on_instagram"):
            self.post_on_instagram = False

    @api.onchange('mode')
    def _onchange_mode(self):
        """
        Function to disable other social media when mode is "upload"
        """
        res = super(SocialMediaPost, self)._onchange_mode()
        if self.mode == 'upload' and hasattr(self, 'post_on_instagram'):
            self.write({
                'post_on_instagram': False,
            })
        if self.mode == 'upload' and hasattr(self, 'post_on_facebook'):
            self.write({
                'post_on_facebook': False,
            })
        if self.mode != 'upload' and hasattr(self, 'post_on_youtube'):
            self.write({
                'post_on_youtube': False,
            })
        return res

    def action_post(self):
        """Function to post the media"""
        try:
            for channel in self.youtube_channel_id:
                if self.post_on_youtube and self.mode == 'upload':
                    if self.state == 'draft':
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _(
                                    "Please Upload a video for posting"),
                                'type': 'warning',
                            },
                        }
                    account = channel.youtube_account_id
                    headers = {
                        'Authorization': f'Bearer {account.access_token}',
                        'Accept': 'application/json',
                    }
                    updated_metadata = {
                        "id": self.youtube_video_number,
                        "status": {
                            "privacyStatus": "public",
                            "embeddable": True,
                        },
                        "snippet": {
                            "title": self.name,
                            "description": self.description,
                            "categoryId": "22"
                        },
                    }
                    update_url = "https://www.googleapis.com/youtube/v3/videos?part=status,snippet"
                    response = requests.put(update_url, headers=headers, json=updated_metadata)
                    pf_link = f"""/web/image/youtube.channel/#{channel.id}/channel_image"""
                    if response.status_code == 400:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _(
                                    "Check internet connection,Try after some "
                                    "time"),
                                'type': 'warning',
                            },
                        }
                    res_json = response.json()
                    if response.status_code == 200:
                        style = 'width:350px; height:200px;'
                        author_link = "https://www.youtube.com/channel/" + res_json['snippet']['channelId']
                        post_image_url = res_json['snippet']['thumbnails']['high']['url']
                        self.env['social.media.feed'].create({
                            'description': self.description if self.description else "",
                            'posted_date': fields.Date.today(),
                            'author_name': channel.name,
                            'posted_image_url': post_image_url,
                            'author_link_url': author_link,
                            'posted_image': """<img src='%s' style='%s' class='img-fluid'/>""" %
                                            (post_image_url, style),
                            'author_link': """<a href=""" + author_link + """>""" + channel.name + """<a>""",
                            'posted_on_youtube': True,
                            'profile_image': """<img src='%s' style='width:50px;height:50px;float:left;margin-right:7px;
                                       border-radius:30px;'/>""" % pf_link,
                            'profile_image_url': pf_link,
                            'youtube_number': res_json.get('id'),
                            'youtube_post_id': self.id,
                            'youtube_channel_id': channel.id,
                            'post_id': self.id
                        })
                        self.sudo().write({
                            'state': 'post'
                        })
            return super().action_post()
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are "
                        "accurate and ensure that your device is connected to "
                        "the internet"),
                    'type': 'warning',
                },
            }

    def action_upload_video(self):
        """Function to open wizard to upload video"""
        post = self.env['upload.video.wizard'].search([('youtube_post_id', '=', self.id)])
        for channel in self.youtube_channel_id:
            account = channel.youtube_account_id
            if not account.token_expiry_date:
                account.action_refresh_access_token()
            elif account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()
        if not post:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Upload Video',
                'target': 'new',
                'view_mode': 'form',
                'res_model': 'upload.video.wizard',
                'context': {'default_youtube_post_id': self.id}
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Upload Video',
                'target': 'new',
                'view_mode': 'form',
                'res_model': 'upload.video.wizard',
                'res_id': post.id
            }

    def get_youtube_account(self):
        """Function to return the access token and details"""
        return {
            'key': self.youtube_channel_id.youtube_account_id.access_token,
            'details': self.read()[0]
        }
