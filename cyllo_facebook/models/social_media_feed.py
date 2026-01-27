# -*- coding: utf-8 -*-
import base64
import requests
from odoo import _, fields, models


class SocialMediaFeed(models.Model):
    """Inherited the model to add function and fields related to Instagram"""
    _inherit = 'social.media.feed'

    fb_media_number = fields.Char(string="Facebook Media ID", help="Unique id in facebook")
    posted_on_facebook = fields.Boolean(string="Posted in Facebook",
                                        help="Boolean field to signifies the feed posted in facebook")
    fb_account_id = fields.Many2one('social.fb.account', string="Facebook Account",
                                    help="Select accounts where this feed have to be posted")

    def action_facebook_comments(self):
        """Action to view Facebook comments associated with the feed."""
        action = self.env.ref('cyllo_facebook.action_facebook_comment').read()[0]
        return action

    def create_lead(self, comment_data):
        """Action to view Facebook comments associated with the feed."""
        partner = self.env['res.partner'].search([('unique_fb_number', '=', comment_data['userid'])])
        lead = self.env['crm.lead'].search([('unique_fb_comment_number', '=', comment_data['id'])])
        if not partner:
            partner = self.env['res.partner'].create({
                'name': comment_data['username'],
                'unique_fb_number': comment_data['userid'],
                'fb_account_id': self.fb_account_id.id,
                'feed_id': self.id,
            })
        values = {
            'name': self.post_id.name,
            'type': 'lead',
            'user_id': self.env.user.id,
            'partner_id': partner.id,
            'contact_name': partner.name,
            'lead': False,
            'unique_fb_comment_number': comment_data['id'],
        } if not lead else {'lead': lead.id}
        return values

    def action_fetch_data_from_feed(self):
        """Action to fetch data from the feed for a specific social media account."""
        try:
            comments_result = self.get_comments_data()
            if comments_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(comments_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            access_token = self.fb_account_id.facebook_access_token
            partners = self.env['res.partner'].search([]).mapped('unique_fb_number')
            partner_count = 0
            for comment in comments_result['data']:
                user_id = comment['from']['id']
                url = (
                    f"{self.fb_account_id.facebook_base_url}/{user_id}?fields=id,name,picture&access_token="
                    f"{access_token}")
                user = requests.get(url).json()
                image_url = user['picture']['data']['url']
                image = base64.b64encode(
                    requests.get(image_url).content).decode('utf-8')
                if user['id'] not in partners:
                    self.env['res.partner'].create({
                        'name': user['name'],
                        'unique_fb_number': user['id'],
                        'feed_id': self.id,
                        'fb_account_id': self.fb_account_id.id,
                        'image_1920': image
                    })
                    partner_count += 1
                    partners.append(user['id'])
            if partner_count == 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("No new contacts to save"),
                        'type': 'warning',
                    },
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("%s new contact saved",
                                     ', '.join(str(partner_count))),
                        'type': 'success',
                    },
                }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your "
                        "device is connected to the internet"),
                    'type': 'warning',
                },
            }

    def get_comments_data(self):
        """Function to retrieve comments data from the social media feed."""
        try:
            post_id = self.fb_media_number
            access_token = self.fb_account_id.facebook_access_token
            url = self.fb_account_id.facebook_base_url
            comments_url = f"{url}/{post_id}/comments?fields=like_count,replies,message,from,created_time&access_token={access_token}"
            comments_result = requests.get(comments_url).json()

            for comment in comments_result['data']:
                comment_id = comment['id']
                replies_url = f"{url}/{comment_id}?fields=comments&access_token={access_token}"
                replies_result = requests.get(replies_url).json()
                replies_data = replies_result.get('comments', {}).get('data',
                                                                      [])
                comment['replies'] = replies_data
            return comments_result
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device "
                        "is connected to the internet"),
                    'type': 'warning',
                },
            }

    def get_facebook_comments(self):
        """Function to fetch comment details of a post in Feeds
        which will be displayed on clicking the Comments icon in
        Feeds."""
        try:
            comments_result = self.get_comments_data()
            if comments_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(comments_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            if comments_result.get('data'):
                comment_details_list = []
                for comment in comments_result['data']:
                    partner = self.env['res.partner'].sudo().search(
                        [('unique_fb_number', '=', comment['from']['id'])])
                    if not partner:
                        partner = self.env['res.partner'].create({
                            'name': comment['from']['name'],
                            'unique_fb_number': comment['from']['id'],
                            'feed_id': self.id,
                            'fb_account_id': self.fb_account_id.id,
                        })
                    replies = []
                    if comment.get('replies'):
                        for reply in comment.get('replies'):
                            partner = self.env['res.partner'].sudo().search(
                                [('unique_fb_number', '=',
                                  reply['from']['id'])])
                            if not partner:
                                partner = self.env['res.partner'].create({
                                    'name': reply['from']['name'],
                                    'unique_fb_number': reply['from']['id'],
                                    'feed_id': self.id,
                                    'fb_account_id': self.fb_account_id.id,
                                })
                            reply['partner_id']=partner.id
                            replies.append(reply)

                    comment_details = {
                        'id': comment['id'],
                        'type': "fb",
                        'username': comment['from']['name'],
                        'userid': comment['from']['id'],
                        'text': comment['message'],
                        'like_count': comment['like_count'],
                        'replies': replies,
                        'partner_id': partner.id,
                    }
                    comment_details_list.append(comment_details)
                return comment_details_list
            return []
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device"
                        " is connected to the internet"),
                    'type': 'warning',
                },
            }

    def post_facebook_comments(self, comment):
        """Function to post comments from social_media_feed model to Instagram post"""
        try:
            account = self.fb_account_id
            graph_url = account.facebook_base_url
            media_id = self.fb_media_number
            url = f"{graph_url}/{media_id}/comments"
            params = {
                'message': comment,
                'access_token': account.facebook_access_token
            }
            response = requests.post(url, data=params)
            response = response.json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(response.get('error')['message']),
                        'type': 'warning',
                    },
                }
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

    def action_social_media_comments(self):
        """
        Action to view social media comments associated with the feed.
        """
        if self.posted_on_facebook:
            action = self.action_facebook_comments()
            return action
        return super().action_social_media_comments()

    def post_facebook_reply(self, fb_comment_id, reply):
        """Function to post replies to Facebook comments associated with the feed."""
        try:
            access_token = self.fb_account_id.facebook_access_token
            graph_url = f'{self.fb_account_id.facebook_base_url}/{fb_comment_id}/comments?access_token={access_token}'
            params = {'message': reply}
            headers = {'Content-Type': 'application/json'}
            response = requests.post(graph_url, params=params, headers=headers)
            response_data = response.json()
            if response_data.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(response_data.get('error')['message']),
                        'type': 'warning',
                    },
                }
            return response_data
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device"
                        " is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_compute_likes_count_all(self):
        records_fb = self.env['social.media.feed'].search(
            [('fb_media_number', '!=', False)])
        try:
            for feed in records_fb:
                account = feed.fb_account_id
                access_token = account.facebook_access_token
                if feed.fb_media_number and feed.posted_on_facebook:
                    feed.likes_count = 0
                    feed.comments_count = 0
                    graph_url = f"{account.facebook_base_url}/{feed.fb_media_number}/likes?access_token={access_token}"
                    response = requests.get(graph_url).json()
                    graph_url = (
                        f"{account.facebook_base_url}/{feed.fb_media_number}/comments?access_token="
                        f"{access_token}")
                    data = requests.get(graph_url).json()
                    if response.get('data'):
                        feed.write({'likes_count': len(response.get('data'))})
                    else:
                        feed.likes_count = 0
                    if data.get('data'):
                        feed.write({'comments_count': len(data.get('data'))})
                    else:
                        feed.comments_count = 0
            return super().action_compute_likes_count_all()
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your "
                        "device is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_compute_likes_count(self):
        """Function to compute the count of likes associated with the feed."""
        try:
            for feed in self:
                account = feed.fb_account_id
                access_token = account.facebook_access_token
                if feed.fb_media_number and feed.posted_on_facebook:
                    feed.likes_count = 0
                    feed.comments_count = 0
                    graph_url = f"{account.facebook_base_url}/{feed.fb_media_number}/likes?access_token={access_token}"
                    response = requests.get(graph_url).json()
                    graph_url = (
                        f"{account.facebook_base_url}/{feed.fb_media_number}/comments?access_token="
                        f"{access_token}")
                    data = requests.get(graph_url).json()
                    if response.get('data'):
                        feed.write({'likes_count': len(response.get('data'))})
                    else:
                        feed.likes_count = 0
                    if data.get('data'):
                        feed.write({'comments_count': len(data.get('data'))})
                    else:
                        feed.comments_count = 0
            return super().action_compute_likes_count()
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your "
                        "device is connected to the internet"),
                    'type': 'warning',
                },
            }
