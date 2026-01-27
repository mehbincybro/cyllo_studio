# -*- coding: utf-8 -*-
from odoo import _, fields, models
import requests
import datetime


class SocialMediaFeed(models.Model):
    """
    Inherited the model to add function and fields related to Instagram
    """
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

    def create_lead_ig(self, comment_data):
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
                'name': self.post_id.name,
                'type': 'lead',
                'user_id': self.env.user.id,
                'partner_id': partner.id,
                'contact_name': partner.name,
                'lead': False,
                'unique_ig_comment_number': comment_data['id'],
            }
        return values

    def get_ig_comments_data(self):
        """
        Action to get Instagram comments associated with the feed.
        """
        try:
            ig_media_number = self.ig_media_number
            ig_comments_url = \
                (
                    f'{self.ig_account_id.instagram_base_url}/{ig_media_number}?fields=comments&access_token='
                    f'{self.ig_account_id.instagram_access_token}')
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

    import datetime
    import requests

    def get_instagram_comments(self, active_id):
        """
        Function to fetch comment details of a post in Feeds which will be displayed on clicking the Comments icon in
        Feeds.
        """
        try:
            feed_id = self.env['social.media.feed'].browse(active_id)
            comments_result = feed_id.get_ig_comments_data()
            account = feed_id.ig_account_id
            comment_details_list = []
            if comments_result.get('comments'):
                for comment in comments_result.get('comments')['data']:
                    comment_details_url = (
                        f'{account.instagram_base_url}/{comment["id"]}?fields=id,username,text,'
                        f'like_count,replies,from,hidden,media,parent_id,timestamp&access_token='
                        f'{account.instagram_access_token}')
                    comment_details_result = requests.get(
                        comment_details_url).json()
                    partner_temp = self.env['res.partner'].sudo().search(
                        [('unique_fb_number', '=',
                          comment_details_result['from']['id'])])
                    if not partner_temp:
                        partner_temp = self.env['res.partner'].create({
                            'name': comment_details_result['from']['username'],
                            'unique_ig_number': comment_details_result['from'][
                                'id'],
                            'feed_id': self.id,
                            'insta_account_id': self.ig_account_id.id,
                        })
                    comment_details_result.update(
                        {'timestamp': datetime.datetime.strptime(
                            comment_details_result['timestamp'],
                            '%Y-%m-%dT%H:%M:%S+0000').date(),
                         'partner_id': partner_temp.id,
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
                            if not partner_current:
                                partner_current = self.env[
                                    'res.partner'].create({
                                    'name': reply_details_result['username'],
                                    'unique_ig_number': reply_details_result[
                                        'id'],
                                    'feed_id': self.id,
                                    'insta_account_id': self.ig_account_id.id,
                                })
                            reply_details_result.update(
                                {
                                    'partner_id': partner_current.id,
                                })
                            comment_details_result['reply'].append(
                                reply_details_result)
                            comment_details_result['reply'] = \
                                comment_details_result['reply'][::-1]
                    comment_details_list.append(comment_details_result)
            return comment_details_list
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

    def post_instagram_comments(self, active_id, comment):
        """
        Function to post comments from social_media_feed model to Instagram post
        """
        try:
            feed_id = self.env['social.media.feed'].browse(active_id)
            graph_url = f'{feed_id.ig_account_id.instagram_base_url}/'
            media_id = feed_id.ig_media_number
            url = graph_url + media_id + '/comments'
            param = dict()
            param['message'] = comment
            param['access_token'] = feed_id.ig_account_id.instagram_access_token
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

    def post_instagram_reply(self, active_id, ig_comment_id, reply):
        """
        Function to post replies to Instagram comments associated with the feed.
        """
        try:
            feed_id = self.env['social.media.feed'].browse(active_id)
            graph_url = f'{feed_id.ig_account_id.instagram_base_url}/'
            url = graph_url + ig_comment_id + '/replies?'
            param = dict()
            param['message'] = reply
            param['access_token'] = feed_id.ig_account_id.instagram_access_token
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
            return super().action_compute_likes_count()
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
