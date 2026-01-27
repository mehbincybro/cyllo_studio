# -*- coding: utf-8 -*-
import requests
from odoo import _, fields, models
from odoo.tools.safe_eval import datetime


class SocialMediaFeed(models.Model):
    """
    Inherited the model to add function and fields related to YouTube
    """
    _inherit = 'social.media.feed'

    youtube_number = fields.Char(string="Youtube Media ID", help="Unique identifier for Youtube media")
    posted_on_youtube = fields.Boolean(string="Posted in Youtube",
                                       help="Indicates whether the media is posted on Youtube")
    youtube_channel_id = fields.Many2one('youtube.channel', string="Related Youtube Channel",
                                         help="Linked Youtube Channel")
    youtube_post_id = fields.Many2one('social.media.post', string="Related Youtube Post", help="Linked Youtube Post")
    views_count = fields.Integer(string="Views", help="Number of views on the post")

    def create_lead_youtube(self, comment_data):
        """
        Action to view YouTube comments associated with the feed.
        """
        partner = self.env['res.partner'].search([('unique_yt_number', '=', comment_data['userid'])])
        lead = self.env['crm.lead'].search([('unique_yt_comment_number', '=', comment_data['id'])])
        if not partner:
            partner = self.env['res.partner'].create({
                'name': comment_data['username'],
                'unique_yt_number': comment_data['userid'],
                'youtube_account_id': self.youtube_channel_id.youtube_account_id.id,
                'feed_id': self.id,
            })
        if lead:
            values = {
                'lead': lead.id,
            }
        else:
            values = {
                'name': self.youtube_post_id.name,
                'type': 'lead',
                'user_id': self.env.user.id,
                'partner_id': partner.id,
                'contact_name': partner.name,
                'lead': False,
                'unique_yt_comment_number': comment_data['id'],
            }
        return values

    def action_youtube_comments(self):
        """
        Action to view YouTube comments associated with the feed.
        """
        action = self.env.ref('cyllo_youtube.action_youtube_comment').read()[0]
        return action

    def get_youtube_comments(self, active_id):
        """
        Function to fetch comment details of a post in Feeds
        which will be displayed on clicking the Comments icon in
        Feeds.
        """
        try:
            feed = self.env['social.media.feed'].sudo().browse(active_id)
            if not feed.youtube_channel_id.youtube_account_id.token_expiry_date:
                feed.youtube_channel_id.youtube_account_id.refresh_access_token()
            elif feed.youtube_channel_id.youtube_account_id.token_expiry_date <= datetime.datetime.now():
                feed.youtube_channel_id.youtube_account_id.refresh_access_token()
            url = "https://www.googleapis.com/youtube/v3/commentThreads"
            params = {
                'part': 'snippet,replies',
                'textFormat': 'plainText',
                'access_token': feed.youtube_channel_id.youtube_account_id.access_token,
                'videoId': feed.youtube_number,
                'maxResults': 20
            }
            comments_result = requests.get(url, params=params)
            comment_details_list = []
            if comments_result.status_code == 200:
                if comments_result.json().get('items'):
                    for comment in comments_result.json().get('items'):
                        snippet = comment['snippet']['topLevelComment'][
                            'snippet']
                        replies = comment.get('replies')
                        if replies and 'comments' in replies:
                            replies_data = replies['comments']
                            reply_count = len(replies_data)
                        else:
                            replies_data = None
                            reply_count = 0
                        comment_details = {
                            'id': comment['id'],
                            'username': snippet['authorDisplayName'],
                            'userid': snippet['authorChannelId']['value'],
                            'text': snippet['textOriginal'],
                            'like_count': snippet['likeCount'],
                            'timestamp': snippet['publishedAt'],
                            'replies': replies_data,
                            'reply_count': reply_count
                        }
                        comment_details_list.append(comment_details)
            return comment_details_list
        except Exception:
            return []

    def post_youtube_comments(self, active_id, comment):
        """
        Function to post comments from social_media_feed model to YouTube post
        """
        try:
            feed = self.env['social.media.feed'].sudo().browse(active_id)
            account = feed.youtube_channel_id.youtube_account_id
            if not account.token_expiry_date:
                account.refresh_access_token()
            elif account.token_expiry_date <= datetime.datetime.now():
                account.refresh_access_token()
            url = 'https://youtube.googleapis.com/youtube/v3/commentThreads'
            params = {
                'part': 'snippet',
            }
            token = account.access_token
            headers = {
                'Authorization': 'Bearer ' + token,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            payload = {
                'snippet': {
                    'videoId': feed.youtube_number,
                    'topLevelComment': {
                        'snippet': {
                            'textOriginal': comment
                        }
                    }
                }
            }
            requests.post(url, params=params, headers=headers, json=payload)
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device is"
                        " connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_social_media_comments(self):
        """
        Action to view social media comments associated with the feed.
        """
        if self.posted_on_youtube:
            action = self.action_youtube_comments()
            return action
        return super().action_social_media_comments()

    def post_youtube_reply(self, active_id, yt_comment_id, reply):
        """
        Function to post replies to YouTube comments associated with the feed.
        """
        try:
            feed_id = self.env['social.media.feed'].sudo().browse(active_id)
            account = feed_id.youtube_channel_id.youtube_account_id
            if not account.token_expiry_date:
                account.refresh_access_token()
            elif account.token_expiry_date <= datetime.datetime.now():
                account.refresh_access_token()
            url = 'https://youtube.googleapis.com/youtube/v3/comments'
            params = {
                'part': 'snippet',
            }
            headers = {
                'Authorization': 'Bearer ' + account.access_token,
                'Accept': 'application/json',
            }
            payload = {
                'snippet': {
                    'parentId': yt_comment_id,
                    'textOriginal': reply
                }
            }
            requests.post(url, params=params, headers=headers, json=payload)
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
        """
        Function to synchronize feed.
        """
        try:
            records_yt = self.env['social.media.feed'].search(
                [('youtube_number', '!=', False)])
            for feed in records_yt:
                account = feed.youtube_channel_id.youtube_account_id
                if not account.token_expiry_date:
                    account.refresh_access_token()
                elif account.token_expiry_date <= datetime.datetime.now():
                    account.refresh_access_token()
                if feed.posted_on_youtube:
                    feed.likes_count = 0
                    feed.comments_count = 0
                    feed.view_count = 0
                    headers = {
                        'Authorization': f'Bearer {account.access_token}',
                        'Accept': 'application/json',
                    }
                    updated_metadata = {
                        "id": feed.youtube_number,
                    }
                    update_url = "https://www.googleapis.com/youtube/v3/videos?part=statistics"
                    response = requests.put(update_url, headers=headers, json=updated_metadata)
                    url = "https://www.googleapis.com/youtube/v3/commentThreads"
                    params = {
                        'part': 'snippet,replies',
                        'textFormat': 'plainText',
                        'access_token': account.access_token,
                        'videoId': feed.youtube_number,
                        'maxResults': 20
                    }
                    comments_result = requests.get(url, params=params)
                    if comments_result.status_code == 200:
                        if comments_result.json().get('items'):
                            feed.comments_count = len(comments_result.json().get('items'))
                    res_json = response.json()
                    if res_json['statistics'].get('likeCount'):
                        feed.likes_count = int(res_json['statistics']['likeCount'])
                    if res_json['statistics'].get('commentCount'):
                        feed.comments_count = int(res_json['statistics']['commentCount'])
                    if res_json['statistics'].get('viewCount'):
                        feed.view_count = int(res_json['statistics']['viewCount'])

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
        Compute the number of likes on the post for YouTube.
        """
        try:
            for feed in self:
                if feed.posted_on_youtube:
                    account = feed.youtube_channel_id.youtube_account_id
                    if not account.token_expiry_date:
                        account.refresh_access_token()
                    elif account.token_expiry_date <= datetime.datetime.now():
                        account.refresh_access_token()
                    feed.likes_count = 0
                    feed.comments_count = 0
                    feed.views_count = 0
                    headers = {
                        'Authorization': f'Bearer {account.access_token}',
                        'Accept': 'application/json',
                    }
                    updated_metadata = {
                        "id": feed.youtube_number,
                    }
                    update_url = "https://www.googleapis.com/youtube/v3/videos?part=statistics"
                    response = requests.put(update_url, headers=headers, json=updated_metadata)
                    url = "https://www.googleapis.com/youtube/v3/commentThreads"
                    params = {
                        'part': 'snippet,replies',
                        'textFormat': 'plainText',
                        'access_token': account.access_token,
                        'videoId': feed.youtube_number,
                        'maxResults': 20
                    }
                    comments_result = requests.get(url, params=params)
                    if comments_result.status_code == 200:
                        if comments_result.json().get('items'):
                            feed.comments_count = len(comments_result.json().get('items'))
                    res_json = response.json()
                    if res_json['statistics'].get('likeCount'):
                        feed.likes_count = int(
                            res_json['statistics']['likeCount'])
                    if res_json['statistics'].get('viewCount'):
                        feed.views_count = int(
                            res_json['statistics']['viewCount'])
            return super().action_compute_likes_count()
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
