/** @odoo-module **/
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { NotificationItem } from "@mail/core/web/notification_item";
import { useService, useBus } from '@web/core/utils/hooks';
import { registry } from '@web/core/registry';
import { Component, onWillStart,onRendered, onMounted,useState } from '@odoo/owl';
import { session } from '@web/session';

export class ApprovalIcon extends MessagingMenu {
    async setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.user = useService("user");
        this.actionService = useService("action");

        this.state.all_approval_requests = await this.orm.searchRead(
            "approval.request",
            [['state', 'in', ['pending', 'approved', 'rejected', 'transferred']], '|', ['approver_ids', 'in', [this.user.userId]], ['requested_by_id', '=', this.user.userId]],
            ['name', 'state', 'requested_by_id', 'requested_date', 'approved_by_id', 'rejected_by_id', 'approver_ids', 'res_id', 'model_name']
        );
        this.state.all_approval_requests = await this.orm.searchRead(
            "approval.request",
            [
                ['state', 'in', ['pending', 'approved', 'rejected', 'transferred']],
                '|',
                ['approver_ids', 'in', [this.user.userId]],
                ['requested_by_id', '=', this.user.userId],
                ['read_by_ids', 'not in', [this.user.userId]]
            ],
            ['name', 'state', 'requested_by_id', 'requested_date', 'approved_by_id', 'rejected_by_id', 'approver_ids', 'res_id', 'model_name']
        );
        this.state.all_approval_requests = this.state.all_approval_requests.map(request => {
            let message = "";
            if (request.state === "pending" && request.approver_ids.includes(this.user.userId)) {
                message = "An Approval request has been assigned to you";
            }
            else if (request.state === "approved" && !request.approver_ids.includes(this.user.userId)) {
                message = `Your Approval request has been approved by ${request.approved_by_id?.[1] || "someone"}`;
            }
            else if (request.state === "rejected" && !request.approver_ids.includes(this.user.userId)) {
                message = `Your Approval request has been rejected by ${request.rejected_by_id?.[1] || "someone"}`;
            }
            else if (request.state === "transferred" && request.approver_ids.includes(this.user.userId)) {
                message = "An Approval request has been forwarded to you for review";
            }
            else if (request.state === "transferred" && !request.approver_ids.includes(this.user.userId)) {
                message = "Your Approval request has been forwarded to another person";
            }
            return {
                ...request,
                message,
            };
        });
        this.state.approval_counter = this.state.all_approval_requests.filter(request => request.message).length;
    }
    openForm(res_id, model_name){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: res_id,
            res_model: model_name,
            views: [[false, "form"]],
        });
    }
    async markAsRead(recordId) {
        await this.orm.call(
            "approval.request",
            "mark_as_read",
            [[recordId]]
        );
        this.state.all_approval_requests = this.state.all_approval_requests.filter(
            request => request.id !== recordId
        );
        this.state.approval_counter = this.state.all_approval_requests.filter(request => request.message).length;
    }


}
ApprovalIcon.template = 'cyllo_approval.ApprovalIcon';
ApprovalIcon.components = {Dropdown, DropdownItem ,NotificationItem,MessagingMenu};
export const ApprovalIconItems = {
    Component: ApprovalIcon,
};
registry.category('systray').add('ApprovalIcon', ApprovalIconItems, {sequence: 1000});