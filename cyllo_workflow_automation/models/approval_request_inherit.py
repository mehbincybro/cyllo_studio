from odoo import models, api

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def action_approve(self):
        res = super().action_approve()
        for record in self:
            if not record.res_model or not record.res_id:
                continue
            target_record = self.env[record.res_model].browse(record.res_id)
            if target_record.exists():
                automation_ids = self.env['work.auto']._get_actions(target_record, 'approval')
                for automation in automation_ids:
                    automation._process({'records': target_record, 'trigger_type': 'approval', 'approval_status': 'approved'})
        return res

    def action_reject(self):
        res = super().action_reject()
        for record in self:
            if not record.res_model or not record.res_id:
                continue
            target_record = self.env[record.res_model].browse(record.res_id)
            if target_record.exists():
                automation_ids = self.env['work.auto']._get_actions(target_record, 'approval')
                for automation in automation_ids:
                    automation._process({'records': target_record, 'trigger_type': 'approval', 'approval_status': 'rejected'})
        return res
