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
import requests
import datetime
from odoo import _, api, fields, models



class SocialMediaFeed(models.Model):
    """Inherited the model to add function and fields related to Instagram"""
    _inherit = 'social.media.feed'

    ig_media_number = fields.Char(string="Instagram Media ID",
                                  help="Unique identifier for Instagram media")
    posted_on_ig = fields.Boolean(string="Posted on Facebook",
                                  help="Indicates whether the media is posted on Facebook")
    ig_account_id = fields.Many2one('social.insta.account',
                                    string="Instagram Account",
                                    help="Linked Instagram account")

    def action_fetch_data_from_ig_feed(self):
        """
            Action to fetch data from the feed for a specific social
            media account.
        """
        try:
            comments_result = self.get_ig_comments_data()
            if comments_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(comments_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            access_token = self.ig_account_id.instagram_access_token
            partners = self.env['res.partner'].search([]).mapped(
                'unique_ig_number')
            partner_count = 0
            if comments_result.get('comments'):
                for comment in comments_result['comments']['data']:
                    url = (
                        f"{self.ig_account_id.instagram_base_url}/{comment['id']}?fields=id,from"
                        f"&access_token={access_token}")
                    comment_details = requests.get(url).json()
                    user_id = comment_details['from']['id']
                    url = (f"{self.ig_account_id.instagram_base_url}/{user_id}"
                           f"?fields=id,name&access_token={access_token}")
                    user = requests.get(url).json()
                    if user.get('id') and user['id'] not in partners:
                        partner_count += 1
                        self.env['res.partner'].create({
                            'name': user['name'],
                            'unique_ig_number': user['id'],
                            'insta_account_id': self.ig_account_id.id,
                            'feed_id': self.id,
                        })
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
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("No new contacts to save"),
                        'type': 'warning',
                    },
                }
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

    @api.model
    def get_insta_feed_data(self, **kwargs):
        try:
            load_more_url = kwargs.get('loadMore')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_insta_account.default_insta_account_id'
            )
            insta_account_id = self.env['social.insta.account'].browse(int(default_id))
            ig_user_id = insta_account_id.instagram_business_account_number
            access_token = insta_account_id.instagram_access_token

            user_info_url = f"https://graph.facebook.com/v20.0/{ig_user_id}?fields=profile_picture_url,username&access_token={access_token}"
            user_info = requests.get(user_info_url).json()
            profile_pic = user_info.get("profile_picture_url", "")

            feeds_api = (
                f"https://graph.facebook.com/v20.0/{ig_user_id}/media?"
                f"fields=id,caption,media_type,media_url,permalink,timestamp,username,"
                f"like_count,comments_count&"
                f"limit=5&access_token={access_token}"
            )
            if load_more_url:
                feeds_api = load_more_url

            res = requests.get(feeds_api).json()
            for post in res.get("data", []):
                post["profile_picture_url"] = profile_pic

            return res

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"Instagram Feed Error: {str(e)}",
                    'type': 'warning',
                },
            }

    def create_lead_ig(self, comment_data, title=None):
        """
        Action to view Facebook comments associated with the feed.
        """
        partner = self.env['res.partner'].search(
            [('unique_ig_number', '=', comment_data['from']['id'])])
        lead = self.env['crm.lead'].search(
            [('unique_ig_comment_number', '=', comment_data['id'])])
        if not partner:
            partner = self.env['res.partner'].create({
                'name': comment_data['username'],
                'unique_ig_number': comment_data['from']['id'],
                'insta_account_id': self.ig_account_id.id,
                'feed_id': self.id,
            })
        if lead:
            values = {
                'lead': lead.id,
            }
        else:
            values = {
                'name': self.post_id.name if self.post_id.name else title,
                'type': 'lead',
                'user_id': self.env.user.id,
                'partner_id': partner.id,
                'contact_name': partner.name,
                'lead': False,
                'unique_ig_comment_number': comment_data['id'],
            }
        return values
    @api.model
    def get_ig_comments_data(self, feed, account, next_url):
        """
        Action to get Instagram comments associated with the feed.
        """
        try:
            if next_url:
                ig_comments_url = next_url
            else:
                ig_comments_url = \
                    (
                        f'{account.instagram_base_url}/{feed}/comments'
                        f'??fields=like_count,replies,message,from,created_time'
                        f'&limit=5&access_token={account.instagram_access_token}'
                    )

            comments_result = requests.get(ig_comments_url).json()

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

    def action_instagram_comments(self):
        """
        Action to view Instagram comments associated with the feed.
        """
        action = \
            self.env.ref('cyllo_instagram.action_instagram_comment').read()[0]
        return action

    @api.model
    def get_instagram_comments(self, **kwargs):
        """
        Function to fetch comment details of a post in Feeds which will be displayed on clicking the Comments icon in
        Feeds.
        """
        feed_id = kwargs.get('feed')
        next_url = kwargs.get('nextUrl', None)
        default_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_insta_account.default_insta_account_id'
        )
        account = self.ig_account_id.browse(int(default_id))
        try:
            comments_result = self.get_ig_comments_data(feed_id, account, next_url)
            if comments_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(comments_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            comment_details_list = []
            if comments_result.get('data'):
                for comment in comments_result['data']:
                    comment_details_url = (
                        f'{account.instagram_base_url}/{comment["id"]}?fields=id,username,text,'
                        f'like_count,replies.limit(2),from,hidden,media,parent_id,timestamp&access_token='
                        f'{account.instagram_access_token}')
                    comment_details_result = requests.get(
                        comment_details_url).json()
                    partner_temp = self.env['res.partner'].sudo().search(
                        [('unique_fb_number', '=',
                          comment_details_result['from']['id'])])
                    comment_details_result.update(
                        {'timestamp': datetime.datetime.strptime(
                            comment_details_result['timestamp'],
                            '%Y-%m-%dT%H:%M:%S+0000').date(),
                         'partner_id': partner_temp.id  if partner_temp else None,
                         })
                    if 'replies' in comment_details_result and 'data' in \
                            comment_details_result['replies']:
                        comment_details_result['reply'] = []
                        for reply in comment_details_result['replies']['data']:
                            reply_details_url = (
                                f'{account.instagram_base_url}/{reply["id"]}?fields=id,username,text,'
                                f'timestamp&access_token={account.instagram_access_token}')
                            reply_details_result = requests.get(
                                reply_details_url).json()
                            partner_current = self.env[
                                'res.partner'].sudo().search(
                                [('unique_fb_number', '=',
                                  reply_details_result['id'])])
                            reply_details_result.update(
                                {
                                    'partner_id': partner_current.id if partner_current else None,
                                })
                            comment_details_result['reply'].append(
                                reply_details_result)
                            comment_details_result['reply'] = \
                                comment_details_result['reply'][::-1]
                    comment_details_list.append(comment_details_result)
            return {
                'data': comment_details_list,
                'paging': comments_result.get("paging", None),
            }
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
    def post_instagram_comments(self, **kwargs):
        """
        Function to post comments from social_media_feed model to Instagram post
        """
        try:
            media_id = kwargs.get('feed')
            comment = kwargs.get('comment')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_insta_account.default_insta_account_id'
            )
            account = self.ig_account_id.browse(int(default_id))
            graph_url = f'{account.instagram_base_url}/'
            url = graph_url + media_id + '/comments'
            param = dict()
            param['message'] = comment
            param['access_token'] = account.instagram_access_token
            response = requests.post(url, params=param)
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

            reply_details_url = (
                f'{account.instagram_base_url}/{response["id"]}?fields=id,username,text,'
                f'timestamp&access_token={account.instagram_access_token}')
            details = requests.get(reply_details_url).json()
            return details
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

    def action_social_media_comments(self):
        """
        Action to view social media comments associated with the feed.
        """
        if self.posted_on_ig:
            action = self.action_instagram_comments()
            return action
        return super().action_social_media_comments()

    @api.model
    def post_instagram_reply(self, **kwargs):
        """
        Function to post replies to Instagram comments associated with the feed.
        """
        try:
            comment_id = kwargs.get('comment')
            reply = kwargs.get('reply')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_insta_account.default_insta_account_id'
            )
            account = self.ig_account_id.browse(int(default_id))
            graph_url = f'{account.instagram_base_url}/'
            url = graph_url + comment_id + '/replies?'
            param = dict()
            param['message'] = reply
            param['access_token'] = account.instagram_access_token
            response = requests.post(url, params=param)
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
            reply_details_url = (
                f'{account.instagram_base_url}/{response["id"]}?fields=id,username,text,'
                f'timestamp&access_token={account.instagram_access_token}')
            details = requests.get(reply_details_url).json()
            return details
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

    def action_compute_likes_count_all(self):
        """Function to compute like and comment count of feed"""
        records_ig = self.env['social.media.feed'].search(
            [('ig_media_number', '!=', False)])
        try:
            for feed in records_ig:
                if feed.posted_on_ig:
                    feed.likes_count = 0
                    feed.comments_count = 0
                    graph_url = 'https://graph.facebook.com/v18.0/'
                    media_id = feed.ig_media_number
                    url = (
                            graph_url + media_id + '?fields=like_count,comments_count,' 'comments&access_token=%s'
                            % feed.ig_account_id.instagram_access_token)
                    response = requests.get(url).json()
                    if response.get('like_count'):
                        feed.likes_count = response.get('like_count')
                    if response.get('comments'):
                        feed.comments_count = len(
                            response.get('comments')['data'])
            return super().action_compute_likes_count_all()
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

    def action_compute_likes_count(self):
        """
        Compute the number of likes on the post for Instagram.
        """
        try:
            for feed in self:
                if feed.posted_on_ig:
                    feed.likes_count = 0
                    feed.comments_count = 0
                    graph_url = 'https://graph.facebook.com/v18.0/'
                    media_id = feed.ig_media_number
                    url = (
                            graph_url + media_id + '?fields=like_count,comments_count,comments&access_token=%s' %
                            feed.ig_account_id.instagram_access_token)
                    response = requests.get(url).json()
                    if response.get('like_count'):
                        feed.likes_count = response.get('like_count')
                    if response.get('comments'):
                        feed.comments_count = len(
                            response.get('comments')['data'])

                if hasattr(feed, 'views_count'):
                    return {
                        'likes_count': feed.likes_count,
                        'comments_count': feed.comments_count,
                        'views_count': feed.views_count,
                    }
                else:
                    return {
                        'likes_count': feed.likes_count,
                        'comments_count': feed.comments_count,
                    }

        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are "
                        "accurate and ensure that your device is connected to"
                        " the internet"),
                    'type': 'warning',
                },
            }
