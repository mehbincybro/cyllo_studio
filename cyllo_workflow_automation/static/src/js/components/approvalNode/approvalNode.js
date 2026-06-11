/** @odoo-module */
const { useState, useRef, onMounted } = owl;
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
    setup() {
        super.setup();
        this.labelInput = useRef("labelInput");

        this.approvalState = useState({
            ruleType: "button",
            buttonMethod: "",
            serverActionId: null,
            stateFieldId: null,
            stateSelectionId: null,
            stateM2oId: null,
            approverType: "user",
            approverId: null,
            approverGroupId: null,
            subject: "Your Approval is Required",
            notifyEmail: true,
            buttons: [],
            users: [],
            groups: [],
            labelError: false,
            approverError: false,
        });

        onMounted(() => {
            if (this.labelInput.el) this.labelInput.el.focus();
            // Restore saved values
            const fs = this.fieldState;
            this.approvalState.ruleType         = fs.approval_rule_type        || "button";
            this.approvalState.buttonMethod     = fs.approval_button_method    || "";
            this.approvalState.serverActionId   = fs.approval_server_action_id || null;
            this.approvalState.stateFieldId     = fs.approval_state_field_id   || null;
            this.approvalState.stateSelectionId = fs.approval_state_to_selection_id || null;
            this.approvalState.stateM2oId       = fs.approval_state_to_m2o_value_id || null;
            this.approvalState.approverType     = fs.approval_approver_type    || "user";
            this.approvalState.approverId       = fs.approval_approver_id      || null;
            this.approvalState.approverGroupId  = fs.approval_approver_group_id || null;
            this.approvalState.subject          = fs.approval_subject          || "Your Approval is Required";
            this.approvalState.notifyEmail      = fs.approval_notify_email !== false;

            this.approvalState.serverActions    = [];
            this.approvalState.stateFields      = [];
            this.approvalState.stateSelections  = [];
            this.approvalState.stateM2os        = [];
            this.approvalState.activeStateField = null; // To store full field metadata

            this.fetchApprovalData();
        });
    }

    async fetchApprovalData() {
        let modelId = this.props.primaryModelId || this.fieldState.model_id;
        
        if (!modelId && this.variables) {
            const currentRec = this.variables.find(v => v.variable_name === 'current_record');
            if (currentRec && currentRec.modelId) {
                modelId = currentRec.modelId;
            }
        }
        
        try {
            if (modelId) {
                await this.orm.call('ir.buttons', 'action_sync_buttons', [modelId]);
                this.approvalState.buttons = await this.orm.searchRead('ir.buttons', [['model_id', '=', modelId]], ['id', 'name', 'display_name']);
            }
        } catch (e) {
            console.warn("Could not fetch ir.buttons", e);
        }

        try {
            if (modelId) {
                this.approvalState.serverActions = await this.orm.searchRead('ir.actions.server', [['model_id', '=', modelId]], ['id', 'name']);
            }
        } catch (e) {}

        try {
            if (modelId) {
                this.approvalState.stateFields = await this.orm.searchRead(
                    'ir.model.fields', 
                    [['model_id', '=', modelId], ['name', 'in', ['state', 'stage_id']]], 
                    ['id', 'name', 'field_description', 'ttype', 'relation']
                );
                
                // If a state field was already selected, load its options
                if (this.approvalState.stateFieldId) {
                    this.onStateFieldChange(this.approvalState.stateFieldId);
                }
            }
        } catch (e) {}

        try {
            this.approvalState.users = await this.orm.searchRead('res.users', [], ['id', 'name']);
        } catch (e) {}

        try {
            this.approvalState.groups = await this.orm.searchRead('res.groups', [], ['id', 'display_name']);
        } catch (e) {}
    }

    async onStateFieldChange(fieldId) {
        this.approvalState.stateFieldId = parseInt(fieldId) || null;
        if (!this.approvalState.stateFieldId) {
            this.approvalState.activeStateField = null;
            this.approvalState.stateSelections = [];
            this.approvalState.stateM2os = [];
            return;
        }

        const field = this.approvalState.stateFields.find(f => f.id === this.approvalState.stateFieldId);
        this.approvalState.activeStateField = field || null;

        if (field && field.ttype === 'selection') {
            this.approvalState.stateSelections = await this.orm.searchRead(
                'ir.model.fields.selection',
                [['field_id', '=', field.id]],
                ['id', 'name', 'value']
            );
            this.approvalState.stateM2os = [];
            // Reset M2O
            if (this.fieldState.approval_state_field_id !== field.id) {
                this.approvalState.stateM2oId = null;
            }
        } else if (field && field.ttype === 'many2one' && field.relation) {
            this.approvalState.stateM2os = await this.orm.searchRead(
                field.relation,
                [],
                ['id', 'display_name']
            );
            this.approvalState.stateSelections = [];
            // Reset Selection
            if (this.fieldState.approval_state_field_id !== field.id) {
                this.approvalState.stateSelectionId = null;
            }
        }
    }

    setButtonMethod(e) {
        this.approvalState.buttonMethod = e.target.value;
    }

    setServerActionId(e) {
        this.approvalState.serverActionId = parseInt(e.target.value) || null;
    }

    setStateSelectionId(e) {
        this.approvalState.stateSelectionId = parseInt(e.target.value) || null;
    }

    setStateM2oId(e) {
        this.approvalState.stateM2oId = parseInt(e.target.value) || null;
    }

    setApproverUserId(e) {
        this.approvalState.approverId = parseInt(e.target.value) || null;
        this.approvalState.approverError = false;
    }

    setApproverGroupId(e) {
        this.approvalState.approverGroupId = parseInt(e.target.value) || null;
        this.approvalState.approverError = false;
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

    setRuleType(value) {
        this.approvalState.ruleType = value;
    }

    get getLabel() {
        return this.fieldState.label || "";
    }

    setLabel(label) {
        this.fieldState.label = label;
        this.approvalState.labelError = false;
        const nodeId = this.props.id;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId });
    }

    setApproverType(value) {
        this.approvalState.approverType = value;
        this.approvalState.approverError = false;
    }

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
        }

        const rType = this.approvalState.ruleType;
        if (rType === "button" && !this.approvalState.buttonMethod) {
            errors.rule = "Enter the button method.";
        } else if (rType === "server" && !this.approvalState.serverActionId) {
            errors.rule = "Enter the server action ID.";
        } else if (rType === "state" && !this.approvalState.stateFieldId) {
            errors.rule = "Enter the state field ID.";
        }

        return { isValid: Object.keys(errors).length === 0, errors };
    }

    generateCode() {
        return "";
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
        this.fieldState.trigger_type                   = "approval";
        this.fieldState.approval_rule_type             = this.approvalState.ruleType;
        this.fieldState.approval_button_method         = this.approvalState.buttonMethod;
        this.fieldState.approval_server_action_id      = this.approvalState.serverActionId;
        this.fieldState.approval_state_field_id        = this.approvalState.stateFieldId;
        this.fieldState.approval_state_to_selection_id = this.approvalState.stateSelectionId;
        this.fieldState.approval_state_to_m2o_value_id = this.approvalState.stateM2oId;
        this.fieldState.approval_approver_type         = this.approvalState.approverType;
        this.fieldState.approval_approver_id           = this.approvalState.approverId;
        this.fieldState.approval_approver_group_id     = this.approvalState.approverGroupId;
        this.fieldState.approval_subject               = this.approvalState.subject;
        this.fieldState.approval_notify_email          = this.approvalState.notifyEmail;

        const code = this.generateCode();
        this.state.used_variables = {};
        this.props.onConfirm(this.fieldState, code, this.state.used_variables);
        this.props.close();
    }
}

ApprovalNode.template = "ApprovalNode";
