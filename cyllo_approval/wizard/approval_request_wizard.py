# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import  fields, models

class ApprovalRequestWizard(models.TransientModel):
    _name = 'approval.request.wizard'
    _description = 'Approval Request Confirmation'

    rule_id = fields.Many2one('approval.rule', required=True)
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)

    def action_request_approval(self):
        """Create approval request from wizard."""
        Request = self.env['approval.request'].sudo()
        Request.create({
            'rule_id': self.rule_id.id,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'requested_by': self.env.user.id,
            'approver_id': self.rule_id.user_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
