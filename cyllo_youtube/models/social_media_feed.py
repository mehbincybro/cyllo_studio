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

from odoo import _, fields, models, api
from odoo.tools.safe_eval import datetime


class SocialMediaFeed(models.Model):
    """
    Inherited the model to add function and fields related to YouTube
    """
    _inherit = 'social.media.feed'

    youtube_number = fields.Char(string="Youtube Media ID",
                                 help="Unique identifier for Youtube media")
    posted_on_youtube = fields.Boolean(string="Posted in Youtube",
                                       help="Indicates whether the media is posted on Youtube")
    youtube_channel_id = fields.Many2one('youtube.channel',
                                         string="Related Youtube Channel",
                                         help="Linked Youtube Channel")
    youtube_post_id = fields.Many2one('social.media.post',
                                      string="Related Youtube Post",
                                      help="Linked Youtube Post")
    views_count = fields.Integer(string="Views",
                                 help="Number of views on the post")

    @api.model
    def get_youtube_feed_data(self, channel_id=None, pageToken=None):
        try:
            if channel_id:
                channel = self.env['youtube.channel'].browse(int(channel_id))
                if not channel.exists():
                    print("ERROR: Channel not found for ID", channel_id)
                    return {"data": [], "nextPageToken": None}
                yt_account = channel.youtube_account_id
            else:
                yt_account = self.env['youtube.account'].get_default_youtube_account()
                if not yt_account or not yt_account.channel_ids:
                    print("ERROR: No default YouTube account or channels")
                    return {"data": [], "nextPageToken": None}
                channel = yt_account.channel_ids[0]

            channel_id_number = channel.youtube_number
            access_token = yt_account.access_token

            channel_url = (
                f"https://www.googleapis.com/youtube/v3/channels"
                f"?part=contentDetails,snippet"
                f"&id={channel_id_number}"
                f"&access_token={access_token}"
            )

            channel_res = requests.get(channel_url).json()
            uploads_playlist_id = channel_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            channel_thumb = channel_res["items"][0]["snippet"]["thumbnails"]["default"]["url"]
            playlist_url = (
                f"https://www.googleapis.com/youtube/v3/playlistItems"
                f"?part=snippet"
                f"&playlistId={uploads_playlist_id}"
                f"&maxResults=5"
                f"&access_token={access_token}"
            )
            if pageToken:
                playlist_url += f"&pageToken={pageToken}"

            playlist_res = requests.get(playlist_url).json()
            video_items = []
            video_ids = []

            for item in playlist_res.get("items", []):
                snippet = item["snippet"]
                video_id = snippet["resourceId"]["videoId"]
                video_ids.append(video_id)
                video_items.append({
                    "id": video_id,
                    "youtube_number": video_id,
                    "publishedAt": snippet["publishedAt"],
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "channelTitle": snippet.get("channelTitle", ""),
                    "thumbnails": snippet.get("thumbnails", {}),
                    "channelThumb": channel_thumb,
                })
            if video_ids:
                stats_url = (
                    f"https://www.googleapis.com/youtube/v3/videos"
                    f"?part=statistics"
                    f"&id={','.join(video_ids)}"
                    f"&access_token={access_token}"
                )
                stats_res = requests.get(stats_url).json()
                stats_map = {item["id"]: item["statistics"] for item in stats_res.get("items", [])}

                for video in video_items:
                    video["statistics"] = stats_map.get(video["id"], {})
            return {
                "data": video_items or [],
                "nextPageToken": playlist_res.get("nextPageToken"),
            }

        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": f"YouTube Feed Error: {str(e)}",
                    "type": "warning",
                },
            }

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

    @api.model
    def get_youtube_comments(self, video_id, page_token=None, channel_id=None):
        """
        Fetch YouTube comments (paginated).
        """
        try:
            yt_account = None
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(channel_id)
                if not channel.exists():
                    return {"comments": [], "nextPageToken": None, "error": "Channel not found"}
                yt_account = channel.youtube_account_id
            else:
                yt_account = self.env['youtube.channel'].set_default_account_from_channel()
            access_token = yt_account.access_token
            comments_url = (
                f"https://www.googleapis.com/youtube/v3/commentThreads"
                f"?part=snippet,replies"
                f"&videoId={video_id}"
                f"&maxResults=10" 
                f"&access_token={access_token}"
            )
            if page_token:
                comments_url += f"&pageToken={page_token}"

            comments_res = requests.get(comments_url).json()
            comment_details_list = []

            for item in comments_res.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]

                partner = self.env['res.partner'].sudo().search(
                    [('unique_yt_number', '=', snippet.get('authorChannelId', {}).get('value'))],
                    limit=1
                )
                if not partner and snippet.get('authorChannelId'):
                    partner = self.env['res.partner'].create({
                        'name': snippet.get('authorDisplayName'),
                        'unique_yt_number': snippet['authorChannelId']['value'],
                    })

                replies_data = []
                reply_count = 0
                if "replies" in item and "comments" in item["replies"]:
                    for rec in item["replies"]["comments"]:
                        r_snippet = rec["snippet"]

                        partner_reply = self.env['res.partner'].sudo().search(
                            [('unique_yt_number', '=', r_snippet.get('authorChannelId', {}).get('value'))],
                            limit=1
                        )
                        if not partner_reply and r_snippet.get('authorChannelId'):
                            partner_reply = self.env['res.partner'].create({
                                'name': r_snippet.get('authorDisplayName'),
                                'unique_yt_number': r_snippet['authorChannelId']['value'],
                            })

                        replies_data.append({
                            "author": r_snippet.get("authorDisplayName"),
                            "author_profile_img": r_snippet.get("authorProfileImageUrl"),
                            "text": r_snippet.get("textOriginal"),
                            "publishedAt": r_snippet.get("publishedAt"),
                            "likeCount": r_snippet.get("likeCount", 0),
                            "partner_id": partner_reply.id if partner_reply else False,
                        })

                    reply_count = len(replies_data)

                comment_details = {
                    "id": item["id"],
                    "username": snippet.get("authorDisplayName"),
                    "author_profile_img": snippet.get("authorProfileImageUrl"),
                    "userid": snippet.get("authorChannelId", {}).get("value"),
                    "text": snippet.get("textOriginal"),
                    "publishedAt": snippet.get("publishedAt"),
                    "likeCount": snippet.get("likeCount", 0),
                    "partner_id": partner.id if partner else False,
                    "replies": replies_data,
                    "reply_count": reply_count,
                }

                comment_details_list.append(comment_details)

            return {
                "comments": comment_details_list,
                "nextPageToken": comments_res.get("nextPageToken")
            }

        except Exception as e:
            return {"comments": [], "nextPageToken": None, "error": str(e)}

    @api.model
    def post_youtube_comments(self, active_id, comment, channel_id=None):
        """
        Function to post comments from social_media_feed model to YouTube post
        """
        try:
            feed = self.env['social.media.feed'].sudo().browse(active_id)
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(channel_id)
                account = channel.youtube_account_id
            else:
                account = self.env['youtube.channel'].set_default_account_from_channel()
            if not account:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "No YouTube account available to post comments",
                        'type': 'warning',
                    },
                }
            if not account.token_expiry_date or account.token_expiry_date <= datetime.datetime.now():
                account.refresh_access_token()

            url = 'https://youtube.googleapis.com/youtube/v3/commentThreads?part=snippet'
            headers = {
                'Authorization': f'Bearer {account.access_token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            payload = {
                'snippet': {
                    'videoId': active_id,
                    'topLevelComment': {
                        'snippet': {'textOriginal': comment}
                    }
                }
            }
            response = requests.post(url, headers=headers, json=payload)
            return response.json()

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"Error posting comment: {str(e)}",
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

    @api.model
    def post_youtube_reply(self, active_id, yt_comment_id, reply, channel_id=None):
        """
        Function to post replies to YouTube comments associated with the feed.
        """
        try:
            feed_id = self.env['social.media.feed'].sudo().browse(active_id)
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(channel_id)
                account = channel.youtube_account_id
            else:
                account = self.env['youtube.channel'].set_default_account_from_channel()
            if not account:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "No YouTube account linked to this feed.",
                        'type': 'warning',
                    },
                }
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