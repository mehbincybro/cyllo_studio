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
from odoo import models, fields, api

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    workflow_id = fields.Many2one('work.auto', string="Automation Workflow")
    workflow_node_id = fields.Many2one('node.struct', string="Workflow Node")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('rule_id'):
                node = self.env['node.struct'].search([('approval_rule_id', '=', vals['rule_id'])], limit=1)
                if node:
                    vals['workflow_id'] = node.work_auto_id.id
                    vals['workflow_node_id'] = node.id
        return super().create(vals_list)

    def _run_approval_workflow(self, status):
        for request in self:
            if not request.workflow_id or not request.workflow_node_id:
                continue
                
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"[APPROVAL] Request {status} for workflow {request.workflow_id.name}")
            
            target_record = self.env[request.res_model].browse(request.res_id)
            if target_record.exists():
                request.workflow_id._process({
                    'records': target_record,
                    'trigger_type': 'approval',
                    'approval_status': status,
                    'approval_node_id': request.workflow_node_id.drawflow_node_id
                })
