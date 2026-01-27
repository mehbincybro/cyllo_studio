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


class ResConfigSettings(models.TransientModel):
    """Inherit res.config.settings to add the boolean fields for voice chatter"""
    _inherit = 'res.config.settings'

    is_voice_chat = fields.Boolean(string="Voice in chatter",
                                 config_parameter='cyllo_voice_to_text_chatter.is_voice_chat',
                                 help="Whether it need to allow voice in the chatter")
    open_ai_api_key = fields.Char(string="Open AI Api key",
                                  config_parameter='cyllo_voice_to_text_chatter.open_ai_api_key',
                                  help="Open AI api key")


