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
    setup() {
        this.busService = useService("bus_service");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        this.approvals = [];

        onMounted(() => {
            this.busService.addChannel("approval_notification");
            this.busService.onNotification(this, this.handleApprovalNotification);
        });
    }
    handleApprovalNotification(notifications) {
        for (const notification of notifications) {
            if (notification.channel === "approval_notification") {
                const { type, approval_id, message } = notification.message;
                this.approvals.push({ type, approval_id, message });
                this.notificationService.notify({
                    type: "info",
                    message,
                    title: type === "assignment" ? "Approval Assigned" : "Approval Update",
                });
            }
        }
        this.render();
    }
    async openApproval(approvalId) {
        const approval = await this.orm.read("approval.request", [approvalId], ["name", "state"]);
        this.env.services.action.doAction({
            name: `Approval Request: ${approval[0].name}`,
            type: "ir.actions.act_window",
            res_model: "approval.request",
            res_id: approvalId,
            view_mode: "form",
        });
    }
}

ApprovalIcon.template = 'cyllo_approval.ApprovalIcon';
ApprovalIcon.components = {Dropdown, DropdownItem ,NotificationItem,MessagingMenu};
export const ApprovalIconItems = {
    Component: ApprovalIcon,
};
registry.category('systray').add('ApprovalIcon', ApprovalIconItems, {sequence: 1000});
