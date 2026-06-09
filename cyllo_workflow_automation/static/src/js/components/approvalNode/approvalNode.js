/** @odoo-module */
const { useState, useRef, onMounted } = owl;
const { onWillStart } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";

/**
 * ApprovalNode — modal configuration for the Human Approval node.
 *
 * The Approval node pauses workflow execution and waits for a human to
 * approve or reject via a secure portal URL. Three output ports are exposed:
 *
 *   Output 1 (Approved)  — nodes executed when the approver approves.
 *   Output 2 (Rejected)  — nodes executed when the approver rejects.
 *   Output 3 (Timeout)   — nodes executed if the request expires before
 *                          a decision is made.
 *
 * Configuration options:
 *   - label                   — display label for the node.
 *   - approverType            — 'user' | 'group' | 'dynamic'.
 *   - approverId              — specific user ID (when type = 'user').
 *   - approverGroupId         — group ID (when type = 'group').
 *   - approverField           — Python expression (when type = 'dynamic').
 *   - subject                 — email/inbox notification subject.
 *   - message                 — notification body.
 *   - notifyEmail             — send email notification.
 *   - notifyInbox             — send Odoo inbox notification.
 *   - expireAfter             — hours until auto-expiry (0 = never).
 *   - autoRule                — Python expression for auto-approval.
 *   - resultVariable          — variable name to store approval status.
 */
export class ApprovalNode extends ConfigurationBase {
    static props = ['*'];
    setup() {
        super.setup();
        this.labelInput = useRef("labelInput");

        this.approvalState = useState({
            approverType: "user",
            approverId: null,
            approverGroupId: null,
            approverField: "",
            subject: "Your Approval is Required",
            message: "",
            notifyEmail: true,
            notifyInbox: true,
            expireAfter: 0,
            autoRule: "",
            resultVariable: "",
            labelError: false,
            approverError: false,
            users: [],
            groups: [],
        });

        onWillStart(async () => {
            try {
                this.approvalState.users = await this.orm.searchRead(
                    "res.users",
                    [["active", "=", true], ["share", "=", false]],
                    ["id", "name"],
                    { limit: 200, order: "name asc" }
                );
                this.approvalState.users = this.approvalState.users.map(u => [u.id, u.name]);
            } catch (e) {
                console.warn("ApprovalNode: could not load users", e);
                this.approvalState.users = [];
            }

            try {
                this.approvalState.groups = await this.orm.searchRead(
                    "res.groups",
                    [],
                    ["id", "name"],
                    { limit: 200, order: "name asc" }
                );
                this.approvalState.groups = this.approvalState.groups.map(g => [g.id, g.name]);
            } catch (e) {
                console.warn("ApprovalNode: could not load groups", e);
                this.approvalState.groups = [];
            }
        });

        onMounted(() => {
            if (this.labelInput.el) this.labelInput.el.focus();
            // Restore saved values
            const fs = this.fieldState;
            this.approvalState.approverType = fs.approval_approver_type || "user";
            this.approvalState.approverId = fs.approval_approver_id || null;
            this.approvalState.approverGroupId = fs.approval_approver_group_id || null;
            this.approvalState.approverField = fs.approval_approver_field || "";
            this.approvalState.subject = fs.approval_subject || "Your Approval is Required";
            this.approvalState.message = fs.approval_message || "";
            this.approvalState.notifyEmail = fs.approval_notify_email !== false;
            this.approvalState.notifyInbox = fs.approval_notify_inbox !== false;
            this.approvalState.expireAfter = fs.approval_expire_after || 0;
            this.approvalState.autoRule = fs.approval_auto_rule || "";
            this.approvalState.resultVariable = fs.approval_result_variable || "";
        });
    }

    // Handlers

    setLabel(value) {
        this.fieldState.label = value;
        this.approvalState.labelError = false;
        this.env.bus.trigger("CHANGE-LABEL", {
            label: value,
            nodeId: this.props.id,
        });
    }

    setApproverType(value) {
        this.approvalState.approverType = value;
        this.approvalState.approverId = null;
        this.approvalState.approverGroupId = null;
        this.approvalState.approverField = "";
        this.approvalState.approverError = false;
    }

    onUserSelected(rawValue) {
        this.approvalState.approverId = parseInt(rawValue) || null;
        this.approvalState.approverError = false;
    }

    onGroupSelected(rawValue) {
        this.approvalState.approverGroupId = parseInt(rawValue) || null;
        this.approvalState.approverError = false;
    }

    setApproverField(value) {
        this.approvalState.approverField = value;
        this.approvalState.approverError = false;
    }

    setSubject(value) { this.approvalState.subject = value; }
    setMessage(value) { this.approvalState.message = value; }
    setNotifyEmail(checked) { this.approvalState.notifyEmail = checked; }
    setNotifyInbox(checked) { this.approvalState.notifyInbox = checked; }
    setExpireAfter(value) { this.approvalState.expireAfter = parseFloat(value) || 0; }
    setAutoRule(value) { this.approvalState.autoRule = value; }
    setResultVariable(value) { this.approvalState.resultVariable = value.trim(); }

    // Validation

    validateForm() {
        const errors = {};

        if (!this.fieldState.label || !this.fieldState.label.trim()) {
            this.approvalState.labelError = true;
            errors.label = "Label is required.";
        }

        const aType = this.approvalState.approverType;
        if (aType === "user" && !this.approvalState.approverId) {
            this.approvalState.approverError = true;
            errors.approver = "Select a specific user as approver.";
        } else if (aType === "group" && !this.approvalState.approverGroupId) {
            this.approvalState.approverError = true;
            errors.approver = "Select a user group as approver.";
        } else if (aType === "dynamic" && !(this.approvalState.approverField || "").trim()) {
            this.approvalState.approverError = true;
            errors.approver = "Enter a Python expression for the approver field.";
        }

        return { isValid: Object.keys(errors).length === 0, errors };
    }

    // Code generation

    /**
     * Generate the Python code injected into the workflow execution context.
     */
    generateCode() {
        const resultVar = (this.approvalState.resultVariable || "").trim();
        const resultVarLine = resultVar ? `\n${resultVar} = approval_branch` : "";
        return "__approval_node_pause__" + resultVarLine;
    }

    // Confirm

    async onConfirm() {
        const { isValid, errors } = this.validateForm();
        if (!isValid) {
            this.env.services.effect.add({
                title: "Validation Error",
                message: "Unable to save Approval node.",
                description: Object.values(errors).join("\n"),
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }

        // Persist config into fieldState
        this.fieldState.approval_approver_type = this.approvalState.approverType;
        this.fieldState.approval_approver_id = this.approvalState.approverId;
        this.fieldState.approval_approver_group_id = this.approvalState.approverGroupId;
        this.fieldState.approval_approver_field = this.approvalState.approverField;
        this.fieldState.approval_subject = this.approvalState.subject;
        this.fieldState.approval_message = this.approvalState.message;
        this.fieldState.approval_notify_email = this.approvalState.notifyEmail;
        this.fieldState.approval_notify_inbox = this.approvalState.notifyInbox;
        this.fieldState.approval_expire_after = this.approvalState.expireAfter;
        this.fieldState.approval_timeout_hours = this.approvalState.expireAfter;
        this.fieldState.approval_auto_rule = this.approvalState.autoRule;
        this.fieldState.approval_result_variable = this.approvalState.resultVariable;

        const code = this.generateCode();
        this.state.used_variables = {};
        this.props.onConfirm(this.fieldState, code, this.state.used_variables);
        this.props.close();
    }
}

ApprovalNode.template = "ApprovalNode";
