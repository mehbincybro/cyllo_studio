# -*- coding: utf-8 -*-
from odoo import models

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] in ['approved', 'rejected']:
            # Check if this request is tied to a workflow node
            for record in self:
                node = self.env['node.struct'].sudo().search([('approval_request_id', '=', record.id)], limit=1)
                if node:
                    node._approval_resume(vals['state'])
        return res
