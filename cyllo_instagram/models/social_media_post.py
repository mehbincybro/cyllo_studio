# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import ValidationError
import json
import requests


class SocialMediaPost(models.Model):
    """
        Inherits the social.media.post model to handle posts for differentsocial media platforms.
    """
    _inherit = 'social.media.post'

    instagram_attachment_id = fields.Many2one('ir.attachment', compute="_compute_instagram_attachment_id")
    post_on_instagram = fields.Boolean(string="Post in Instagram")
    insta_account_ids = fields.Many2many('social.insta.account', string="Instagram Accounts",
                                         help="Instagram connected accounts")

    def _compute_instagram_attachment_id(self):
        """
        Computes the attachment ID for Instagram posts.
        """
        for post in self:
            jpeg_images = post.ir_attachment_ids.filtered(lambda image: image.mimetype == 'image/jpeg')
            post.instagram_attachment_id = jpeg_images[0] if jpeg_images else False
            post.instagram_attachment_id.public = True

    def action_post(self):
        """
        Inherited to post the Message and attached image in Social Post to Instagram Publishing image to instagram is
        a two-step process.
        1. Create a Container, which means uploading the image and message. It will return a container ID.
        2. Publishing the Container. In this step, the container ID returned in the previous
        step will be published.
        So that the image and message will be visible on the Instagram account
        """
        try:
            for account in self.insta_account_ids:
                if self.company_id and self.post_on_instagram:
                    page_id = account.facebook_insta_page_number
                    access_token = account.instagram_access_token
                    business_account = (f'{account.instagram_base_url}/{page_id}?fields=instagram_business_account'
                                        f'&access_token={access_token}')
                    res = requests.get(business_account).json()
                    if res.get('error'):
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _(res.get('error')['message']),
                                'type': 'warning',
                            },
                        }
                    instagram_business_account = res['instagram_business_account']['id']
                    post_url = f'{account.instagram_base_url}/{instagram_business_account}/media'
                    if self.mode == 'attachment':
                        payload = {
                            'image_url': self.instagram_attachment_id.public_url,
                            'caption': self.description,
                            'access_token': access_token
                        }
                        post_image_url = self.instagram_attachment_id.public_url
                    else:
                        payload = {
                            'image_url': self.post_url,
                            'caption': self.description if self.description else "",
                            'access_token': access_token
                        }
                        post_image_url = self.post_url
                    r = requests.post(post_url, data=payload)
                    result = json.loads(r.text)
                    if 'id' in result:
                        creation_id = result['id']
                        publish_url = f'{account.instagram_base_url}/{instagram_business_account}/media_publish'
                        second_payload = {
                            'creation_id': creation_id,
                            'access_token': access_token
                        }
                        image_publish = requests.post(publish_url,
                                                      data=second_payload)
                        ig_media_number = json.loads(image_publish.text)['id']
                        profile_url = (f'{account.instagram_base_url}/{instagram_business_account}?fields=name,'
                                       f'username,biography,website,followers_count,follows_count,media_count,'
                                       f'profile_picture_url&access_token={access_token}')
                        profile_details = requests.get(profile_url).json()
                        author_link = ('https://www.instagram.com/%s' % profile_details.get('username'))
                        style = 'width:350px; height:200px;'
                        pf_link = f'cyllo_social_media_marketing/static/src/img/profile_pic.jpg'
                        if not json.loads(image_publish.text).get('error'):
                            self.env['social.media.feed'].create({
                                'description': self.description if self.description else "",
                                'posted_date': fields.Date.today(),
                                'author_name': profile_details.get('username'),
                                'posted_image_url': post_image_url,
                                'author_link_url': author_link,
                                'posted_image': """<img src='%s' style='%s' class='img-fluid'/>""" %
                                                (post_image_url, style),
                                'author_link': """<a href=""" + author_link + """>""" +
                                               profile_details.get('name') + """<a>""",
                                'posted_on_ig': True,
                                'profile_image': """<img src='%s' style='width:50px;height:50px;float:left;
                                margin-right:7px;border-radius:30px;'/>""" % pf_link,
                                'profile_image_url': pf_link,
                                'ig_media_number': ig_media_number,
                                'post_id': self.id,
                                'ig_account_id': account.id
                            })
                elif (self.mode == 'attachment' and self.company_id and self.ir_attachment_ids and
                      not self.instagram_attachment_id):
                    raise ValidationError(_('Only .jpg/.jpeg images can be posted on Instagram.'))
            return super().action_post()
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device is "
                        "connected to the internet"),
                    'type': 'warning',
                },
            }
