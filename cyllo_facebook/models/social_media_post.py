# -*- coding: utf-8 -*-
import requests
from odoo import _, fields, models


class SocialMediaPost(models.Model):
    """
    Inherits the social.media.post model to handle posts for different
    social media platforms.
    """
    _inherit = 'social.media.post'

    facebook_attachment_id = fields.Many2one(
        'ir.attachment', compute="_compute_facebook_attachment_id", string="Facebook Attachment to Post",
        help="The attachment ID related to the Facebook post.")
    post_on_facebook = fields.Boolean(string="Post in Facebook", help="Enable this to post this post in facebook")
    fb_account_ids = fields.Many2many('social.fb.account', string="Facebook Accounts",
                                      help="Facebook connected accounts")

    def _compute_facebook_attachment_id(self):
        """Computes the attachment ID for Facebook posts."""
        for post in self:
            jpeg_images = post.ir_attachment_ids.filtered(lambda image: image.mimetype == 'image/jpeg')
            post.facebook_attachment_id = jpeg_images[0] if jpeg_images else False
            post.facebook_attachment_id.public = True

    def action_post(self):
        """Posts content to the specified Facebook account."""
        try:
            for account in self.fb_account_ids:
                if self.post_on_facebook:
                    if self.mode == 'attachment' and not self.facebook_attachment_id:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _("Attachment is empty or given attachment doesnt support. "
                                             "Added jpg/jpeg format attachments"),
                                'type': 'warning',
                            },
                        }
                    page_id = account.facebook_page_number
                    graph_url = f"{account.facebook_base_url}/{page_id}/feed"
                    if self.mode == 'attachment':
                        payload = {
                            'access_token': account.facebook_access_token,
                            'message': self.description,
                            'link': self.facebook_attachment_id.fb_public_url,
                        }
                        post_image_url = self.facebook_attachment_id.fb_public_url
                    elif self.mode == 'content_only':
                        payload = {
                            'access_token': account.facebook_access_token,
                            'message': self.description,
                        }
                        post_image_url = 'cyllo_facebook/static/src/img/fb.jpeg'
                    else:
                        payload = {
                            'access_token': account.facebook_access_token,
                            'message': self.description if self.description else "",
                            'link': self.post_url,
                        }
                        post_image_url = self.post_url
                    response = requests.post(graph_url, data=payload)
                    if response.json().get('error'):
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _(response.json().get('error')['message']),
                                'type': 'warning',
                            },
                        }
                    url = (f"{account.facebook_base_url}/{page_id}?fields=name,picture,id&access_token="
                           f"{account.facebook_access_token}")
                    user = requests.get(url)
                    data = user.json()
                    result = response.json()
                    if result.get('error'):
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _(result.get('error')['message']),
                                'type': 'warning',
                            },
                        }
                    author_link = f"https://www.facebook.com/profile.php?id={data.get('id')}"
                    style = 'width:350px; height:200px;'
                    pf_link = f'cyllo_social_media_marketing/static/src/img/profile_pic.jpg'
                    if 'id' in result:
                        self.env['social.media.feed'].create({
                            'description': self.description if self.description else "",
                            'posted_date': fields.Date.today(),
                            'author_name': data.get('name'),
                            'fb_media_number': result['id'],
                            'fb_account_id': account.id,
                            'posted_image_url': post_image_url,
                            'author_link_url': author_link,
                            'posted_image': """<img src='%s' style='%s'
                             class='img-fluid'/>""" % (post_image_url, style),
                            'author_link': """<a href=""" + author_link + """>""" + data.get('name') + """<a>""",
                            'posted_on_facebook': True,
                            'profile_image_url': data['picture']['data']['url'] if data[
                                'picture']['data']['url'] else pf_link,
                            'profile_image': """<img src='%s'style='width:50px;
                            height:50px;float:left;margin-right:7px;
                            border-radius:30px;'/>""" % (data['picture']['data']['url'] if data[
                                'picture']['data']['url'] else pf_link),
                            'post_id': self.id
                        })
            return super().action_post()
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Check the internet connection."),
                    'type': 'warning',
                },
            }
