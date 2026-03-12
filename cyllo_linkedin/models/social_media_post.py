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
from odoo import fields, models, _
import requests
import logging

_logger = logging.getLogger(__name__)


class SocialMediaPost(models.Model):
    """Class to define the fields and functions for social media posts."""
    _inherit = ['social.media.post']


    linkedin_account_ids = fields.Many2many('linkedin.account',
                                            string="LinkedIn Accounts",
                                            help="LinkedIn connected accounts")
    linkedin_organization_ids = fields.Many2many('linkedin.organization',
                                                 string="LinkedIn Pages",
                                                 help="Specific LinkedIn organization pages to post to.")
    linkedin_content_type = fields.Selection([
        ('text', 'Text Only'),
        ('image', 'Image'),
        ('poll', 'Poll'),
    ], string="LinkedIn Content Type", default='text',
        help="Type of content to post on LinkedIn.")
    linkedin_image_ids = fields.Many2many(
        'ir.attachment',
        'social_post_li_image_rel',
        'post_id', 'attachment_id',
        string="LinkedIn Images",
        help="Images to attach to the LinkedIn post (max 20)."
    )
    # ── Poll fields ──────────────────────────────────────
    linkedin_poll_question = fields.Char(string="Poll Question",
                                         help="Question for the LinkedIn poll.")
    linkedin_poll_option_1 = fields.Char(string="Option 1")
    linkedin_poll_option_2 = fields.Char(string="Option 2")
    linkedin_poll_option_3 = fields.Char(string="Option 3 (optional)")
    linkedin_poll_option_4 = fields.Char(string="Option 4 (optional)")
    linkedin_poll_duration = fields.Selection([
        ('ONE_DAY', '1 Day'),
        ('THREE_DAYS', '3 Days'),
        ('SEVEN_DAYS', '7 Days'),
        ('FOURTEEN_DAYS', '14 Days'),
    ], string="Poll Duration", default='THREE_DAYS')

    def action_post(self):
        """Function to post to LinkedIn."""

        for post in self:
            linkedin_success = True
            if post.posted_on_linkedin:
                for org in post.linkedin_organization_ids:
                    account = org.account_id
                    if not account.linkedin_access_token or not org.org_urn:
                        _logger.warning(f"LinkedIn organization {org.name} missing token or URN.")
                        continue

                    url = 'https://api.linkedin.com/v2/ugcPosts'
                    headers = {
                        'Authorization': f'Bearer {account.linkedin_access_token}',
                        'X-Restli-Protocol-Version': '2.0.0',
                        'Content-Type': 'application/json',
                    }

                    owner_urn = org.org_urn
                    _logger.info(f"Posting to LinkedIn with author URN: {owner_urn}")

                    payload = {
                        "author": owner_urn,
                        "lifecycleState": "PUBLISHED",
                        "specificContent": {
                            "com.linkedin.ugc.ShareContent": {
                                "shareCommentary": {
                                    "text": post.description
                                },
                                "shareMediaCategory": "NONE"
                            }
                        },
                        "visibility": {
                            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                        }
                    }

                    if post.mode == 'url' and post.post_url:
                        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"
                        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                            "status": "READY",
                            "originalUrl": post.post_url,
                            "title": { "text": post.name }
                        }]

                    try:
                        content_type = post.linkedin_content_type or 'text'
                        if content_type == 'image':
                            response = self._post_linkedin_image(post, org, account, headers)
                        elif content_type == 'poll':
                            response = self._post_linkedin_poll(post, org, account, headers)
                        else:
                            response = self._post_linkedin_text(post, org, headers)

                        restli_id = response.headers.get('x-restli-id')
                        success_codes = [200, 201]
                        if response.status_code in success_codes:
                            result = response.json() if response.text else {}
                            post_id = result.get('id') or restli_id
                            # Build the feed record values
                            feed_vals = {
                                'description': post.description,
                                'posted_date': fields.Datetime.now(),
                                'author_name': org.name,
                                'linkedin_account_id': account.id,
                                'linkedin_org_id': org.id,
                                'posted_on_linkedin': True,
                                'linkedin_post_urn': post_id,
                                'post_id': post.id,
                                'profile_image_url': org.logo_url or False,
                                'author_link_url': f"https://www.linkedin.com/feed/update/{post_id}" if post_id else False,
                            }
                            # For image posts: store the first image URL so it shows in the timeline immediately
                            if post.linkedin_content_type == 'image' and post.linkedin_image_ids:
                                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                                first_img = post.linkedin_image_ids[0]
                                feed_vals['posted_image_url'] = f"{base_url}/web/image/{first_img.id}"
                            # For poll posts: store poll data immediately
                            elif post.linkedin_content_type == 'poll':
                                import json as _json
                                options = []
                                for opt in [post.linkedin_poll_option_1, post.linkedin_poll_option_2,
                                            post.linkedin_poll_option_3, post.linkedin_poll_option_4]:
                                    if opt and opt.strip():
                                        options.append({'text': opt.strip(), 'voteCount': 0})
                                feed_vals.update({
                                    'is_poll': True,
                                    'poll_question': post.linkedin_poll_question or post.description,
                                    'poll_options': _json.dumps(options),
                                    'poll_duration': post.linkedin_poll_duration or 'THREE_DAYS',
                                    'poll_total_votes': 0,
                                })
                            self.env['social.media.feed'].create(feed_vals)
                            self.message_post(body=_("Successfully posted to LinkedIn (%s)") % org.name)
                        else:
                            linkedin_success = False
                            error_msg = response.text
                            _logger.error(f"LinkedIn API error ({response.status_code}): {error_msg}")
                            self.message_post(body=_(
                                "Failed to post to LinkedIn (%s).\n"
                                "URN used: %s\n"
                                "Error: %s\n\n"
                                "TIP: If this is an organization page, ensure you have the 'w_organization_social' permission."
                            ) % (org.name, owner_urn, error_msg))
                    except Exception as e:
                        linkedin_success = False
                        _logger.exception("LinkedIn post exception")
                        self.message_post(body=_(f"Exception while posting to LinkedIn: {str(e)}"))

            if linkedin_success:
                post.write({
                    'posted_date': fields.Datetime.now(),
                    'state': 'post',
                })
            else:
                pass

    def _post_linkedin_text(self, post, org, headers):
        """Helper method to post text-only content to LinkedIn."""
        url = 'https://api.linkedin.com/v2/ugcPosts'
        payload = {
            "author": org.org_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post.description
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        if post.mode == 'url' and post.post_url:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"][
                "shareMediaCategory"] = "ARTICLE"
            payload["specificContent"]["com.linkedin.ugc.ShareContent"][
                "media"] = [{
                "status": "READY",
                "originalUrl": post.post_url,
                "title": {"text": post.name}
            }]

        _logger.info("Posting LinkedIn Text/Article: %s", payload)
        return requests.post(url, headers=headers, json=payload, timeout=60)

    def _post_linkedin_image(self, post, org, account, headers):
        """Helper method to post images to LinkedIn."""
        if not post.linkedin_image_ids:
            # Fallback to text if no images attached
            return self._post_linkedin_text(post, org, headers)
        media_assets = []
        for img in post.linkedin_image_ids:
            register_url = 'https://api.linkedin.com/v2/assets?action=registerUpload'
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": org.org_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            reg_res = requests.post(register_url, headers=headers,
                                    json=register_payload, timeout=30)
            if not reg_res.ok:
                return reg_res  # Fallback or return failed register response

            reg_data = reg_res.json()
            upload_url = reg_data.get('value', {}).get('uploadMechanism',
                                                       {}).get(
                'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest',
                {}).get('uploadUrl')
            asset_urn = reg_data.get('value', {}).get('asset')

            # 2. Upload Image
            import base64
            image_content = base64.b64decode(img.datas)
            # A fresh header without Content-Type limitation for binary upload
            upload_headers = {'Authorization': headers['Authorization']}
            upload_res = requests.put(upload_url, headers=upload_headers,
                                      data=image_content, timeout=120)
            if not upload_res.ok:
                return upload_res

            media_assets.append({
                "status": "READY",
                "media": asset_urn,
                "title": {"text": img.name or "Image"}
            })

        # 3. Create UGC Post with Images
        url = 'https://api.linkedin.com/v2/ugcPosts'
        post_payload = {
            "author": org.org_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post.description
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": media_assets
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        return requests.post(url, headers=headers, json=post_payload,
                             timeout=60)

    def _post_linkedin_poll(self, post, org, account, headers):
        """Helper method to post a poll to LinkedIn.
        Requires modern /rest/posts endpoint and LinkedIn-Version header.
        """
        url = 'https://api.linkedin.com/rest/posts'
        rest_headers = dict(headers)
        rest_headers.update({
            'LinkedIn-Version': '202602',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json'
        })
        options = []
        for opt in [post.linkedin_poll_option_1, post.linkedin_poll_option_2,
                    post.linkedin_poll_option_3, post.linkedin_poll_option_4]:
            if opt and opt.strip():
                options.append({"text": opt.strip()})

        if len(options) < 2:
            raise ValueError("A poll must have at least 2 options.")
        duration = post.linkedin_poll_duration or 'THREE_DAYS'
        payload = {
            "author": org.org_urn,
            "commentary": post.description,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "content": {
                "poll": {
                    "question": post.linkedin_poll_question or post.description,
                    "options": options,
                    "settings": {
                        "duration": duration
                    }
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        _logger.info("Posting LinkedIn Poll: %s", payload)
        return requests.post(url, headers=rest_headers, json=payload,
                             timeout=60)

