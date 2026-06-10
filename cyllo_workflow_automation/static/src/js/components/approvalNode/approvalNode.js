/** @odoo-module */
const { useState, useRef, onMounted } = owl;
const { onWillStart } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";

/**
 * ApprovalNode — configuration modal for the Approval workflow node.
 *
 * The node is only rendered when cyllo_approval is installed
 * (controlled by state.hasApprovalModule in workflow_automation.js).
 *
 * Three output ports (mirrors Try Catch):
 *   Output 1  →  Approved branch
 *   Output 2  →  Rejected branch
 *   Output 3  →  Timeout branch
 *
 * Tabs:
 *   1. Approval Rule   — select rule type + existing rule OR auto-create
 *   2. Approver        — who approves (user / group / dynamic expression)
 *   3. Notifications   — mirrors approval.rule notification tab
 *   4. Advanced        — auto-approve condition, timeout, result variable
 */
export class ApprovalNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.labelInput = useRef("labelInput");

        this.state2 = useState({
            // Tabs
            activeTab: 'general',

            // General tab
            ruleType: 'server',           // button | state | server

            // Trigger configuration
            buttonId: null,
            stateFieldId: null,
            stateSelectionId: null,
            stateM2oId: null,
            serverActionId: null,

            // Selectable options
            buttons: [],
            serverActions: [],
            stateFields: [],
            stateSelections: [],
            stateM2oValues: [],
            
            // Current model ID
            modelId: null,

            // Approver tab
            approverType: 'user',
            approverId: null,
            approverName: '',
            approverGroupId: null,
            approverGroupName: '',
            approverField: '',
            users: [],
            groups: [],

            // Notifications tab
            allowComment: false,
            notifyEmail: true,
            notifyOnRequest: true,
            notifyOnApprove: true,
            notifyOnReject: true,

            // Advanced tab
            autoRule: '',
            expireAfter: 0,
            resultVariable: '',

            // Validation
            labelError: false,
            approverError: false,
        });

        onWillStart(async () => {
            await this._loadUsers();
            await this._loadGroups();
            await this._loadModelData();
        });

        onMounted(() => {
            if (this.labelInput.el) this.labelInput.el.focus();
            this._restoreFromFieldState();
        });
    }

    // ── Data loaders ────────────────────────────────────────────────────────

    async _loadUsers() {
        try {
            const rows = await this.orm.searchRead(
                'res.users',
                [['active', '=', true], ['share', '=', false]],
                ['id', 'name'],
                { limit: 300, order: 'name asc' }
            );
            this.state2.users = rows.map(r => ({ id: r.id, name: r.name }));
        } catch (e) {
            this.state2.users = [];
        }
    }

    async _loadGroups() {
        try {
            const rows = await this.orm.searchRead(
                'res.groups',
                [],
                ['id', 'full_name'],
                { limit: 300, order: 'full_name asc' }
            );
            this.state2.groups = rows.map(r => ({ id: r.id, name: r.full_name || r.name }));
        } catch (e) {
            this.state2.groups = [];
        }
    }

    async _loadModelData() {
        const modelName = this.env.globalContext ? this.env.globalContext().modelName : null;
        if (!modelName) return;
        try {
            const models = await this.orm.searchRead('ir.model', [['model', '=', modelName]], ['id']);
            if (models.length > 0) {
                this.state2.modelId = models[0].id;
                await Promise.all([
                    this._loadButtons(),
                    this._loadServerActions(),
                    this._loadStateFields()
                ]);
                if (this.state2.stateFieldId) {
                    await this._loadStateValues(this.state2.stateFieldId);
                }
            }
        } catch(e) {
            console.error(e);
        }
    }

    async _loadButtons() {
        if (!this.state2.modelId) return;
        try {
            this.state2.buttons = await this.orm.searchRead('ir.buttons', [['model_id', '=', this.state2.modelId]], ['id', 'name']);
        } catch(e) {}
    }

    async _loadServerActions() {
        if (!this.state2.modelId) return;
        try {
            this.state2.serverActions = await this.orm.searchRead('ir.actions.server', [['model_id', '=', this.state2.modelId]], ['id', 'name']);
        } catch(e) {}
    }

    async _loadStateFields() {
        if (!this.state2.modelId) return;
        try {
            this.state2.stateFields = await this.orm.searchRead('ir.model.fields', [
                ['model_id', '=', this.state2.modelId],
                ['name', 'in', ['state', 'stage_id']]
            ], ['id', 'name', 'field_description', 'ttype', 'relation']);
        } catch(e) {}
    }

    async _loadStateValues(fieldId) {
        if (!fieldId) {
            this.state2.stateSelections = [];
            this.state2.stateM2oValues = [];
            return;
        }
        const field = this.state2.stateFields.find(f => f.id === fieldId);
        if (!field) return;
        
        try {
            if (field.ttype === 'selection') {
                this.state2.stateSelections = await this.orm.searchRead('ir.model.fields.selection', [['field_id', '=', fieldId]], ['id', 'name']);
                this.state2.stateM2oValues = [];
            } else if (field.ttype === 'many2one' && field.relation) {
                this.state2.stateSelections = [];
                // Auto-sync approval.state.value if needed by calling server method or just read
                this.state2.stateM2oValues = await this.orm.searchRead('approval.state.value', [['res_model', '=', field.relation]], ['id', 'name']);
            }
        } catch(e) {}
    }



    _restoreFromFieldState() {
        const fs = this.fieldState;

        // General tab
        this.state2.ruleType = fs.approval_rule_type || 'server';
        this.state2.buttonId = fs.approval_button_id || null;
        this.state2.stateFieldId = fs.approval_state_field_id || null;
        this.state2.stateSelectionId = fs.approval_state_to_selection_id || null;
        this.state2.stateM2oId = fs.approval_state_to_m2o_value_id || null;
        this.state2.serverActionId = fs.approval_server_action_id || null;

        // Approver tab
        this.state2.approverType = fs.approval_approver_type || 'user';
        this.state2.approverId = fs.approval_approver_id || null;
        this.state2.approverGroupId = fs.approval_approver_group_id || null;
        this.state2.approverField = fs.approval_approver_field || '';

        // Notifications tab
        this.state2.allowComment = !!fs.approval_allow_comment;
        this.state2.notifyEmail = fs.approval_notify_email !== undefined ? !!fs.approval_notify_email : true;
        this.state2.notifyOnRequest = fs.approval_notify_on_request !== undefined ? !!fs.approval_notify_on_request : true;
        this.state2.notifyOnApprove = fs.approval_notify_on_approve !== undefined ? !!fs.approval_notify_on_approve : true;
        this.state2.notifyOnReject = fs.approval_notify_on_reject !== undefined ? !!fs.approval_notify_on_reject : true;

        // Advanced tab
        this.state2.autoRule = fs.approval_auto_rule || '';
        this.state2.expireAfter = fs.approval_expire_after || 0;
        this.state2.resultVariable = fs.approval_result_variable || '';
    }

    // ── Tab handlers ─────────────────────────────────────────────────────────

    setTab(tab) { this.state2.activeTab = tab; }

    // ── General tab handlers ─────────────────────────────────────────────────────

    setRuleType(value) {
        this.state2.ruleType = value;
    }

    setButtonId(value) {
        this.state2.buttonId = parseInt(value) || null;
    }

    setServerActionId(value) {
        this.state2.serverActionId = parseInt(value) || null;
    }

    async setStateFieldId(value) {
        const id = parseInt(value) || null;
        this.state2.stateFieldId = id;
        this.state2.stateSelectionId = null;
        this.state2.stateM2oId = null;
        await this._loadStateValues(id);
    }

    setStateSelectionId(value) {
        this.state2.stateSelectionId = parseInt(value) || null;
    }

    setStateM2oId(value) {
        this.state2.stateM2oId = parseInt(value) || null;
    }

    // ── Approver tab handlers ────────────────────────────────────────────────

    setLabel(value) {
        this.fieldState.label = value;
        this.state2.labelError = false;
        this.env.bus.trigger('CHANGE-LABEL', { label: value, nodeId: this.props.id });
    }

    setApproverType(value) {
        this.state2.approverType = value;
        this.state2.approverId = null;
        this.state2.approverGroupId = null;
        this.state2.approverField = '';
        this.state2.approverError = false;
    }

    setApprover(rawValue) {
        this.state2.approverId = parseInt(rawValue) || null;
        this.state2.approverError = false;
    }

    setApproverGroup(rawValue) {
        this.state2.approverGroupId = parseInt(rawValue) || null;
        this.state2.approverError = false;
    }

    setApproverField(value) {
        this.state2.approverField = value;
        this.state2.approverError = false;
    }

    // ── Notification tab handlers ────────────────────────────────────────────

    toggleAllowComment(ev) { this.state2.allowComment = ev.target.checked; }
    toggleNotifyEmail(ev) {
        this.state2.notifyEmail = ev.target.checked;
        if (!this.state2.notifyEmail) {
            this.state2.notifyOnRequest = false;
            this.state2.notifyOnApprove = false;
            this.state2.notifyOnReject = false;
        }
    }
    toggleNotifyOnRequest(ev) { this.state2.notifyOnRequest = ev.target.checked; }
    toggleNotifyOnApprove(ev) { this.state2.notifyOnApprove = ev.target.checked; }
    toggleNotifyOnReject(ev) { this.state2.notifyOnReject = ev.target.checked; }

    // ── Advanced tab handlers ────────────────────────────────────────────────

    setAutoRule(value) { this.state2.autoRule = value; }
    setExpireAfter(value) { this.state2.expireAfter = parseFloat(value) || 0; }
    setResultVariable(value) { this.state2.resultVariable = (value || '').trim(); }

    // ── Validation ───────────────────────────────────────────────────────────

    validateForm() {
        const errors = {};
        if (!this.fieldState.label || !this.fieldState.label.trim()) {
            this.state2.labelError = true;
            errors.label = 'Node label is required.';
        }
        const atype = this.state2.approverType;
        if (atype === 'user' && !this.state2.approverId) {
            this.state2.approverError = true;
            errors.approver = 'Select a specific user as approver.';
        } else if (atype === 'group' && !this.state2.approverGroupId) {
            this.state2.approverError = true;
            errors.approver = 'Select a user group as approver.';
        } else if (atype === 'dynamic' && !(this.state2.approverField || '').trim()) {
            this.state2.approverError = true;
            errors.approver = 'Enter a Python expression for the approver.';
        }
        return { isValid: Object.keys(errors).length === 0, errors };
    }

    // ── Code generation ──────────────────────────────────────────────────────

    generateCode() {
        const resultVar = (this.state2.resultVariable || '').trim();
        const resultVarLine = resultVar ? `\n${resultVar} = approval_branch` : '';
        return '__approval_node_pause__' + resultVarLine;
    }

    // ── Confirm ──────────────────────────────────────────────────────────────

    async onConfirm() {
        const { isValid, errors } = this.validateForm();
        if (!isValid) {
            this.env.services.effect.add({
                title: 'Validation Error',
                message: 'Cannot save Approval node.',
                description: Object.values(errors).join('\n'),
                type: 'notification_panel',
                notificationType: 'warning',
            });
            return;
        }

        // General tab
        this.fieldState.approval_rule_type = this.state2.ruleType;
        this.fieldState.approval_rule_id = false;
        this.fieldState.approval_button_id = this.state2.buttonId;
        this.fieldState.approval_server_action_id = this.state2.serverActionId;
        this.fieldState.approval_state_field_id = this.state2.stateFieldId;
        this.fieldState.approval_state_to_selection_id = this.state2.stateSelectionId;
        this.fieldState.approval_state_to_m2o_value_id = this.state2.stateM2oId;

        // Approver tab
        this.fieldState.approval_approver_type = this.state2.approverType;
        this.fieldState.approval_approver_id = this.state2.approverId;
        this.fieldState.approval_approver_group_id = this.state2.approverGroupId;
        this.fieldState.approval_approver_field = this.state2.approverField;

        // Notifications tab
        this.fieldState.approval_allow_comment = this.state2.allowComment;
        this.fieldState.approval_notify_email = this.state2.notifyEmail;
        this.fieldState.approval_notify_on_request = this.state2.notifyOnRequest;
        this.fieldState.approval_notify_on_approve = this.state2.notifyOnApprove;
        this.fieldState.approval_notify_on_reject = this.state2.notifyOnReject;

        // Advanced tab
        this.fieldState.approval_auto_rule = this.state2.autoRule;
        this.fieldState.approval_expire_after = this.state2.expireAfter;
        this.fieldState.approval_timeout_hours = this.state2.expireAfter;
        this.fieldState.approval_result_variable = this.state2.resultVariable;

        const code = this.generateCode();
        this.state.used_variables = {};
        this.props.onConfirm(this.fieldState, code, this.state.used_variables);
        this.props.close();
    }
}

ApprovalNode.template = 'ApprovalNode';
