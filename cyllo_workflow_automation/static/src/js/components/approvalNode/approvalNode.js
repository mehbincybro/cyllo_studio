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
        });

        onMounted(() => {
            if (this.labelInput.el) this.labelInput.el.focus();
            // Restore saved values
            const fs = this.fieldState;
            this.approvalState.approverType     = fs.approval_approver_type    || "user";
            this.approvalState.approverId       = fs.approval_approver_id      || null;
            this.approvalState.approverGroupId  = fs.approval_approver_group_id || null;
            this.approvalState.approverField    = fs.approval_approver_field   || "";
            this.approvalState.subject          = fs.approval_subject          || "Your Approval is Required";
            this.approvalState.message          = fs.approval_message          || "";
            this.approvalState.notifyEmail      = fs.approval_notify_email !== false;
            this.approvalState.notifyInbox      = fs.approval_notify_inbox !== false;
            this.approvalState.expireAfter      = fs.approval_expire_after     || 0;
            this.approvalState.autoRule         = fs.approval_auto_rule        || "";
            this.approvalState.resultVariable   = fs.approval_result_variable  || "";
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
        this.approvalState.approverError = false;
    }

    setApproverField(value) {
        this.approvalState.approverField = value;
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
        } else if (aType === "dynamic" && !(this.approvalState.approverField || "").trim()) {
            this.approvalState.approverError = true;
            errors.approver = "Enter a Python expression for the approver field.";
        }

        return { isValid: Object.keys(errors).length === 0, errors };
    }

    // Code generation

    /**
     * Generate the Python code injected into the workflow execution context.
     *
     * The generated code:
     *  1. Evaluates the auto-approval rule (if any).
     *  2. Resolves the approver from the configured type.
     *  3. Creates a workflow.approval.request record.
     *  4. Sends notifications.
     *  5. Raises WorkflowApprovalPause to freeze execution.
     *
     * On resume, the engine injects `approval_branch` ('approved'|'rejected'|'timeout')
     * into the context so the three output-port branches can route correctly.
     */
    generateCode() {
        const aType   = this.approvalState.approverType;
        const subject = (this.approvalState.subject || "Your Approval is Required").replace(/'/g, "\\'");
        const expireH = parseFloat(this.approvalState.expireAfter) || 0;
        const autoRule = (this.approvalState.autoRule || "").trim();
        const resultVar = (this.approvalState.resultVariable || "").trim();
        const notifyEmail = this.approvalState.notifyEmail;
        const notifyInbox = this.approvalState.notifyInbox;

        let approverResolutionCode = "";
        if (aType === "user" && this.approvalState.approverId) {
            approverResolutionCode = `_approval_approver = env['res.users'].browse(${this.approvalState.approverId})`;
        } else if (aType === "group" && this.approvalState.approverGroupId) {
            approverResolutionCode = `_approval_approver = env['res.groups'].browse(${this.approvalState.approverGroupId}).users[:1]`;
        } else if (aType === "dynamic") {
            const field = (this.approvalState.approverField || "record.user_id").trim();
            approverResolutionCode = `_approval_approver = (${field})`;
        }

        let autoRuleLine = "";
        if (autoRule) {
            autoRuleLine = `
if (${autoRule}):
    approval_branch = 'approved'
    approval_status = 'approved'
else:`;
        }

        let expireLine = "None";
        if (expireH > 0) {
            expireLine = `fields.Datetime.now() + relativedelta(hours=${expireH})`;
        }

        let resultVarLine = "";
        if (resultVar) {
            resultVarLine = `\n${resultVar} = approval_branch`;
        }

        const baseCode = [
            "# Approval node",
            approverResolutionCode,
            `_approval_subject = '${subject}'`,
            `_approval_notify_email = ${notifyEmail ? 'True' : 'False'}`,
            `_approval_notify_inbox = ${notifyInbox ? 'True' : 'False'}`,
            `_approval_expiration = ${expireLine}`,
            "",
            "# Persist approval request",
            "_approval_ctx = {",
            "    'res_model': current_record._name if current_record else '',",
            "    'res_id': current_record.id if current_record else 0,",
            "    'trigger_type': trigger_type,",
            "}",
            "_approval_req = env['workflow.approval.request'].sudo().create({",
            "    'workflow_id': env['work.auto'].browse(work_auto_id).id if env.context.get('work_auto_id') else False,",
            "    'approver_id': _approval_approver.id if _approval_approver else False,",
            "    'approver_name': _approval_approver.name if _approval_approver else '',",
            "    'approver_email': _approval_approver.email if _approval_approver else '',",
            "    'res_model': _approval_ctx.get('res_model', ''),",
            "    'res_id': _approval_ctx.get('res_id', 0),",
            "    'execution_context': _approval_ctx,",
            "    'expiration': _approval_expiration,",
            "    'state': 'pending',",
            "})",
            "env['workflow.approval.log'].sudo().create({",
            "    'request_id': _approval_req.id,",
            "    'event': 'created',",
            "    'user_id': env.uid,",
            "})",
            "",
            "# Build approval URL",
            "_approval_base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', '')",
            "_approval_url = f'{_approval_base_url}/workflow/approval/{_approval_req.token}'",
            "",
            "# Send notifications",
            "if _approval_notify_email and _approval_approver and _approval_approver.email:",
            "    _approval_body = f'''<p>Hello {_approval_approver.name},</p>",
            "    <p>Your approval is required. Please click the link below:</p>",
            "    <p><a href=\"{_approval_url}\" style=\"background:#875a7b;color:white;padding:8px 20px;",
            "    border-radius:4px;text-decoration:none;\">Review & Approve</a></p>",
            "    <p>Subject: {_approval_subject}</p>'''",
            "    env['mail.mail'].sudo().create({",
            "        'subject': _approval_subject,",
            "        'body_html': _approval_body,",
            "        'email_to': _approval_approver.email,",
            "    }).send()",
            "    env['workflow.approval.log'].sudo().create({",
            "        'request_id': _approval_req.id,",
            "        'event': 'notified',",
            "        'user_id': env.uid,",
            "        'comment': 'Email sent to ' + _approval_approver.email,",
            "    })",
            "if _approval_notify_inbox and _approval_approver:",
            "    try:",
            "        _approval_approver.sudo().notify_warning(",
            "            _approval_subject,",
            "            f'Approval required. Open: {_approval_url}',",
            "        )",
            "    except Exception:",
            "        pass",
            "",
            "# Pause execution",
            "raise WorkflowApprovalPause(_approval_req.id, _approval_req.token)",
        ].join("\n");

        if (autoRule) {
            return (
                `# Auto-approval rule check\n` +
                `if (${autoRule}):\n` +
                `    approval_branch = 'approved'\n` +
                `    approval_status = 'approved'\n` +
                resultVarLine.replace(/^/gm, "    ") +
                `\nelse:\n` +
                baseCode.split("\n").map(l => `    ${l}`).join("\n") +
                (resultVar ? `\n    ${resultVar} = approval_branch` : "")
            );
        }

        return baseCode + resultVarLine;
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
        this.fieldState.approval_approver_type     = this.approvalState.approverType;
        this.fieldState.approval_approver_id       = this.approvalState.approverId;
        this.fieldState.approval_approver_group_id = this.approvalState.approverGroupId;
        this.fieldState.approval_approver_field    = this.approvalState.approverField;
        this.fieldState.approval_subject           = this.approvalState.subject;
        this.fieldState.approval_message           = this.approvalState.message;
        this.fieldState.approval_notify_email      = this.approvalState.notifyEmail;
        this.fieldState.approval_notify_inbox      = this.approvalState.notifyInbox;
        this.fieldState.approval_expire_after      = this.approvalState.expireAfter;
        this.fieldState.approval_auto_rule         = this.approvalState.autoRule;
        this.fieldState.approval_result_variable   = this.approvalState.resultVariable;

        const code = this.generateCode();
        this.state.used_variables = {};
        this.props.onConfirm(this.fieldState, code, this.state.used_variables);
        this.props.close();
    }
}

ApprovalNode.template = "ApprovalNode";
