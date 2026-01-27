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
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_fb_account(self):
        return self.env['social.fb.account'].search([('state', '=', 'connected')], limit=1).id

    def _default_insta_account(self):
        return self.env['social.insta.account'].search([('state', '=', 'connected')], limit=1).id

    default_fb_account_id = fields.Many2one(
        'social.fb.account',
        'Default Facebook Page',
        config_parameter = 'social_fb_account.default_fb_account_id',
        default = _default_fb_account,
        default_model = 'social.fb.account'
    )
    default_insta_account_id = fields.Many2one(
        'social.insta.account',
        'Default Instagram Account',
        config_parameter='social_insta_account.default_insta_account_id',
        default=_default_insta_account,
        default_model='social.insta.account'
    )