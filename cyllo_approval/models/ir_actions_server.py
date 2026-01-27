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
from odoo import _, models


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    def run(self):
        current_model = self.env.context.get('active_model', {})
        if not current_model:
            return super(IrActionsServer, self).run()
        current_record = self.env[current_model].browse(
            self.env.context.get('active_id'))
        if not current_record:
            return super(IrActionsServer, self).run()
        approval_rules = self.env['approval.rule'].sudo().search([
            ('definition_type', '=', 'server_action'),
            ('state', '=', 'enable'),
            ('model_select', '=', current_model)
        ])
        for rule in approval_rules:
            if self.id == rule.server_action_id.id:
                approval_requests = self.env['approval.request'].search([
                    ('approval_rule_id', '=', rule.id),
                    ('res_id', '=', current_record.id),
                    ('state', '=', 'approved'),
                    ('requested_by_id', '=', self.env.user.id)
                ])
                if approval_requests:
                    return super(IrActionsServer, self).run()
                current_record.write({
                    'server_trigger': True,
                    'approval_rule_id': rule.id,
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Need an Approval for this Order"),
                        'type': 'warning',
                        'sticky': True,
                        'next': {'type': 'ir.actions.client',
                                 'tag': 'reload'}
                    },
                }
        return super(IrActionsServer, self).run()
