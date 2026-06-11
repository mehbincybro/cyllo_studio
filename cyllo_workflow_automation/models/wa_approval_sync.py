from odoo import models, api

class WorkAutoApprovalSync(models.Model):
    _inherit = 'work.auto'

    def save_data(self, data, name, ttype, **kwargs):
        res = super().save_data(data, name, ttype, **kwargs)
        if not self.env['ir.module.module'].search([('name', '=', 'cyllo_approval'), ('state', '=', 'installed')]):
            return res

        # After saving, sync approval rule
        automation = self.browse(res)
        
        # Check if there is an approval node
        approval_nodes = automation.node_struct_ids.filtered(lambda n: n.name == 'Approval' and n.trigger_type == 'approval')
        for node in approval_nodes:
            # Create or update approval.rule in cyllo_approval
            rule_vals = {
                'name': node.label or f'Approval Rule for {automation.name}',
                'model_id': automation.model_id.id,
                'rule_type': 'server', # Need something to avoid overriding standard buttons? Wait, cyllo_approval rule_type
                'user_id': node.approval_approver_id.id if node.approval_approver_type == 'user' else False,
                'group_id': node.approval_approver_group_id.id if node.approval_approver_type == 'group' else False,
                'is_email': node.approval_notify_email,
            }
            # We need to map it to the automation? Actually, cyllo_approval's approval.rule needs to trigger this automation.
        return res
