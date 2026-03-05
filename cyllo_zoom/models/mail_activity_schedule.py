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
import logging
import ast
_logger = logging.getLogger(__name__)

class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    def action_create_calendar_event(self):
        self.ensure_one()

        action = super().action_create_calendar_event()
        ctx = action.get("context", {})
        default_values = ctx.get("default_", {}) or {}
        target_ids = ast.literal_eval(self.res_ids)
        record = self.env[self.res_model].browse(target_ids[0])
        partner_ids = []
        partner_ids.append(self.env.user.partner_id.id)
        if hasattr(record, "partner_id") and record.partner_id:
            partner_ids.append(record.partner_id.id)
        action["context"].update({
            "default_partner_ids": [fields.Command.link(p) for p in
                                partner_ids]
        })
        return action

