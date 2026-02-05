# -*- coding: utf-8 -*-
from odoo import  fields, models
from odoo.exceptions import UserError


class ApprovalTransferWizard(models.TransientModel):
    _name = 'approval.transfer.wizard'
    _description = "Transfer Approval Wizard"

    request_id = fields.Many2one(
        'approval.request',
        required=True,
    )

    user_id = fields.Many2one(
        'res.users',
        string="Transfer To",
        required=True,
    )

    current_user_id = fields.Many2one('res.users')

    def action_transfer_approval(self):
        """Transfer approval from one user to another."""
        self.ensure_one()
        request = self.request_id

        if request.approver_id != self.current_user_id:
            raise UserError(
                "Only the current approver can transfer this approval.")

        # Update current approver
        request.approver_id = self.user_id.id

        model = request.res_model
        approval_record = self.env[model].browse(request.res_id)
        approval_record.write({
            'x_current_approver_id': self.user_id.id,
        })

        # # Chatter log
        # request.message_post(
        #     body=f"Approval transferred from {self.current_user_id.name} "
        #          f"to {self.user_id.name}."
        # )


        return {'type': 'ir.actions.act_window_close'}
