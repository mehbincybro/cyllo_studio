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
import logging
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from werkzeug.urls import url_encode, url_join
import urllib.parse
import re

_logger = logging.getLogger(__name__)


class LinkedInAccount(models.Model):
    """
    Model representing a Social Media LinkedIn Account.
    """
    _name = "linkedin.account"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media LinkedIn Account"

    name = fields.Char(string="Name", required=True)
    username = fields.Char(string="Username", help="Optional. Enter to autofill LinkedIn login page.")
    linkedin_access_token = fields.Char(string='Access Token', help='Access token for your linkedin app')
    state = fields.Selection([('not connected', 'Not Connected'), ('connected', 'Connected')],
                             required=True, default='not connected', tracking=True)
    linkedin_profile_image_url = fields.Char(string='Logo URL', help='LinkedIn Organization Logo URL')
    company_id = fields.Many2one(string="Related Company",
                                 comodel_name='res.company',
                                 default=lambda self: self.env.company.id,
                                 required=True, index=True,
                                 help="The company associated with the social media account.")
    is_default = fields.Boolean(string="Is Default", compute="_compute_is_default", store=False)
    org_ids = fields.One2many(
        'linkedin.organization',
        'account_id',
        string='Organization Pages',
        help='LinkedIn organization pages linked to this account.',
    )


    @api.model_create_single
    def create(self, vals):
        """Override to handle manual access token connection."""
        if vals.get('linkedin_access_token'):
            vals['state'] = 'connected'
        
        record = super(LinkedInAccount, self).create(vals)
        
        if record.linkedin_access_token:
            try:
                record.action_sync_organizations()
            except Exception as e:
                _logger.error(f"Failed to sync organizations for manual account {record.name}: {e}")
        
        return record


    def _compute_is_default(self):
        default_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_linkedin_account.default_account_id'
        )
        for rec in self:
            rec.is_default = str(rec.id) == str(default_id)

    def action_connect_linkedin(self):
        """Connect LinkedIn account via OAuth only."""
        self.ensure_one()

        linkedin_auth_provider = self.env.ref(
            'cyllo_hr_linkedin_recruitment.provider_linkedin'
        )

        if not linkedin_auth_provider.client_id or not linkedin_auth_provider.client_secret:
            raise ValidationError(_(
                'LinkedIn Access Credentials are empty!\n'
                'Please fill them in the Auth Provider form.'
            ))

        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        redirect_uri = url_join(base_url, '/linkedin/redirect')

        params = {
            'response_type': 'code',
            'client_id': linkedin_auth_provider.client_id,
            'redirect_uri': redirect_uri,
            'state': f'smm_{self.id}',
            'scope': (
                'openid profile email '
                'w_member_social '
                # 'r_organization_social '
                # 'rw_organization_admin '
                # 'w_organization_social'
            ),
        }

        if self.username:
            params['login_hint'] = self.username

        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.linkedin.com/oauth/v2/authorization?%s' % url_encode(
                params),
            'target': 'self',
        }

    def action_disconnect(self):
        """ Function to disconnect the LinkedIn account. """
        self.write({
            'state': 'not connected',
            'linkedin_access_token': False,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'social_linkedin_account.default_account_id', None
        )

    def action_sync_organizations(self):
        """Create/update linkedin.organization records."""
        self.ensure_one()
        if not self.linkedin_access_token:
            return []
        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        identity_records = []
        try:
            acl_url = 'https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee'
            acl_res = requests.get(acl_url, headers=headers)
            if acl_res.ok:
                acl_elements = acl_res.json().get('elements', [])
                for acl in acl_elements:
                    org_urn = acl.get('organizationalTarget')
                    if not org_urn or 'urn:li:organization:' not in org_urn:
                        continue
                        
                    org_id_num = org_urn.split(':')[-1]
                    org_name = self.name # Fallback
                    org_logo = False
                    
                    try:
                        org_detail_url = (
                            f'https://api.linkedin.com/v2/organizations/{org_id_num}'
                            f'?projection=(localizedName,logoV2(original~:playableStreams,cropped~:playableStreams))'
                        )
                        org_det_res = requests.get(org_detail_url, headers=headers)
                        if org_det_res.ok:
                            org_det = org_det_res.json()
                            org_name = org_det.get('localizedName', org_name)
                            logo_v2 = org_det.get('logoV2')
                            
                            if isinstance(logo_v2, dict):
                                for field in ['original~', 'cropped~']:
                                    expanded = logo_v2.get(field, {})
                                    streams = expanded.get('elements', [])
                                    if streams:
                                        identifiers = streams[0].get('identifiers', [])
                                        if identifiers:
                                            org_logo = identifiers[0].get('identifier')
                                            break
                                
                                if not org_logo:
                                    # Fallback: Manual Images API
                                    logo_urn = logo_v2.get('original') or logo_v2.get('cropped')
                                    if logo_urn and isinstance(logo_urn, str) and logo_urn.startswith('urn:li:digitalmediaAsset:'):
                                        image_id = logo_urn.split(':')[-1]
                                        img_res = requests.get(f"https://api.linkedin.com/v2/images/{image_id}", headers=headers)
                                        if img_res.ok:
                                            org_logo = img_res.json().get('downloadUrl')
                        
                        # Create/Update Org record
                        existing_org = self.env['linkedin.organization'].search([
                            ('org_urn', '=', org_urn),
                            ('account_id', '=', self.id)
                        ], limit=1)
                        vals = {
                            'name': org_name,
                            'logo_url': org_logo,
                            'type': 'organization',
                            'state': 'active',
                        }
                        if existing_org:
                            existing_org.write(vals)
                            identity_records.append(existing_org)
                        else:
                            vals.update({'org_urn': org_urn, 'account_id': self.id})
                            new_org = self.env['linkedin.organization'].create(vals)
                            identity_records.append(new_org)
                    except Exception as e:
                        _logger.warning(f'Could not fetch details for {org_urn}: {e}')
                        
        except Exception as e:
            _logger.error(f'Error in action_sync_organizations: {e}')
            
        return identity_records

    def action_fetch_linkedin_feeds(self, start=0, count=15):
        """Fetch LinkedIn feeds for all managed org pages. Auto-syncs orgs first."""

        self.ensure_one()
        if not self.linkedin_access_token:
            raise ValidationError(_("Please connect to LinkedIn first."))

        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        legacy_headers = {'Authorization': f'Bearer {self.linkedin_access_token}'}

        try:
            user_res = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
            if user_res.ok:
                ui = user_res.json()
                pic = ui.get('picture')
                if pic:
                    self.write({'linkedin_profile_image_url': pic})
        except Exception as e:
            _logger.warning(f'Could not refresh personal picture: {e}')

        identity_records = self.action_sync_organizations()

        all_urns = []
        for ident in identity_records:
            all_urns.append((ident.org_urn, ident.name, ident.logo_url, ident.id))

        if not all_urns:
            _logger.info(f'No linked organizations found for account {self.name}. Skipping feed fetch.')
            return {
                'has_more': False,
                'total_created': 0,
                'notification': {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Info'),
                        'message': _('No LinkedIn organizations found to sync.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            }

        _logger.info(f'Fetching feeds for: {[u[0] for u in all_urns]} (start={start}, count={count})')

        total_created = 0
        has_more = False
        for fetch_urn, fetch_name, fetch_pic, org_id in all_urns:
            try:
                res = self._fetch_feeds_for_urn(fetch_urn, fetch_name, fetch_pic, legacy_headers, org_id=org_id, start=start, count=count)
                total_created += res.get('created_count', 0)
                if res.get('has_more'):
                    has_more = True
            except Exception as e:
                _logger.error(f'Error fetching feeds for {fetch_urn}: {e}')

        return {
            'has_more': has_more,
            'total_created': total_created,
            'notification': {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(f'{total_created} LinkedIn feeds synced across {len(all_urns)} account(s).'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        }

    def _fetch_feeds_for_urn(self, owner_urn, author_name, profile_pic_url, legacy_headers, org_id=False, start=0, count=15):
        """Fetch and store feeds for a single LinkedIn URN. Returns count of new records created."""
        params = {'q': 'owners', 'owners': owner_urn, 'start': start, 'count': count}
        response = requests.get('https://api.linkedin.com/v2/shares', params=params, headers=legacy_headers)
        _logger.info(f'Feeds for {owner_urn}: HTTP {response.status_code} (start={start}, count={count})')
        if not response.ok:
            _logger.error(f'Failed: {response.text[:300]}')
            return {'created_count': 0, 'has_more': False}
        elements = response.json().get('elements', [])
        if not elements:
            return {'created_count': 0, 'has_more': False}

        has_more = len(elements) > 0
        
        created_count = 0
        for element in elements:
            activity_urn = element.get('activity') or element.get('id')
            unique_id = element.get('id') or activity_urn
            if not unique_id:
                continue
            existing_feed = self.env['social.media.feed'].search([
                '|',
                ('author_link_url', 'ilike', unique_id),
                ('author_link_url', 'ilike', activity_urn),
                ('linkedin_account_id', '=', self.id)
            ], limit=1)
            likes_count = 0
            comments_count = 0
            try:
                action_res = requests.get(
                    f'https://api.linkedin.com/v2/socialActions/{activity_urn}',
                    headers=legacy_headers
                )
                if action_res.ok:
                    ad = action_res.json()
                    likes_count = ad.get('likesSummary', {}).get('totalLikes', 0)
                    comments_count = ad.get('commentsSummary', {}).get(
                        'aggregatedTotalComments',
                        ad.get('commentsSummary', {}).get('totalComments', 0)
                    )
            except Exception:
                pass
            if existing_feed:
                existing_feed.write({
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'linkedin_post_urn': activity_urn,
                    'profile_image_url': profile_pic_url,
                    'author_name': author_name,
                    'linkedin_org_id': org_id,
                })
                continue
            # Parse content
            text_content = ''
            image_url = False
            first_pub = False
            if 'specificContent' in element:
                content = element.get('specificContent', {}).get('com.linkedin.ugc.ShareContent', {})
                text_content = content.get('shareCommentary', {}).get('text', '')
                first_pub = element.get('firstPublishedAt') or element.get('created', {}).get('time', 0)
                media = content.get('media', [])
                if media and media[0].get('thumbnails'):
                    image_url = media[0]['thumbnails'][0].get('url')
            else:
                text_content = element.get('text', {}).get('text', '')
                first_pub = element.get('created', {}).get('time', 0)
                if 'content' in element and 'contentEntities' in element['content']:
                    entities = element['content']['contentEntities']
                    if entities and 'thumbnails' in entities[0] and entities[0]['thumbnails']:
                        image_url = entities[0]['thumbnails'][0].get('resolvedUrl')
            created_time = first_pub / 1000 if first_pub else 0
            posted_datetime = datetime.fromtimestamp(created_time) if created_time else fields.Datetime.now()
            self.env['social.media.feed'].create({
                'description': text_content or 'No description',
                'posted_date': posted_datetime,
                'author_name': author_name,
                'linkedin_account_id': self.id,
                'linkedin_org_id': org_id,
                'posted_on_linkedin': True,
                'linkedin_post_urn': activity_urn,
                'posted_image_url': image_url,
                'profile_image_url': profile_pic_url,
                'author_link_url': f'https://www.linkedin.com/feed/update/{activity_urn}',
                'likes_count': likes_count,
                'comments_count': comments_count,
            })
            created_count += 1
        return {'created_count': created_count, 'has_more': has_more}

    def action_fetch_feed_comments(self, parent_urn):
        """Fetch all comments for a specific LinkedIn post or comment using V2 API."""

        self.ensure_one()
        
        parent_urn = parent_urn.strip() if parent_urn else ""
        _logger.info(f"START LinkedIn comment fetch (V2). Parent URN: '{parent_urn}'")
        
        if not self.linkedin_access_token:
            _logger.warning("LinkedIn access token missing.")
            return []

        # Ensure parent_urn is encoded for the URL
        parent_urn_encoded = urllib.parse.quote(parent_urn)

        v2_url = f"https://api.linkedin.com/v2/socialActions/{parent_urn_encoded}/comments?projection=(elements*(id,message,created,actor~,commentsSummary(aggregatedTotalComments,totalComments)))"
        
        try:
            _logger.info(f"V2 Request: GET {v2_url}")
            v2_res = requests.get(v2_url, headers={'Authorization': f'Bearer {self.linkedin_access_token}'}, timeout=30)
            _logger.info(f"V2 Response: {v2_res.status_code}")
            
            if v2_res.ok:
                v2_data = v2_res.json()
                v2_comments = []
                for element in v2_data.get('elements', []):
                    actor_data = element.get('actor~', {})
                    author_name = actor_data.get('localizedFirstName', '')
                    if actor_data.get('localizedLastName'):
                        author_name += ' ' + actor_data['localizedLastName']
                    if not author_name:
                        author_name = actor_data.get('localizedName', 'LinkedIn User')
                        
                    created_at_ms = element.get('created', {}).get('time', 0)
                    created_datetime = datetime.fromtimestamp(created_at_ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S') if created_at_ms else ""

                    # URN Construction Logic
                    comment_id = element.get('id')
                    _logger.debug(f"V2 Raw Comment ID: {comment_id}")
                    
                    # Check if parent_urn is itself a comment URN: urn:li:comment:(urn:li:activity:..., ...)
                    # We need to extract the activity URN to construct the child URN: urn:li:comment:(urn:li:activity:..., child_id)
                    parent_match = re.search(r'urn:li:comment:\((urn:li:activity:\d+),', parent_urn)
                    
                    if comment_id and str(comment_id).startswith('urn:li:comment:'):
                        full_urn = comment_id
                    elif parent_match and comment_id:
                        # Nested comment: construct using Activity URN
                        activity_urn = parent_match.group(1)
                        full_urn = f"urn:li:comment:({activity_urn},{comment_id})"
                    elif comment_id and 'activity' in parent_urn:
                        # Top level comment on an Activity
                        full_urn = f"urn:li:comment:({parent_urn},{comment_id})"
                    else:
                        full_urn = comment_id # Fallback
                    
                    # Extract comment counts (replies)
                    comments_summary = element.get('commentsSummary', {})
                    reply_count = comments_summary.get('aggregatedTotalComments', comments_summary.get('totalComments', 0))

                    v2_comments.append({
                        'id': full_urn, 
                        'text': element.get('message', {}).get('text', ''),
                        'author_name': author_name,
                        'created_at': created_datetime,
                        'comments_count': reply_count, 
                        'likes_count': 0,
                    })
                
                v2_comments.sort(key=lambda x: x['created_at'], reverse=True)

                if 'activity' in parent_urn:
                    self._sync_linkedin_comment_count(parent_urn, len(v2_comments))
                return v2_comments
            else:
                _logger.error(f"V2 Fetch Failed: {v2_res.status_code} - {v2_res.text[:200]}")
                return []
                
        except Exception as e:
            _logger.error(f"Critical error in LinkedIn comment fetch (V2): {str(e)}", exc_info=True)
            return []

    # Manual override to insert logging in post comment
    def action_post_linkedin_comment(self, post_urn, message):
        """Post a top-level comment to a LinkedIn post via V2 API."""
        self.ensure_one()
        import urllib.parse
        if not self.linkedin_access_token or not self.org_ids:
            return {'error': 'LinkedIn account not connected or no identities found.'}

        _logger.info(f"POST LinkedIn Comment (V2). Target: {post_urn}")

        post_urn_encoded = urllib.parse.quote(post_urn)
        v2_url = f"https://api.linkedin.com/v2/socialActions/{post_urn_encoded}/comments"
        
        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        
        feed = self.env['social.media.feed'].search([
            ('linkedin_post_urn', '=', post_urn),
            ('linkedin_account_id', '=', self.id)
        ], limit=1)
        actor = False
        if feed and feed.linkedin_org_id:
            actor = feed.linkedin_org_id.org_urn
        else:
            # Fallback to first available organization
            active_orgs = self.org_ids.filtered(lambda i: i.state == 'active')
            if active_orgs:
                actor = active_orgs[0].org_urn
            elif self.org_ids:
                actor = self.org_ids[0].org_urn

        if not actor:
            return {'error': 'Could not resolve author URN for posting.'}

        body = {
            "actor": actor,
            "message": {
                "text": message
            }
        }
        
        try:
            _logger.info(f"V2 POST Request: {v2_url} | Body: {body}")
            res = requests.post(v2_url, json=body, headers=headers, timeout=30)
            _logger.info(f"V2 POST Response: {res.status_code} - {res.text[:200]}")
            
            if res.status_code in (200, 201):
                return res.json()
            else:
                 return {'error': res.text}
        except Exception as e:
            _logger.error(f"LinkedIn V2 Post Exception: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def _sync_linkedin_comment_count(self, post_urn, count):
        """Helper to keep the feed record count in sync with live comments popup."""
        feed = self.env['social.media.feed'].search([
            ('linkedin_post_urn', '=', post_urn),
            ('linkedin_account_id', '=', self.id)
        ], limit=1)
        if feed:
            _logger.debug(f"Syncing comment count for feed {feed.id}: {count}")
            feed.write({'comments_count': count})

    def action_post_linkedin_reply(self, comment_urn, message):
        """Post a REPLY to a LinkedIn comment via V2 API."""
        self.ensure_one()
        import urllib.parse
        
        if not self.linkedin_access_token or not self.org_ids:
            return {'error': 'LinkedIn account not connected or no identities found.'}

        _logger.info(f"POST LinkedIn Reply (V2). Parent Comment: {comment_urn}")

        comment_urn_encoded = urllib.parse.quote(comment_urn)
        v2_url = f"https://api.linkedin.com/v2/socialActions/{comment_urn_encoded}/comments"
        
        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
        }

        activity_urn = False
        parts = re.search(r'urn:li:comment:\((urn:li:activity:\d+),', comment_urn)
        if parts:
            activity_urn = parts.group(1)
        
        actor = False
        if activity_urn:
            feed = self.env['social.media.feed'].search([
                ('linkedin_post_urn', '=', activity_urn),
                ('linkedin_account_id', '=', self.id)
            ], limit=1)
            if feed and feed.linkedin_org_id:
                actor = feed.linkedin_org_id.org_urn

        if not actor:
            active_orgs = self.org_ids.filtered(lambda i: i.state == 'active')
            if active_orgs:
                actor = active_orgs[0].org_urn
            elif self.org_ids:
                actor = self.org_ids[0].org_urn

        if not actor:
            return {'error': 'Could not resolve author URN for replying.'}

        body = {
            "actor": actor,
            "message": {
                "text": message
            },
            "parentComment": comment_urn,
        }
        
        try:
            _logger.info(f"V2 POST Reply Request: {v2_url} | Body: {body}")
            res = requests.post(v2_url, json=body, headers=headers, timeout=30)
            _logger.info(f"V2 POST Reply Response: {res.status_code} - {res.text[:200]}")
            
            if res.status_code in (200, 201):
                return res.json()
            else:
                return {'error': res.text}
        except Exception as e:
            _logger.error(f"LinkedIn V2 Reply Exception: {str(e)}", exc_info=True)
            return {'error': str(e)}
