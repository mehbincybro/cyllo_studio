# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import base64
import requests
from odoo import _, api, fields, models


class SocialMediaFeed(models.Model):
    """Inherited the model to add function and fields related to Facebook"""
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

    def create_lead(self, comment_data, title=None):
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
            'name': self.post_id.name if self.post_id.name else title,
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
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            fb_account_id = self.fb_account_id.browse(int(default_id))
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

    @api.model
    def get_feed_data(self, **kwargs):
        try:
            load_more_url = kwargs.get('loadMore')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            fb_account_id = self.fb_account_id.browse(int(default_id))
            page_id = fb_account_id.facebook_page_number
            page_access_token = fb_account_id.facebook_access_token
            url = fb_account_id.facebook_base_url
            feeds_api = (
                f"{url}/{page_id}/feed?"
                f"fields=created_time,from,id,message,attachments,"
                f"likes.summary(true),"
                f"comments.summary(true){{id,message,from,comments.summary(true)}}&"
                f"limit=5&"
                f"access_token={page_access_token}"
            )

            if load_more_url:
                feeds_api = load_more_url
            res = requests.get(feeds_api).json()
            return res
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

    @api.model
    def get_comments_data(self, feed, next_url):
        """Function to retrieve comments data from the social media feed."""
        try:
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            post_id = feed
            fb_account_id = self.fb_account_id.browse(int(default_id))
            page_access_token = fb_account_id.facebook_access_token
            url = fb_account_id.facebook_base_url

            if next_url:
                comments_url = next_url
            else:
                comments_url = (
                    f"{url}/{post_id}/comments"
                    f"?fields=like_count,replies,message,from,created_time"
                    f"&limit=5&access_token={page_access_token}"
                )

            comments_result = requests.get(comments_url).json()

            for comment in comments_result['data']:
                comment_id = comment['id']
                replies_url = (f"{url}/{comment_id}"
                               f"?fields=comments.limit(2)&access_token={page_access_token}")
                replies_result = requests.get(replies_url).json()
                replies_data = replies_result.get('comments', {}).get('data',[])
                replies_paging = replies_result.get('comments', {}).get('paging',{})
                comment['replies'] = replies_data
                comment['replies_paging'] = replies_paging
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

    @api.model
    def get_facebook_comments(self, **kwargs):
        feed_id = kwargs.get('feed')
        next_url = kwargs.get('nextUrl', None)
        default_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_fb_account.default_fb_account_id'
        )
        fb_account_id = self.fb_account_id.browse(int(default_id))
        comments_result = self.get_comments_data(feed_id, next_url)
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
                replies = []
                if comment.get('replies'):
                    for reply in comment.get('replies'):
                        replies.append(reply)

                comment_details = {
                    'id': comment['id'],
                    'type': "fb",
                    'username': comment.get('from', {}).get('name', 'Facebook User'),
                    'userid': comment.get('from', {}).get('id', '0'),
                    'text': comment['message'],
                    'like_count': comment['like_count'],
                    'replies': replies,
                    'replies_paging': comment.get('replies_paging'),
                    'partner_id': 0,
                }
                comment_details_list.append(comment_details)
            return {
                'data': comment_details_list,
                'paging': comments_result.get("paging", None),
            }
        return []



    @api.model
    def post_facebook_comments(self, **kwargs):
        try:
            media_id = kwargs.get('feed')
            comment = kwargs.get('comment')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            account = self.fb_account_id.browse(int(default_id))
            graph_url = account.facebook_base_url
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
            details = requests.get(
                f"{account.facebook_base_url}/{response.get('id')}?fields=id,message,from,created_time,like_count&access_token={account.facebook_access_token}"
            ).json()
            return details
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

    @api.model
    def post_facebook_reply(self, **kwargs):
        """Function to post replies to Facebook comments associated with the feed."""
        try:
            comment_id = kwargs.get('comment')
            reply = kwargs.get('reply')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            account = self.fb_account_id.browse(int(default_id))
            access_token = account.facebook_access_token
            graph_url = f'{account.facebook_base_url}/{comment_id}/comments?access_token={access_token}'
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
            details_url = f"{account.facebook_base_url}/{response_data.get('id')}"
            details_params = {
                "fields": "id,message,from,created_time,like_count",
                "access_token": access_token,
            }
            details = requests.get(details_url, params=details_params).json()
            return details
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

    @api.model
    def action_compute_fb_likes_count(self, **kwargs):
        """Function to compute the count of likes associated with the feed."""
        try:
            feed_id = kwargs.get('feed')
            if feed_id:
                feeds = self.search([('fb_media_number', '=', feed_id)], limit=1)
            else:
                feeds = self.search(['fb_media_number', '!=', False])
            for feed in feeds:
                account = feed.fb_account_id
                access_token = account.facebook_access_token
                if feed.fb_media_number and feed.posted_on_facebook:
                    feed.likes_count = 0
                    feed.comments_count = 0
                    graph_url = (
                        f"{account.facebook_base_url}/{feed.fb_media_number}?fields=likes.summary(true)"
                        f"&access_token={access_token}")
                    likes = requests.get(graph_url).json()
                    graph_url = (
                        f"{account.facebook_base_url}/{feed.fb_media_number}/comments"
                        f"?summary=true&filter=stream&access_token={access_token}"
                    )
                    comments = requests.get(graph_url).json()
                    if likes.get('likes'):
                        feed.write(
                            {'likes_count': int(likes.get("likes", {}).get("summary", {}).get("total_count", 0))})
                    else:
                        feed.likes_count = 0
                    if comments.get('data'):
                        feed.write({'comments_count': int(comments.get("summary", {}).get("total_count", 0))})
                    else:
                        feed.comments_count = 0
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
