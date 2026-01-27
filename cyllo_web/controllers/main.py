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


class AuthController(http.Controller):

    @http.route('/check/mail', type='json', auth='public', methods=['POST'])
    def validate_mail(self):
        response_data = request.get_json_data()
        data = response_data.get('params')

        email = data.get('email')

        user_exists = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
        if user_exists:
            return {
                'status': 'success',
                'message': 'User exists'
            }
        else:
            return {
                'status': 'error',
                'message': 'User with this email does not exist'
            }
