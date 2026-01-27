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
from odoo import http
from odoo.http import request

class CustomerPortal(http.Controller):

    @http.route(['/my/approval_requests'], type='http', auth="user", website=True)
    def portal_approval_requests(self, user_id=None, **kwargs):
        user_id = int(user_id) if user_id else request.uid


        # Fetch only the approval requests assigned to the user
        approval_requests = request.env['approval.request'].sudo().search([
            ('approver_ids', '=', user_id)
        ])

        values = {
            'approval_requests': approval_requests,
        }
        return request.render('cyllo_approval.portal_my_approval_requests', values)

    @http.route(['/my/approval_request/action'], type='http', auth="user", methods=['POST'], website=True,csrf=False)
    def handle_approval_action(self, **post):
        request_id = post.get('request_id')
        action = post.get('action')

        if request_id and action:
            approval_request = request.env['approval.request'].sudo().browse(int(request_id))
            approval_request.sudo().action_approve()
            if approval_request.exists():
                if action == 'accept':
                    approval_request.sudo().write({'state': 'approved'})
                elif action == 'reject':
                    approval_request.sudo().write({'state': 'rejected'})

        return request.redirect('/my/approval_requests')
