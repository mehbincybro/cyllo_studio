import requests
from odoo import http, _
from odoo.http import request
from werkzeug.urls import url_join
from odoo.addons.cyllo_hr_linkedin_recruitment.controller.hr_linkedin_recruitment import LinkedinSocial

class LinkedInSocialController(LinkedinSocial):

    @http.route('/linkedin/redirect', type='http', auth='user', website=True)
    def social_linkedin_callbacks(self, **kw):
        """
        Handle LinkedIn OAuth callback. 
        If 'state' starts with 'smm_', it's an SMM connection. 
        Otherwise, delegate to the Recruitment module.
        """
        state = kw.get('state')
        
        # 1. Intercept SMM requests
        if state and state.startswith('smm_'):
            code = kw.get('code')

            try:
                account_id = int(state.split('_')[1])
            except (IndexError, ValueError):
                return request.redirect('/web')

            linkedin_account = request.env['linkedin.account'].sudo().browse(account_id)
            if not linkedin_account.exists():
                return request.redirect('/web')

            linkedin_auth_provider = request.env.ref('cyllo_hr_linkedin_recruitment.provider_linkedin')
            if not linkedin_auth_provider.client_id or not linkedin_auth_provider.client_secret:
                return request.make_response(
                    _('LinkedIn Provider credentials (recruitment settings) are missing.'),
                    status=400
                )

            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = url_join(base_url, '/linkedin/redirect')

            token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': linkedin_auth_provider.client_id,
                'client_secret': linkedin_auth_provider.client_secret,
                'redirect_uri': redirect_uri,
            }
            
            try:
                token_response = requests.post(token_url, data=token_data).json()
                access_token = token_response.get('access_token')
            except Exception as e:
                return request.make_response(
                    _('Failed to connect to LinkedIn: %s') % str(e),
                    status=400
                )

            if not access_token:
                return request.make_response(
                    _('Failed to obtain access token. Response: %s') % token_response,
                    status=400
                )

            user_info_url = 'https://api.linkedin.com/v2/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                user_info_response = requests.get(user_info_url, headers=headers).json()
                profile_pic = user_info_response.get('picture')
            except Exception as e:
                 return request.make_response(
                    _('Failed to fetch user info: %s') % str(e),
                    status=400
                )

            linkedin_account.write({
                'linkedin_access_token': access_token,
                'state': 'connected',
                'linkedin_profile_image_url': profile_pic,
                'name': user_info_response.get('name', linkedin_account.name or 'LinkedIn Account'),
            })
            
            linkedin_account.action_sync_organizations()

            try:
                menu_id = request.env.ref('cyllo_social_media_marketing.menu_cyllo_social_media_marketing_root').id
                action_id = request.env.ref("cyllo_social_media_marketing.social_media_dashboard_action").id
                url = f'/web#menu_id={menu_id}&action={action_id}'
            except Exception:
                url = '/web'
            return request.redirect(url)

        return super(LinkedInSocialController, self).social_linkedin_callbacks()
