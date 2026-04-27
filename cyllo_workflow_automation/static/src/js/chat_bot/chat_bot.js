/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useState } from "@odoo/owl";
import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";

// ─── Global variable IDs (must match what WorkFlowAuto seeds into env.globalVariables) ───
const CURRENT_RECORD_VAR_ID   = "global/variable/current/rec";
const CURRENT_RECORD_VAR_NAME = "current_record";
const CURRENT_USER_VAR_ID     = "global/variable/current/user";
const CURRENT_USER_VAR_NAME   = "current_user";
const CURRENT_DATE_VAR_ID     = "global/variable/current/date";
const CURRENT_DATE_VAR_NAME   = "current_date";

// Monotonic counter so every message gets a unique ID regardless of timing
let _msgIdCounter = 0;
function _nextMsgId() {
    return ++_msgIdCounter;
}

class WorkFlowAutoOverride extends WorkFlowAuto {

    setup() {
        super.setup();
        this._fieldCache = new Map();
        // FIX: added aiLoading flag to prevent double-submission and show spinner
        this.state = useState({
            nodeDetails: [],
            actions: [],
            aiChatOpen: false,
            aiInput: "",
            aiMessages: [],
            aiLoading: false,
        });
    }

    settingModelState(data) {
        if (!data) return;
        this.state.modelState = data.modelState || [];
    }

    openAiChat() {
        this.state.aiChatOpen = !this.state.aiChatOpen;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // UI helpers
    // ─────────────────────────────────────────────────────────────────────────

    // FIX: use _nextMsgId() for truly unique IDs instead of array-index-based IDs
    _pushAiMessage(text, options = {}) {
        const { type = 'info' } = options;
        this.state.aiMessages.push({ from: 'ai', text, id: _nextMsgId(), type });
        this._scrollChatToBottom();
    }

    // FIX: auto-scroll the chat output div to the latest message
    _scrollChatToBottom() {
        // Use a microtask so the DOM has updated before we scroll
        Promise.resolve().then(() => {
            const el = this.__owl__?.refs?.aiChatOutput;
            if (el) {
                el.scrollTop = el.scrollHeight;
            }
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Canvas helpers
    // ─────────────────────────────────────────────────────────────────────────

    async _addNode(name, posX, posY, selectedValue, record, action, type, triggerType) {
        const before = new Set(
            Object.values(this.editor.drawflow.drawflow.Home.data).map(n => n.id)
        );
        await this.addNodeToDrawFlow(name, posX, posY, selectedValue, record, action, type, triggerType);
        const dfData = this.editor.drawflow.drawflow.Home.data;
        const newNode = Object.values(dfData).find(n => !before.has(n.id));
        if (!newNode) return { dfId: null, nodeId: null };
        return { dfId: newNode.id, nodeId: newNode.data.nodeId };
    }

    _connectNodes(outputDfId, inputDfId, outputClass = 'output_1', inputClass = 'input_1') {
        if (!outputDfId || !inputDfId) return;
        this.editor.addConnection(outputDfId, inputDfId, outputClass, inputClass);
    }

    _focusAiWorkflow(drawflowIds = []) {
        const uniqueIds = [...new Set(drawflowIds.filter(Boolean).map((id) => Number(id)))];
        if (!uniqueIds.length) {
            return;
        }
        requestAnimationFrame(() => requestAnimationFrame(() => {
            const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
            const nodes = uniqueIds
                .map((id) => flowData[id])
                .filter(Boolean);
            if (!nodes.length || typeof this.getViewportBoundsForNodes !== 'function') {
                return;
            }

            const viewport = this.getViewportBoundsForNodes(nodes);
            if (!viewport) {
                return;
            }

            const targetZoom = 1;
            const drawBoardEl = this.drawBoard?.el;
            if (!drawBoardEl || typeof this.getNodeCanvasBounds !== 'function') {
                return;
            }

            const bounds = nodes.reduce((acc, node) => {
                const nodeBounds = this.getNodeCanvasBounds(node);
                if (!nodeBounds) {
                    return acc;
                }
                return {
                    minX: Math.min(acc.minX, nodeBounds.left),
                    minY: Math.min(acc.minY, nodeBounds.top),
                    maxX: Math.max(acc.maxX, nodeBounds.right),
                    maxY: Math.max(acc.maxY, nodeBounds.bottom),
                };
            }, {
                minX: Infinity,
                minY: Infinity,
                maxX: -Infinity,
                maxY: -Infinity,
            });

            if (!Number.isFinite(bounds.minX)) {
                return;
            }

            const viewportWidth = drawBoardEl.clientWidth;
            const viewportHeight = drawBoardEl.clientHeight;
            const width = Math.max(1, bounds.maxX - bounds.minX);
            const height = Math.max(1, bounds.maxY - bounds.minY);
            const targetX = Math.max(48, (viewportWidth - width) / 2) - bounds.minX;
            const targetY = Math.max(32, (viewportHeight - height) / 2) - bounds.minY;

            this.initialViewport = {
                canvas_x: targetX,
                canvas_y: targetY,
                zoom: targetZoom,
            };

            if (typeof this.animateCanvasFocus === 'function') {
                this.animateCanvasFocus(targetX, targetY, targetZoom);
            } else if (typeof this.focusCanvasOnNodes === 'function') {
                this.focusCanvasOnNodes(nodes);
            }
        }));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Field definitions cache
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Fetches all field defs for a model including type, relation, string AND
     * selection — so selection fields (state, payment_state, etc.) get their
     * full option list and show correctly in the condition value dropdown.
     */
    async _getModelFieldDefs(modelName) {
        if (!modelName) return {};
        if (!this._fieldCache.has(modelName)) {
            this._fieldCache.set(
                modelName,
                this.orm.call(modelName, 'fields_get', [[], ['type', 'relation', 'string', 'selection']])
                    .catch(() => ({}))
            );
        }
        return await this._fieldCache.get(modelName);
    }

    _findFieldByCandidates(fieldDefs, candidates, allowedRelations = []) {
        for (const candidate of candidates) {
            const fieldDef = fieldDefs?.[candidate];
            if (!fieldDef) continue;
            if (!allowedRelations.length || allowedRelations.includes(fieldDef.relation || '')) {
                return { name: candidate, ...fieldDef };
            }
        }
        return null;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Condition tree builder
    // ─────────────────────────────────────────────────────────────────────────

    _buildConditionTreeValue(aiConditions, modelName, fieldDefs = {}) {
        if (!aiConditions || !aiConditions.length) return null;

        const conditions = aiConditions.map((cond) => ({
            type: 'simple',
            fieldType: 'record',
            field: {
                record: CURRENT_RECORD_VAR_ID,
                path: cond.field,
                info: {
                    fieldDef: this._getConditionFieldDef(modelName, cond.field, cond.value, fieldDefs),
                    resModel: modelName,
                }
            },
            operator: this._normalizeConditionOperator(cond.operator),
            value: {
                value: cond.value,
                fieldType: 'static',
            },
            logicalOperator: 'and',
        }));

        return [{ conditions, groupOperator: 'and' }];
    }

    _getConditionFieldDef(modelName, fieldName, value, fieldDefs = {}) {
        const fieldDef = fieldDefs?.[fieldName];
        if (fieldDef) {
            return {
                type: fieldDef.type,
                ...(fieldDef.relation  ? { relation:  fieldDef.relation  } : {}),
                ...(fieldDef.selection ? { selection: fieldDef.selection } : {}),
                ...(fieldName          ? { name:      fieldName           } : {}),
            };
        }
        // Fallback: guess type from the JS value
        return {
            type: this._guessFieldType(value),
            ...(fieldName ? { name: fieldName } : {}),
        };
    }

    _guessFieldType(value) {
        if (typeof value === 'boolean') return 'boolean';
        if (typeof value === 'number')  return 'float';
        return 'char';
    }

    _normalizeConditionOperator(operator) {
        if (!operator) return '=';
        if (operator === '==') return '=';
        return operator;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Selection / variable builders
    // ─────────────────────────────────────────────────────────────────────────

    _currentRecordRef() {
        return { value: CURRENT_RECORD_VAR_ID, label: CURRENT_RECORD_VAR_NAME };
    }

    _buildVariableSelection(variableId, variableName) {
        return {
            selectionType: 'variable',
            value: {
                selectedVariable: variableId,
                pathValue: variableName,
                isVariable: true,
            },
        };
    }

    _buildStaticSelection(value) {
        return { selectionType: 'static', value };
    }

    _computePathValue(path, fieldType) {
        if (!path) return '';
        if (fieldType === 'many2one') return `${path}.id`;
        if (fieldType === 'many2many' || fieldType === 'one2many') return `${path}.ids`;
        return path;
    }

    _buildCurrentRecordPath(sourceModel, path, fieldType = 'char', relation = null) {
        return {
            selectionType: 'record',
            value: {
                record: CURRENT_RECORD_VAR_ID,
                path,
                pathValue: this._computePathValue(path, fieldType),
                info: {
                    fieldDef: {
                        type: fieldType,
                        ...(relation ? { relation } : {}),
                    },
                    resModel: sourceModel,
                },
            },
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Recipient / assignee / deadline resolvers
    // ─────────────────────────────────────────────────────────────────────────

    _normalizeText(value) {
        return String(value || '').toLowerCase();
    }

    _hasAnyToken(text, tokens) {
        return tokens.some((token) => text.includes(token));
    }

    _resolveMailRecipientSelection(queryText, act, modelName, fieldDefs) {
        const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);

        if (this._hasAnyToken(hintText, ['notify me', 'send me', 'mail me', 'email me', 'current user'])) {
            return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
        }

        const partnerField  = this._findFieldByCandidates(fieldDefs,
            ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
            ['res.partner']);
        const userField     = this._findFieldByCandidates(fieldDefs,
            ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
            ['res.users']);
        const employeeField = this._findFieldByCandidates(fieldDefs,
            ['employee_id', 'user_employee_id'],
            ['hr.employee']);

        if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
            return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
        }
        if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user']) && userField) {
            return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
        }
        if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
            return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
        }

        // Auto-fallback: prefer partner, then user, then current user
        if (partnerField)  return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
        if (userField)     return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
        if (employeeField) return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
        return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
    }

    _resolveSmsRecipientSelection(queryText, act, modelName, fieldDefs) {
        const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);

        if (this._hasAnyToken(hintText, ['notify me', 'send me', 'text me', 'sms me', 'current user'])) {
            return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
        }

        const partnerField  = this._findFieldByCandidates(fieldDefs,
            ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
            ['res.partner']);
        const userField     = this._findFieldByCandidates(fieldDefs,
            ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
            ['res.users']);
        const employeeField = this._findFieldByCandidates(fieldDefs,
            ['employee_id', 'user_employee_id'],
            ['hr.employee']);

        if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
            return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
        }
        if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user']) && userField) {
            return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
        }
        if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
            return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
        }

        if (partnerField)  return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
        if (userField)     return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
        if (employeeField) return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
        return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
    }

    _resolveActivityAssigneeSelection(queryText, act, modelName, fieldDefs) {
        const hintText  = this._normalizeText(`${queryText} ${act?.assignee_role || ''}`);
        const userField = this._findFieldByCandidates(fieldDefs,
            ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
            ['res.users']);

        if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user'])
            && userField) {
            return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
        }
        return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
    }

    _resolveActivityDeadlineSelection(queryText, act) {
        const explicitDate = String(act?.deadline || '').trim();
        if (/^\d{4}-\d{2}-\d{2}$/.test(explicitDate)) {
            return this._buildStaticSelection(explicitDate);
        }
        // Always default to current_date variable so nodes open without errors
        return this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Node data builders (one per action type)
    // ─────────────────────────────────────────────────────────────────────────

    _buildWarningNodeData(act) {
        return {
            label:        act.label   || "Warning",
            warning_type: "error",
            warning:      "UserError",
            warning_text: act.message || "An error has occurred.",
        };
    }

    _buildMailNodeData(act, context = {}) {
        const subject = act.subject || act.summary || "Notification";
        const body    = act.body    || act.message  || "";
        return {
            label:           act.label || "Send Mail",
            mail_isTemplate: false,
            mail_record:     this._currentRecordRef(),
            mail_subject:    this._buildStaticSelection(subject),
            mail_body:       body,
            mail_to:         [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
        };
    }

    _buildSmsNodeData(act, context = {}) {
        const message = act.message || act.body || "";
        return {
            label:           act.label || "Send SMS",
            sms_isTemplate:  false,
            sms_record:      this._currentRecordRef(),
            sms_message:     message,
            sms_partner_ids: [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
        };
    }

    _buildActivityNodeData(act, activityType, context = {}) {
        const summary = act.summary || act.message || "Follow up";
        return {
            label:             act.label || "Activity",
            activity_record:   this._currentRecordRef(),
            activity_type:     activityType || null,
            activity_summary:  summary,
            activity_deadline: context.deadlineSelection  || this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME),
            activity_user:     context.assigneeSelection  || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME),
        };
    }

    async _resolveRelationIds(relationModel, rawValue, { createIfMissing = false } = {}) {
        const values = Array.isArray(rawValue) ? rawValue : [rawValue];
        const normalizedValues = values
            .map((value) => typeof value === 'string' ? value.trim() : value)
            .filter((value) => value !== undefined && value !== null && value !== '');

        if (!relationModel || !normalizedValues.length) {
            return [];
        }

        const numericIds = normalizedValues
            .map((value) => typeof value === 'number' ? value : (typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : null))
            .filter((value) => Number.isInteger(value));
        if (numericIds.length === normalizedValues.length) {
            return numericIds;
        }

        const resolvedIds = [];
        for (const value of normalizedValues) {
            if (typeof value === 'number') {
                resolvedIds.push(value);
                continue;
            }

            let records = [];
            const candidateDomains = [
                [['name', '=', value]],
                [['display_name', '=', value]],
                [['name', 'ilike', value]],
                [['display_name', 'ilike', value]],
            ];

            for (const domain of candidateDomains) {
                try {
                    records = await this.orm.searchRead(relationModel, domain, ['id'], { limit: 1 });
                } catch {
                    records = [];
                }
                if (records.length) {
                    break;
                }
            }

            if (!records.length && createIfMissing) {
                try {
                    const [createdId] = await this.orm.create(relationModel, [{ name: value }]);
                    if (createdId) {
                        records = [{ id: createdId }];
                    }
                } catch {
                    records = [];
                }
            }

            if (records.length) {
                resolvedIds.push(records[0].id);
            }
        }

        return [...new Set(resolvedIds)];
    }

    async _buildWriteNodeData(act, modelName, fieldDefs = {}) {
        const fieldDef = fieldDefs?.[act.field] || {};
        let resolvedValue = act.value !== undefined ? act.value : "";
        const relationModel = fieldDef.relation || null;

        if (fieldDef.type === 'many2many' || fieldDef.type === 'one2many') {
            resolvedValue = await this._resolveRelationIds(relationModel, act.value, {
                createIfMissing: relationModel === 'res.partner.category',
            });
        } else if (fieldDef.type === 'many2one') {
            const [resolvedId] = await this._resolveRelationIds(relationModel, act.value);
            resolvedValue = resolvedId || false;
        }

        const treeItem = {
            id:            Date.now(),
            path:          act.field  || "",
            value:         resolvedValue,
            type:          fieldDef.type || this._guessFieldType(act.value),
            selectionType: 'static',
        };
        return {
            label:                 act.label || "Write Record",
            write_selected_record: this._currentRecordRef(),
            write_field_value:     JSON.stringify([treeItem]),
        };
    }

    async _buildActionNodeData(act, activityType, context = {}) {
        switch (act.type) {
            case 'Warning':  return this._buildWarningNodeData(act);
            case 'Mail':     return this._buildMailNodeData(act, context);
            case 'SMS':      return this._buildSmsNodeData(act, context);
            case 'Activity': return this._buildActivityNodeData(act, activityType, context);
            case 'Write':    return this._buildWriteNodeData(act, context.modelName, context.fieldDefs || {});
            default:         return act.label ? { label: act.label } : null;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Enter-key handler for the chat input
    // ─────────────────────────────────────────────────────────────────────────

    // FIX: allow pressing Enter to send message (Shift+Enter does nothing extra)
    onAiInputKeydown(ev) {
        if (ev.key === 'Enter' && !ev.shiftKey) {
            ev.preventDefault();
            this.sendAiMessage();
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Main send handler
    // ─────────────────────────────────────────────────────────────────────────

    async sendAiMessage() {
        const userQuery = (this.state.aiInput || '').trim();
        if (!userQuery) return;

        // FIX: guard against double-submission while AI is still processing
        if (this.state.aiLoading) return;

        // FIX: use _nextMsgId() for unique IDs
        const userMsgId = _nextMsgId();
        this.state.aiMessages.push({ from: 'user', text: userQuery, id: userMsgId, type: 'info' });
        this.state.aiInput = "";
        this.state.aiLoading = true;
        this._scrollChatToBottom();

        const aiResponseId = _nextMsgId();
        let aiData;

        try {
            // ── Step 1: Call AI backend ──────────────────────────────────────
            try {
                const result = await this.orm.call('chat.bot', 'my_python_method', [userQuery]);
                aiData = typeof result === 'string' ? JSON.parse(result) : result;
            } catch (e) {
                console.error('AI call failed:', e);
                const rpcMessage = e?.data?.message || e?.message || 'Unknown RPC error.';
                this._pushAiMessage(`AI call failed: ${rpcMessage}`, { id: aiResponseId, type: 'error' });
                return;
            }

            // ── Step 2: Validate AI response ─────────────────────────────────
            if (aiData?.error) {
                const errorText = [aiData.error, aiData.details].filter(Boolean).join(' — ');
                this._pushAiMessage(errorText, { id: aiResponseId, type: 'error' });
                return;
            }

            if (!aiData?.object) {
                this._pushAiMessage(
                    'No model was returned by the AI. Please rephrase your query.',
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }

            if (!aiData?.trigger) {
                this._pushAiMessage(
                    'No trigger was returned by the AI. Please rephrase your query.',
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }

            if (!aiData?.actions?.length) {
                this._pushAiMessage(
                    'No actions were returned by the AI. Please rephrase your query.',
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }

            // ── Step 3: Resolve Odoo model ───────────────────────────────────
            const modelName = aiData.object.trim();
            let res;
            try {
                res = await this.orm.searchRead(
                    'ir.model',
                    [['model', '=', modelName]],
                    ['id', 'display_name', 'model']
                );
                // Fallback: ilike search if exact match fails
                if (!res?.length) {
                    res = await this.orm.searchRead(
                        'ir.model',
                        [['model', 'ilike', modelName]],
                        ['id', 'display_name', 'model']
                    );
                }
            } catch (e) {
                this._pushAiMessage(
                    `Failed to search for model "${modelName}": ${e?.message || e}`,
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }

            if (!res?.length) {
                this._pushAiMessage(
                    `Model "${modelName}" was not found. Please install the required module and try again.`,
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }

            const modelId            = res[0].id;
            const modelTechnicalName = res[0].model;
            const modelDisplayName   = res[0].display_name;

            // ── Step 4: Fetch field definitions (includes selection options) ──
            const modelFieldDefs = await this._getModelFieldDefs(modelTechnicalName);

            // ── Step 5: Pre-resolve activity type ────────────────────────────
            let defaultActivityType = null;
            const hasActivity = (aiData.actions || []).some(a => a.type === 'Activity');
            if (hasActivity) {
                try {
                    let actTypes = await this.orm.searchRead(
                        'mail.activity.type',
                        [['name', 'ilike', 'to-do']],
                        ['id', 'name'],
                        { limit: 1 }
                    );
                    if (!actTypes.length) {
                        actTypes = await this.orm.searchRead(
                            'mail.activity.type',
                            [],
                            ['id', 'name'],
                            { limit: 1 }
                        );
                    }
                    if (actTypes.length) {
                        defaultActivityType = { id: actTypes[0].id, name: actTypes[0].name };
                    }
                } catch (e) {
                    console.warn('Could not fetch mail.activity.type:', e);
                }
            }

            // ── Step 6: Set up the primary model node ─────────────────────────
            try {
                await this.onSelectPrimary([{ id: modelId, display_name: modelDisplayName, model: modelTechnicalName }]);
            } catch (e) {
                this._pushAiMessage(
                    `Failed to set up model node: ${e?.message || e}`,
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }
            await new Promise(r => setTimeout(r, 150));

            const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
                .find(n => n.data.type === 'model');
            const modelDfId = modelDfNode ? modelDfNode.id : null;
            const createdNodeDfIds = modelDfId ? [modelDfId] : [];

            // ── Step 7: Resolve trigger work.function ─────────────────────────
            const TRIGGER_FUNC_NAMES = {
                'On Create': 'create',
                'On Write':  'write',
                'On Unlink': 'unlink',
            };
            const funcName = TRIGGER_FUNC_NAMES[aiData.trigger] || 'create';

            let triggerFunctions;
            try {
                triggerFunctions = await this.orm.searchRead(
                    'work.function',
                    [['func_name', '=', funcName]],
                    ['id', 'name', 'trigger_type']
                );
            } catch (e) {
                this._pushAiMessage(
                    `Failed to search trigger functions: ${e?.message || e}`,
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }

            if (!triggerFunctions.length) {
                this._pushAiMessage(
                    `Trigger function "${funcName}" was not found in the database.`,
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }

            const triggerFn   = triggerFunctions[0];
            const actionId    = String(triggerFn.id);
            const triggerType = triggerFn.trigger_type;

            // ── Step 8: Add trigger node ──────────────────────────────────────
            this.state.nodeDetails = this.state.nodeDetails || [];
            let triggerDfId;
            try {
                const result = await this._addNode(
                    aiData.trigger, 538, 340,
                    modelDisplayName, modelId, actionId, 'trigger', triggerType
                );
                triggerDfId = result.dfId;
                if (triggerDfId) {
                    createdNodeDfIds.push(triggerDfId);
                }
            } catch (e) {
                this._pushAiMessage(
                    `Failed to add trigger node: ${e?.message || e}`,
                    { id: aiResponseId, type: 'error' }
                );
                return;
            }
            await new Promise(r => setTimeout(r, 100));

            // ── Step 9: Connect model → trigger ──────────────────────────────
            if (modelDfId && triggerDfId) {
                this._connectNodes(modelDfId, triggerDfId);
            }
            await new Promise(r => setTimeout(r, 80));

            // ── Step 10: Add Condition node (only when AI returned conditions) ─
            let conditionDfId   = null;
            let conditionNodeId = null;

            if (aiData.conditions && aiData.conditions.length > 0) {
                try {
                    const { dfId: cDfId, nodeId: cNodeId } = await this._addNode(
                        'Condition', 538, 480,
                        modelDisplayName, modelId, null, null
                    );
                    conditionDfId   = cDfId;
                    conditionNodeId = cNodeId;
                    if (conditionDfId) {
                        createdNodeDfIds.push(conditionDfId);
                    }
                } catch (e) {
                    console.warn('Failed to add Condition node:', e);
                }

                if (triggerDfId && conditionDfId) {
                    this._connectNodes(triggerDfId, conditionDfId);
                }
                await new Promise(r => setTimeout(r, 80));

                if (conditionNodeId) {
                    const conditionTreeValue = this._buildConditionTreeValue(
                        aiData.conditions,
                        modelTechnicalName,
                        modelFieldDefs
                    );
                    if (conditionTreeValue) {
                        try {
                            await this.orm.write('node.struct', [conditionNodeId], {
                                label: "Condition",
                                condition_tree_value: conditionTreeValue,
                            });
                        } catch (e) {
                            console.warn('Could not save condition_tree_value:', e);
                        }
                    }
                }
            }

            // ── Step 11: Add action nodes ─────────────────────────────────────
            const actionParentDfId = conditionDfId ?? triggerDfId;
            const actions          = aiData.actions || [];

            for (let i = 0; i < actions.length; i++) {
                const act      = actions[i];
                const nodeType = act?.type || 'Warning';

                let actDfId, actNodeId;
                try {
                    const result = await this._addNode(
                        nodeType,
                        660 + (i * 260), 620,
                        modelDisplayName, modelId, null, null
                    );
                    actDfId   = result.dfId;
                    actNodeId = result.nodeId;
                    if (actDfId) {
                        createdNodeDfIds.push(actDfId);
                    }
                } catch (e) {
                    console.warn(`Failed to add action node (${nodeType}):`, e);
                    continue;
                }
                await new Promise(r => setTimeout(r, 80));

                if (actNodeId) {
                    const actionContext = {};
                    if (nodeType === 'Mail') {
                        actionContext.recipientSelection = this._resolveMailRecipientSelection(
                            userQuery, act, modelTechnicalName, modelFieldDefs
                        );
                    } else if (nodeType === 'SMS') {
                        actionContext.recipientSelection = this._resolveSmsRecipientSelection(
                            userQuery, act, modelTechnicalName, modelFieldDefs
                        );
                    } else if (nodeType === 'Activity') {
                        actionContext.assigneeSelection = this._resolveActivityAssigneeSelection(
                            userQuery, act, modelTechnicalName, modelFieldDefs
                        );
                        actionContext.deadlineSelection = this._resolveActivityDeadlineSelection(
                            userQuery, act
                        );
                    }

                    actionContext.modelName = modelTechnicalName;
                    actionContext.fieldDefs = modelFieldDefs;
                    const nodeData = await this._buildActionNodeData(act, defaultActivityType, actionContext);
                    if (nodeData) {
                        try {
                            await this.orm.write('node.struct', [actNodeId], nodeData);
                        } catch (e) {
                            console.warn(`Could not save config for ${nodeType} node:`, e);
                        }
                    }
                }

                if (actionParentDfId && actDfId) {
                    this._connectNodes(actionParentDfId, actDfId, 'output_1');
                }
                await new Promise(r => setTimeout(r, 60));
            }

            // ── Step 12: Success message ──────────────────────────────────────
            const condCount = aiData.conditions?.length ?? 0;
            const actCount  = actions.length;
            const summary =
                `✓ Workflow built: ${aiData.trigger} on ${modelDisplayName}` +
                (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
                ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;

            this._focusAiWorkflow(createdNodeDfIds);
            this._pushAiMessage(summary, { id: aiResponseId });

        } finally {
            // FIX: always clear the loading flag, even if an error/return happened early
            this.state.aiLoading = false;
        }
    }
}

WorkFlowAutoOverride.template = "client_action.automation_view";

registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });





// /** @odoo-module **/
// import { registry } from "@web/core/registry";
// import { useState } from "@odoo/owl";
// import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";
//
// // ─── Global variable IDs (must match what WorkFlowAuto seeds into env.globalVariables) ───
// const CURRENT_RECORD_VAR_ID   = "global/variable/current/rec";
// const CURRENT_RECORD_VAR_NAME = "current_record";
// const CURRENT_USER_VAR_ID     = "global/variable/current/user";
// const CURRENT_USER_VAR_NAME   = "current_user";
// const CURRENT_DATE_VAR_ID     = "global/variable/current/date";
// const CURRENT_DATE_VAR_NAME   = "current_date";
//
// class WorkFlowAutoOverride extends WorkFlowAuto {
//
//     setup() {
//         super.setup();
//         this._fieldCache = new Map();
//         this.state = useState({
//             nodeDetails: [],
//             actions: [],
//             aiChatOpen: false,
//             aiInput: "",
//             aiMessages: [],
//         });
//     }
//
//     settingModelState(data) {
//         if (!data) return;
//         this.state.modelState = data.modelState || [];
//     }
//
//     openAiChat() {
//         this.state.aiChatOpen = !this.state.aiChatOpen;
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // UI helpers
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _pushAiMessage(text, options = {}) {
//         const { id, type = 'info' } = options;
//         this.state.aiMessages.push({ from: 'ai', text, id, type });
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Canvas helpers
//     // ─────────────────────────────────────────────────────────────────────────
//
//     async _addNode(name, posX, posY, selectedValue, record, action, type, triggerType) {
//         const before = new Set(
//             Object.values(this.editor.drawflow.drawflow.Home.data).map(n => n.id)
//         );
//         await this.addNodeToDrawFlow(name, posX, posY, selectedValue, record, action, type, triggerType);
//         const dfData = this.editor.drawflow.drawflow.Home.data;
//         const newNode = Object.values(dfData).find(n => !before.has(n.id));
//         if (!newNode) return { dfId: null, nodeId: null };
//         return { dfId: newNode.id, nodeId: newNode.data.nodeId };
//     }
//
//     _connectNodes(outputDfId, inputDfId, outputClass = 'output_1', inputClass = 'input_1') {
//         if (!outputDfId || !inputDfId) return;
//         this.editor.addConnection(outputDfId, inputDfId, outputClass, inputClass);
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Field definitions cache
//     // ─────────────────────────────────────────────────────────────────────────
//
//     /**
//      * Fetches all field defs for a model including type, relation, string AND
//      * selection — so selection fields (state, payment_state, etc.) get their
//      * full option list and show correctly in the condition value dropdown.
//      */
//     async _getModelFieldDefs(modelName) {
//         if (!modelName) return {};
//         if (!this._fieldCache.has(modelName)) {
//             this._fieldCache.set(
//                 modelName,
//                 this.orm.call(modelName, 'fields_get', [[], ['type', 'relation', 'string', 'selection']])
//                     .catch(() => ({}))
//             );
//         }
//         return await this._fieldCache.get(modelName);
//     }
//
//     _findFieldByCandidates(fieldDefs, candidates, allowedRelations = []) {
//         for (const candidate of candidates) {
//             const fieldDef = fieldDefs?.[candidate];
//             if (!fieldDef) continue;
//             if (!allowedRelations.length || allowedRelations.includes(fieldDef.relation || '')) {
//                 return { name: candidate, ...fieldDef };
//             }
//         }
//         return null;
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Condition tree builder
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _buildConditionTreeValue(aiConditions, modelName, fieldDefs = {}) {
//         if (!aiConditions || !aiConditions.length) return null;
//
//         const conditions = aiConditions.map((cond) => ({
//             type: 'simple',
//             fieldType: 'record',
//             field: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path: cond.field,
//                 info: {
//                     fieldDef: this._getConditionFieldDef(modelName, cond.field, cond.value, fieldDefs),
//                     resModel: modelName,
//                 }
//             },
//             operator: this._normalizeConditionOperator(cond.operator),
//             value: {
//                 value: cond.value,
//                 fieldType: 'static',
//             },
//             logicalOperator: 'and',
//         }));
//
//         return [{ conditions, groupOperator: 'and' }];
//     }
//
//     _getConditionFieldDef(modelName, fieldName, value, fieldDefs = {}) {
//         const fieldDef = fieldDefs?.[fieldName];
//         if (fieldDef) {
//             return {
//                 type: fieldDef.type,
//                 ...(fieldDef.relation  ? { relation:  fieldDef.relation  } : {}),
//                 ...(fieldDef.selection ? { selection: fieldDef.selection } : {}),
//                 ...(fieldName          ? { name:      fieldName           } : {}),
//             };
//         }
//         // Fallback: guess type from the JS value
//         return {
//             type: this._guessFieldType(value),
//             ...(fieldName ? { name: fieldName } : {}),
//         };
//     }
//
//     _guessFieldType(value) {
//         if (typeof value === 'boolean') return 'boolean';
//         if (typeof value === 'number')  return 'float';
//         return 'char';
//     }
//
//     _normalizeConditionOperator(operator) {
//         if (!operator) return '=';
//         if (operator === '==') return '=';
//         return operator;
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Selection / variable builders
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _currentRecordRef() {
//         return { value: CURRENT_RECORD_VAR_ID, label: CURRENT_RECORD_VAR_NAME };
//     }
//
//     _buildVariableSelection(variableId, variableName) {
//         return {
//             selectionType: 'variable',
//             value: {
//                 selectedVariable: variableId,
//                 pathValue: variableName,
//                 isVariable: true,
//             },
//         };
//     }
//
//     _buildStaticSelection(value) {
//         return { selectionType: 'static', value };
//     }
//
//     _computePathValue(path, fieldType) {
//         if (!path) return '';
//         if (fieldType === 'many2one') return `${path}.id`;
//         if (fieldType === 'many2many' || fieldType === 'one2many') return `${path}.ids`;
//         return path;
//     }
//
//     _buildCurrentRecordPath(sourceModel, path, fieldType = 'char', relation = null) {
//         return {
//             selectionType: 'record',
//             value: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path,
//                 pathValue: this._computePathValue(path, fieldType),
//                 info: {
//                     fieldDef: {
//                         type: fieldType,
//                         ...(relation ? { relation } : {}),
//                     },
//                     resModel: sourceModel,
//                 },
//             },
//         };
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Recipient / assignee / deadline resolvers
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _normalizeText(value) {
//         return String(value || '').toLowerCase();
//     }
//
//     _hasAnyToken(text, tokens) {
//         return tokens.some((token) => text.includes(token));
//     }
//
//     _resolveMailRecipientSelection(queryText, act, modelName, fieldDefs) {
//         const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);
//
//         if (this._hasAnyToken(hintText, ['notify me', 'send me', 'mail me', 'email me', 'current user'])) {
//             return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//         }
//
//         const partnerField  = this._findFieldByCandidates(fieldDefs,
//             ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
//             ['res.partner']);
//         const userField     = this._findFieldByCandidates(fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']);
//         const employeeField = this._findFieldByCandidates(fieldDefs,
//             ['employee_id', 'user_employee_id'],
//             ['hr.employee']);
//
//         if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user']) && userField) {
//             return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//
//         // Auto-fallback: prefer partner, then user, then current user
//         if (partnerField)  return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         if (userField)     return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
//         if (employeeField) return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveSmsRecipientSelection(queryText, act, modelName, fieldDefs) {
//         const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);
//
//         if (this._hasAnyToken(hintText, ['notify me', 'send me', 'text me', 'sms me', 'current user'])) {
//             return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//         }
//
//         const partnerField  = this._findFieldByCandidates(fieldDefs,
//             ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
//             ['res.partner']);
//         const userField     = this._findFieldByCandidates(fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']);
//         const employeeField = this._findFieldByCandidates(fieldDefs,
//             ['employee_id', 'user_employee_id'],
//             ['hr.employee']);
//
//         if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user']) && userField) {
//             return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         }
//         if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//
//         if (partnerField)  return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         if (userField)     return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         if (employeeField) return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveActivityAssigneeSelection(queryText, act, modelName, fieldDefs) {
//         const hintText  = this._normalizeText(`${queryText} ${act?.assignee_role || ''}`);
//         const userField = this._findFieldByCandidates(fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']);
//
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user'])
//             && userField) {
//             return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         }
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveActivityDeadlineSelection(queryText, act) {
//         const explicitDate = String(act?.deadline || '').trim();
//         if (/^\d{4}-\d{2}-\d{2}$/.test(explicitDate)) {
//             return this._buildStaticSelection(explicitDate);
//         }
//         // Always default to current_date variable so nodes open without errors
//         return this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME);
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Node data builders (one per action type)
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _buildWarningNodeData(act) {
//         return {
//             label:        act.label   || "Warning",
//             warning_type: "error",
//             warning:      "UserError",
//             warning_text: act.message || "An error has occurred.",
//         };
//     }
//
//     _buildMailNodeData(act, context = {}) {
//         const subject = act.subject || act.summary || "Notification";
//         const body    = act.body    || act.message  || "";
//         return {
//             label:           act.label || "Send Mail",
//             mail_isTemplate: false,
//             mail_record:     this._currentRecordRef(),
//             mail_subject:    this._buildStaticSelection(subject),
//             mail_body:       body,
//             mail_to:         [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
//         };
//     }
//
//     _buildSmsNodeData(act, context = {}) {
//         const message = act.message || act.body || "";
//         return {
//             label:           act.label || "Send SMS",
//             sms_isTemplate:  false,
//             sms_record:      this._currentRecordRef(),
//             sms_message:     message,
//             sms_partner_ids: [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
//         };
//     }
//
//     _buildActivityNodeData(act, activityType, context = {}) {
//         const summary = act.summary || act.message || "Follow up";
//         return {
//             label:             act.label || "Activity",
//             activity_record:   this._currentRecordRef(),
//             activity_type:     activityType || null,
//             activity_summary:  summary,
//             activity_deadline: context.deadlineSelection  || this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME),
//             activity_user:     context.assigneeSelection  || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME),
//         };
//     }
//
//     _buildWriteNodeData(act) {
//         const treeItem = {
//             id:            Date.now(),
//             path:          act.field  || "",
//             value:         act.value  !== undefined ? act.value : "",
//             type:          this._guessFieldType(act.value),
//             selectionType: 'static',
//         };
//         return {
//             label:                 act.label || "Write Record",
//             write_selected_record: this._currentRecordRef(),
//             write_field_value:     JSON.stringify([treeItem]),
//         };
//     }
//
//     _buildActionNodeData(act, activityType, context = {}) {
//         switch (act.type) {
//             case 'Warning':  return this._buildWarningNodeData(act);
//             case 'Mail':     return this._buildMailNodeData(act, context);
//             case 'SMS':      return this._buildSmsNodeData(act, context);
//             case 'Activity': return this._buildActivityNodeData(act, activityType, context);
//             case 'Write':    return this._buildWriteNodeData(act);
//             default:         return act.label ? { label: act.label } : null;
//         }
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Main send handler
//     // ─────────────────────────────────────────────────────────────────────────
//
//     async sendAiMessage() {
//         const userQuery = (this.state.aiInput || '').trim();
//         if (!userQuery) return;
//
//         const userId = this.state.aiMessages.length;
//         this.state.aiMessages.push({ from: 'user', text: userQuery, id: userId });
//         this.state.aiInput = "";
//
//         const aiResponseId = userId + 1;
//         let aiData;
//
//         // ── Step 1: Call AI backend ────────────────────────────────────────
//         try {
//             const result = await this.orm.call('chat.bot', 'my_python_method', [userQuery]);
//             aiData = typeof result === 'string' ? JSON.parse(result) : result;
//         } catch (e) {
//             console.error('AI call failed:', e);
//             const rpcMessage = e?.data?.message || e?.message || 'Unknown RPC error.';
//             this._pushAiMessage(`AI call failed: ${rpcMessage}`, { id: aiResponseId, type: 'error' });
//             return;
//         }
//
//         // ── Step 2: Validate AI response ───────────────────────────────────
//         if (aiData?.error) {
//             const errorText = [aiData.error, aiData.details, aiData.raw].filter(Boolean).join(' | ');
//             this._pushAiMessage(errorText, { id: aiResponseId, type: 'error' });
//             return;
//         }
//
//         if (!aiData?.object) {
//             this._pushAiMessage(
//                 'No model was returned by the AI. Please rephrase your query.',
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!aiData?.trigger) {
//             this._pushAiMessage(
//                 'No trigger was returned by the AI. Please rephrase your query.',
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!aiData?.actions?.length) {
//             this._pushAiMessage(
//                 'No actions were returned by the AI. Please rephrase your query.',
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         // ── Step 3: Resolve Odoo model ─────────────────────────────────────
//         const modelName = aiData.object.trim();
//         let res;
//         try {
//             res = await this.orm.searchRead(
//                 'ir.model',
//                 [['model', '=', modelName]],
//                 ['id', 'display_name', 'model']
//             );
//             // Fallback: ilike search if exact match fails
//             if (!res?.length) {
//                 res = await this.orm.searchRead(
//                     'ir.model',
//                     [['model', 'ilike', modelName]],
//                     ['id', 'display_name', 'model']
//                 );
//             }
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to search for model "${modelName}": ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!res?.length) {
//             this._pushAiMessage(
//                 `Model "${modelName}" was not found. Please install the required module and try again.`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         const modelId           = res[0].id;
//         const modelTechnicalName = res[0].model;
//         const modelDisplayName  = res[0].display_name;
//
//         // ── Step 4: Fetch field definitions (includes selection options) ────
//         const modelFieldDefs = await this._getModelFieldDefs(modelTechnicalName);
//
//         // ── Step 5: Pre-resolve activity type ─────────────────────────────
//         let defaultActivityType = null;
//         const hasActivity = (aiData.actions || []).some(a => a.type === 'Activity');
//         if (hasActivity) {
//             try {
//                 let actTypes = await this.orm.searchRead(
//                     'mail.activity.type',
//                     [['name', 'ilike', 'to-do']],
//                     ['id', 'name'],
//                     { limit: 1 }
//                 );
//                 if (!actTypes.length) {
//                     actTypes = await this.orm.searchRead(
//                         'mail.activity.type',
//                         [],
//                         ['id', 'name'],
//                         { limit: 1 }
//                     );
//                 }
//                 if (actTypes.length) {
//                     defaultActivityType = { id: actTypes[0].id, name: actTypes[0].name };
//                 }
//             } catch (e) {
//                 console.warn('Could not fetch mail.activity.type:', e);
//             }
//         }
//
//         // ── Step 6: Set up the primary model node ──────────────────────────
//         try {
//             await this.onSelectPrimary([{ id: modelId, display_name: modelDisplayName, model: modelTechnicalName }]);
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to set up model node: ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//         await new Promise(r => setTimeout(r, 150));
//
//         const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
//             .find(n => n.data.type === 'model');
//         const modelDfId = modelDfNode ? modelDfNode.id : null;
//
//         // ── Step 7: Resolve trigger work.function ──────────────────────────
//         const TRIGGER_FUNC_NAMES = {
//             'On Create': 'create',
//             'On Write':  'write',
//             'On Unlink': 'unlink',
//         };
//         const funcName = TRIGGER_FUNC_NAMES[aiData.trigger] || 'create';
//
//         let triggerFunctions;
//         try {
//             triggerFunctions = await this.orm.searchRead(
//                 'work.function',
//                 [['func_name', '=', funcName]],
//                 ['id', 'name', 'trigger_type']
//             );
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to search trigger functions: ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!triggerFunctions.length) {
//             this._pushAiMessage(
//                 `Trigger function "${funcName}" was not found in the database.`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         const triggerFn   = triggerFunctions[0];
//         const actionId    = String(triggerFn.id);
//         const triggerType = triggerFn.trigger_type;
//
//         // ── Step 8: Add trigger node ───────────────────────────────────────
//         this.state.nodeDetails = this.state.nodeDetails || [];
//         let triggerDfId;
//         try {
//             const result = await this._addNode(
//                 aiData.trigger, 538, 340,
//                 modelDisplayName, modelId, actionId, 'trigger', triggerType
//             );
//             triggerDfId = result.dfId;
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to add trigger node: ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//         await new Promise(r => setTimeout(r, 100));
//
//         // ── Step 9: Connect model → trigger ───────────────────────────────
//         if (modelDfId && triggerDfId) {
//             this._connectNodes(modelDfId, triggerDfId);
//         }
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── Step 10: Add Condition node (only when AI returned conditions) ─
//         let conditionDfId  = null;
//         let conditionNodeId = null;
//
//         if (aiData.conditions && aiData.conditions.length > 0) {
//             try {
//                 const { dfId: cDfId, nodeId: cNodeId } = await this._addNode(
//                     'Condition', 538, 480,
//                     modelDisplayName, modelId, null, null
//                 );
//                 conditionDfId  = cDfId;
//                 conditionNodeId = cNodeId;
//             } catch (e) {
//                 console.warn('Failed to add Condition node:', e);
//             }
//
//             if (triggerDfId && conditionDfId) {
//                 this._connectNodes(triggerDfId, conditionDfId);
//             }
//             await new Promise(r => setTimeout(r, 80));
//
//             if (conditionNodeId) {
//                 const conditionTreeValue = this._buildConditionTreeValue(
//                     aiData.conditions,
//                     modelTechnicalName,
//                     modelFieldDefs
//                 );
//                 if (conditionTreeValue) {
//                     try {
//                         await this.orm.write('node.struct', [conditionNodeId], {
//                             label: "Condition",
//                             condition_tree_value: conditionTreeValue,
//                         });
//                     } catch (e) {
//                         console.warn('Could not save condition_tree_value:', e);
//                     }
//                 }
//             }
//         }
//
//         // ── Step 11: Add action nodes ──────────────────────────────────────
//         const actionParentDfId = conditionDfId ?? triggerDfId;
//         const actions          = aiData.actions || [];
//
//         for (let i = 0; i < actions.length; i++) {
//             const act      = actions[i];
//             const nodeType = act?.type || 'Warning';
//
//             let actDfId, actNodeId;
//             try {
//                 const result = await this._addNode(
//                     nodeType,
//                     660 + (i * 260), 620,
//                     modelDisplayName, modelId, null, null
//                 );
//                 actDfId   = result.dfId;
//                 actNodeId = result.nodeId;
//             } catch (e) {
//                 console.warn(`Failed to add action node (${nodeType}):`, e);
//                 continue;
//             }
//             await new Promise(r => setTimeout(r, 80));
//
//             if (actNodeId) {
//                 const actionContext = {};
//                 if (nodeType === 'Mail') {
//                     actionContext.recipientSelection = this._resolveMailRecipientSelection(
//                         userQuery, act, modelTechnicalName, modelFieldDefs
//                     );
//                 } else if (nodeType === 'SMS') {
//                     actionContext.recipientSelection = this._resolveSmsRecipientSelection(
//                         userQuery, act, modelTechnicalName, modelFieldDefs
//                     );
//                 } else if (nodeType === 'Activity') {
//                     actionContext.assigneeSelection = this._resolveActivityAssigneeSelection(
//                         userQuery, act, modelTechnicalName, modelFieldDefs
//                     );
//                     actionContext.deadlineSelection = this._resolveActivityDeadlineSelection(
//                         userQuery, act
//                     );
//                 }
//
//                 const nodeData = this._buildActionNodeData(act, defaultActivityType, actionContext);
//                 if (nodeData) {
//                     try {
//                         await this.orm.write('node.struct', [actNodeId], nodeData);
//                     } catch (e) {
//                         console.warn(`Could not save config for ${nodeType} node:`, e);
//                     }
//                 }
//             }
//
//             if (actionParentDfId && actDfId) {
//                 this._connectNodes(actionParentDfId, actDfId, 'output_1');
//             }
//             await new Promise(r => setTimeout(r, 60));
//         }
//
//         // ── Step 12: Success message ───────────────────────────────────────
//         const condCount = aiData.conditions?.length ?? 0;
//         const actCount  = actions.length;
//         const summary =
//             `✓ Workflow built: ${aiData.trigger} on ${modelDisplayName}` +
//             (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
//             ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;
//
//         this._pushAiMessage(summary, { id: aiResponseId });
//     }
// }
//
// WorkFlowAutoOverride.template = "client_action.automation_view";
//
// registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });
//

// /** @odoo-module **/
// import { registry } from "@web/core/registry";
// import { useState } from "@odoo/owl";
// import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";
//
// // ─── Global variable IDs (must match what WorkFlowAuto seeds into env.globalVariables) ───
// const CURRENT_RECORD_VAR_ID   = "global/variable/current/rec";
// const CURRENT_RECORD_VAR_NAME = "current_record";
// const CURRENT_USER_VAR_ID     = "global/variable/current/user";
// const CURRENT_USER_VAR_NAME   = "current_user";
// const CURRENT_DATE_VAR_ID     = "global/variable/current/date";
// const CURRENT_DATE_VAR_NAME   = "current_date";
//
// class WorkFlowAutoOverride extends WorkFlowAuto {
//
//     setup() {
//         super.setup();
//         this._fieldCache = new Map();
//         this.state = useState({
//             nodeDetails: [],
//             actions: [],
//             aiChatOpen: false,
//             aiInput: "",
//             aiMessages: [],
//         });
//     }
//
//     settingModelState(data) {
//         if (!data) return;
//         this.state.modelState = data.modelState || [];
//     }
//
//     openAiChat() {
//         this.state.aiChatOpen = !this.state.aiChatOpen;
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // UI helpers
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _pushAiMessage(text, options = {}) {
//         const { id, type = 'info' } = options;
//         this.state.aiMessages.push({ from: 'ai', text, id, type });
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Canvas helpers
//     // ─────────────────────────────────────────────────────────────────────────
//
//     async _addNode(name, posX, posY, selectedValue, record, action, type, triggerType) {
//         const before = new Set(
//             Object.values(this.editor.drawflow.drawflow.Home.data).map(n => n.id)
//         );
//         await this.addNodeToDrawFlow(name, posX, posY, selectedValue, record, action, type, triggerType);
//         const dfData = this.editor.drawflow.drawflow.Home.data;
//         const newNode = Object.values(dfData).find(n => !before.has(n.id));
//         if (!newNode) return { dfId: null, nodeId: null };
//         return { dfId: newNode.id, nodeId: newNode.data.nodeId };
//     }
//
//     _connectNodes(outputDfId, inputDfId, outputClass = 'output_1', inputClass = 'input_1') {
//         if (!outputDfId || !inputDfId) return;
//         this.editor.addConnection(outputDfId, inputDfId, outputClass, inputClass);
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Field definitions cache
//     // ─────────────────────────────────────────────────────────────────────────
//
//     /**
//      * Fetches all field defs for a model including type, relation, string AND
//      * selection — so selection fields (state, payment_state, etc.) get their
//      * full option list and show correctly in the condition value dropdown.
//      */
//     async _getModelFieldDefs(modelName) {
//         if (!modelName) return {};
//         if (!this._fieldCache.has(modelName)) {
//             this._fieldCache.set(
//                 modelName,
//                 this.orm.call(modelName, 'fields_get', [[], ['type', 'relation', 'string', 'selection']])
//                     .catch(() => ({}))
//             );
//         }
//         return await this._fieldCache.get(modelName);
//     }
//
//     _findFieldByCandidates(fieldDefs, candidates, allowedRelations = []) {
//         for (const candidate of candidates) {
//             const fieldDef = fieldDefs?.[candidate];
//             if (!fieldDef) continue;
//             if (!allowedRelations.length || allowedRelations.includes(fieldDef.relation || '')) {
//                 return { name: candidate, ...fieldDef };
//             }
//         }
//         return null;
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Condition tree builder
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _buildConditionTreeValue(aiConditions, modelName, fieldDefs = {}) {
//         if (!aiConditions || !aiConditions.length) return null;
//
//         const conditions = aiConditions.map((cond) => ({
//             type: 'simple',
//             fieldType: 'record',
//             field: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path: cond.field,
//                 info: {
//                     fieldDef: this._getConditionFieldDef(modelName, cond.field, cond.value, fieldDefs),
//                     resModel: modelName,
//                 }
//             },
//             operator: this._normalizeConditionOperator(cond.operator),
//             value: {
//                 value: cond.value,
//                 fieldType: 'static',
//             },
//             logicalOperator: 'and',
//         }));
//
//         return [{ conditions, groupOperator: 'and' }];
//     }
//
//     _getConditionFieldDef(modelName, fieldName, value, fieldDefs = {}) {
//         const fieldDef = fieldDefs?.[fieldName];
//         if (fieldDef) {
//             return {
//                 type: fieldDef.type,
//                 ...(fieldDef.relation  ? { relation:  fieldDef.relation  } : {}),
//                 ...(fieldDef.selection ? { selection: fieldDef.selection } : {}),
//                 ...(fieldName          ? { name:      fieldName           } : {}),
//             };
//         }
//         // Fallback: guess type from the JS value
//         return {
//             type: this._guessFieldType(value),
//             ...(fieldName ? { name: fieldName } : {}),
//         };
//     }
//
//     _guessFieldType(value) {
//         if (typeof value === 'boolean') return 'boolean';
//         if (typeof value === 'number')  return 'float';
//         return 'char';
//     }
//
//     _normalizeConditionOperator(operator) {
//         if (!operator) return '=';
//         if (operator === '==') return '=';
//         return operator;
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Selection / variable builders
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _currentRecordRef() {
//         return { value: CURRENT_RECORD_VAR_ID, label: CURRENT_RECORD_VAR_NAME };
//     }
//
//     _buildVariableSelection(variableId, variableName) {
//         return {
//             selectionType: 'variable',
//             value: {
//                 selectedVariable: variableId,
//                 pathValue: variableName,
//                 isVariable: true,
//             },
//         };
//     }
//
//     _buildStaticSelection(value) {
//         return { selectionType: 'static', value };
//     }
//
//     _computePathValue(path, fieldType) {
//         if (!path) return '';
//         if (fieldType === 'many2one') return `${path}.id`;
//         if (fieldType === 'many2many' || fieldType === 'one2many') return `${path}.ids`;
//         return path;
//     }
//
//     _buildCurrentRecordPath(sourceModel, path, fieldType = 'char', relation = null) {
//         return {
//             selectionType: 'record',
//             value: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path,
//                 pathValue: this._computePathValue(path, fieldType),
//                 info: {
//                     fieldDef: {
//                         type: fieldType,
//                         ...(relation ? { relation } : {}),
//                     },
//                     resModel: sourceModel,
//                 },
//             },
//         };
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Recipient / assignee / deadline resolvers
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _normalizeText(value) {
//         return String(value || '').toLowerCase();
//     }
//
//     _hasAnyToken(text, tokens) {
//         return tokens.some((token) => text.includes(token));
//     }
//
//     _resolveMailRecipientSelection(queryText, act, modelName, fieldDefs) {
//         const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);
//
//         if (this._hasAnyToken(hintText, ['notify me', 'send me', 'mail me', 'email me', 'current user'])) {
//             return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//         }
//
//         const partnerField  = this._findFieldByCandidates(fieldDefs,
//             ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
//             ['res.partner']);
//         const userField     = this._findFieldByCandidates(fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']);
//         const employeeField = this._findFieldByCandidates(fieldDefs,
//             ['employee_id', 'user_employee_id'],
//             ['hr.employee']);
//
//         if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user']) && userField) {
//             return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//
//         // Auto-fallback: prefer partner, then user, then current user
//         if (partnerField)  return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         if (userField)     return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
//         if (employeeField) return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveSmsRecipientSelection(queryText, act, modelName, fieldDefs) {
//         const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);
//
//         if (this._hasAnyToken(hintText, ['notify me', 'send me', 'text me', 'sms me', 'current user'])) {
//             return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//         }
//
//         const partnerField  = this._findFieldByCandidates(fieldDefs,
//             ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
//             ['res.partner']);
//         const userField     = this._findFieldByCandidates(fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']);
//         const employeeField = this._findFieldByCandidates(fieldDefs,
//             ['employee_id', 'user_employee_id'],
//             ['hr.employee']);
//
//         if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user']) && userField) {
//             return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         }
//         if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//
//         if (partnerField)  return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         if (userField)     return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         if (employeeField) return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveActivityAssigneeSelection(queryText, act, modelName, fieldDefs) {
//         const hintText  = this._normalizeText(`${queryText} ${act?.assignee_role || ''}`);
//         const userField = this._findFieldByCandidates(fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']);
//
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'assigned_user', 'responsible', 'owner', 'user'])
//             && userField) {
//             return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         }
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveActivityDeadlineSelection(queryText, act) {
//         const explicitDate = String(act?.deadline || '').trim();
//         if (/^\d{4}-\d{2}-\d{2}$/.test(explicitDate)) {
//             return this._buildStaticSelection(explicitDate);
//         }
//         // Always default to current_date variable so nodes open without errors
//         return this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME);
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Node data builders (one per action type)
//     // ─────────────────────────────────────────────────────────────────────────
//
//     _buildWarningNodeData(act) {
//         return {
//             label:        act.label   || "Warning",
//             warning_type: "error",
//             warning:      "UserError",
//             warning_text: act.message || "An error has occurred.",
//         };
//     }
//
//     _buildMailNodeData(act, context = {}) {
//         const subject = act.subject || act.summary || "Notification";
//         const body    = act.body    || act.message  || "";
//         return {
//             label:           act.label || "Send Mail",
//             mail_isTemplate: false,
//             mail_record:     this._currentRecordRef(),
//             mail_subject:    this._buildStaticSelection(subject),
//             mail_body:       body,
//             mail_to:         [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
//         };
//     }
//
//     _buildSmsNodeData(act, context = {}) {
//         const message = act.message || act.body || "";
//         return {
//             label:           act.label || "Send SMS",
//             sms_isTemplate:  false,
//             sms_record:      this._currentRecordRef(),
//             sms_message:     message,
//             sms_partner_ids: [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
//         };
//     }
//
//     _buildActivityNodeData(act, activityType, context = {}) {
//         const summary = act.summary || act.message || "Follow up";
//         return {
//             label:             act.label || "Activity",
//             activity_record:   this._currentRecordRef(),
//             activity_type:     activityType || null,
//             activity_summary:  summary,
//             activity_deadline: context.deadlineSelection  || this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME),
//             activity_user:     context.assigneeSelection  || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME),
//         };
//     }
//
//     _buildWriteNodeData(act) {
//         const treeItem = {
//             id:            Date.now(),
//             path:          act.field  || "",
//             value:         act.value  !== undefined ? act.value : "",
//             type:          this._guessFieldType(act.value),
//             selectionType: 'static',
//         };
//         return {
//             label:                 act.label || "Write Record",
//             write_selected_record: this._currentRecordRef(),
//             write_field_value:     JSON.stringify([treeItem]),
//         };
//     }
//
//     _buildActionNodeData(act, activityType, context = {}) {
//         switch (act.type) {
//             case 'Warning':  return this._buildWarningNodeData(act);
//             case 'Mail':     return this._buildMailNodeData(act, context);
//             case 'SMS':      return this._buildSmsNodeData(act, context);
//             case 'Activity': return this._buildActivityNodeData(act, activityType, context);
//             case 'Write':    return this._buildWriteNodeData(act);
//             default:         return act.label ? { label: act.label } : null;
//         }
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Main send handler
//     // ─────────────────────────────────────────────────────────────────────────
//
//     async sendAiMessage() {
//         const userQuery = (this.state.aiInput || '').trim();
//         if (!userQuery) return;
//
//         const userId = this.state.aiMessages.length;
//         this.state.aiMessages.push({ from: 'user', text: userQuery, id: userId });
//         this.state.aiInput = "";
//
//         const aiResponseId = userId + 1;
//         let aiData;
//
//         // ── Step 1: Call AI backend ────────────────────────────────────────
//         try {
//             const result = await this.orm.call('chat.bot', 'my_python_method', [userQuery]);
//             aiData = typeof result === 'string' ? JSON.parse(result) : result;
//         } catch (e) {
//             console.error('AI call failed:', e);
//             const rpcMessage = e?.data?.message || e?.message || 'Unknown RPC error.';
//             this._pushAiMessage(`AI call failed: ${rpcMessage}`, { id: aiResponseId, type: 'error' });
//             return;
//         }
//
//         // ── Step 2: Validate AI response ───────────────────────────────────
//         if (aiData?.error) {
//             const errorText = [aiData.error, aiData.details, aiData.raw].filter(Boolean).join(' | ');
//             this._pushAiMessage(errorText, { id: aiResponseId, type: 'error' });
//             return;
//         }
//
//         if (!aiData?.object) {
//             this._pushAiMessage(
//                 'No model was returned by the AI. Please rephrase your query.',
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!aiData?.trigger) {
//             this._pushAiMessage(
//                 'No trigger was returned by the AI. Please rephrase your query.',
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!aiData?.actions?.length) {
//             this._pushAiMessage(
//                 'No actions were returned by the AI. Please rephrase your query.',
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         // ── Step 3: Resolve Odoo model ─────────────────────────────────────
//         const modelName = aiData.object.trim();
//         let res;
//         try {
//             res = await this.orm.searchRead(
//                 'ir.model',
//                 [['model', '=', modelName]],
//                 ['id', 'display_name', 'model']
//             );
//             // Fallback: ilike search if exact match fails
//             if (!res?.length) {
//                 res = await this.orm.searchRead(
//                     'ir.model',
//                     [['model', 'ilike', modelName]],
//                     ['id', 'display_name', 'model']
//                 );
//             }
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to search for model "${modelName}": ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!res?.length) {
//             this._pushAiMessage(
//                 `Model "${modelName}" was not found. Please install the required module and try again.`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         const modelId           = res[0].id;
//         const modelTechnicalName = res[0].model;
//         const modelDisplayName  = res[0].display_name;
//
//         // ── Step 4: Fetch field definitions (includes selection options) ────
//         const modelFieldDefs = await this._getModelFieldDefs(modelTechnicalName);
//
//         // ── Step 5: Pre-resolve activity type ─────────────────────────────
//         let defaultActivityType = null;
//         const hasActivity = (aiData.actions || []).some(a => a.type === 'Activity');
//         if (hasActivity) {
//             try {
//                 let actTypes = await this.orm.searchRead(
//                     'mail.activity.type',
//                     [['name', 'ilike', 'to-do']],
//                     ['id', 'name'],
//                     { limit: 1 }
//                 );
//                 if (!actTypes.length) {
//                     actTypes = await this.orm.searchRead(
//                         'mail.activity.type',
//                         [],
//                         ['id', 'name'],
//                         { limit: 1 }
//                     );
//                 }
//                 if (actTypes.length) {
//                     defaultActivityType = { id: actTypes[0].id, name: actTypes[0].name };
//                 }
//             } catch (e) {
//                 console.warn('Could not fetch mail.activity.type:', e);
//             }
//         }
//
//         // ── Step 6: Set up the primary model node ──────────────────────────
//         try {
//             await this.onSelectPrimary([{ id: modelId, display_name: modelDisplayName, model: modelTechnicalName }]);
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to set up model node: ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//         await new Promise(r => setTimeout(r, 150));
//
//         const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
//             .find(n => n.data.type === 'model');
//         const modelDfId = modelDfNode ? modelDfNode.id : null;
//
//         // ── Step 7: Resolve trigger work.function ──────────────────────────
//         const TRIGGER_FUNC_NAMES = {
//             'On Create': 'create',
//             'On Write':  'write',
//             'On Unlink': 'unlink',
//         };
//         const funcName = TRIGGER_FUNC_NAMES[aiData.trigger] || 'create';
//
//         let triggerFunctions;
//         try {
//             triggerFunctions = await this.orm.searchRead(
//                 'work.function',
//                 [['func_name', '=', funcName]],
//                 ['id', 'name', 'trigger_type']
//             );
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to search trigger functions: ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         if (!triggerFunctions.length) {
//             this._pushAiMessage(
//                 `Trigger function "${funcName}" was not found in the database.`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         const triggerFn   = triggerFunctions[0];
//         const actionId    = String(triggerFn.id);
//         const triggerType = triggerFn.trigger_type;
//
//         // ── Step 8: Add trigger node ───────────────────────────────────────
//         this.state.nodeDetails = this.state.nodeDetails || [];
//         let triggerDfId;
//         try {
//             const result = await this._addNode(
//                 aiData.trigger, 538, 340,
//                 modelDisplayName, modelId, actionId, 'trigger', triggerType
//             );
//             triggerDfId = result.dfId;
//         } catch (e) {
//             this._pushAiMessage(
//                 `Failed to add trigger node: ${e?.message || e}`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//         await new Promise(r => setTimeout(r, 100));
//
//         // ── Step 9: Connect model → trigger ───────────────────────────────
//         if (modelDfId && triggerDfId) {
//             this._connectNodes(modelDfId, triggerDfId);
//         }
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── Step 10: Add Condition node (only when AI returned conditions) ─
//         let conditionDfId  = null;
//         let conditionNodeId = null;
//
//         if (aiData.conditions && aiData.conditions.length > 0) {
//             try {
//                 const { dfId: cDfId, nodeId: cNodeId } = await this._addNode(
//                     'Condition', 538, 480,
//                     modelDisplayName, modelId, null, null
//                 );
//                 conditionDfId  = cDfId;
//                 conditionNodeId = cNodeId;
//             } catch (e) {
//                 console.warn('Failed to add Condition node:', e);
//             }
//
//             if (triggerDfId && conditionDfId) {
//                 this._connectNodes(triggerDfId, conditionDfId);
//             }
//             await new Promise(r => setTimeout(r, 80));
//
//             if (conditionNodeId) {
//                 const conditionTreeValue = this._buildConditionTreeValue(
//                     aiData.conditions,
//                     modelTechnicalName,
//                     modelFieldDefs
//                 );
//                 if (conditionTreeValue) {
//                     try {
//                         await this.orm.write('node.struct', [conditionNodeId], {
//                             label: "Condition",
//                             condition_tree_value: conditionTreeValue,
//                         });
//                     } catch (e) {
//                         console.warn('Could not save condition_tree_value:', e);
//                     }
//                 }
//             }
//         }
//
//         // ── Step 11: Add action nodes ──────────────────────────────────────
//         const actionParentDfId = conditionDfId ?? triggerDfId;
//         const actions          = aiData.actions || [];
//
//         for (let i = 0; i < actions.length; i++) {
//             const act      = actions[i];
//             const nodeType = act?.type || 'Warning';
//
//             let actDfId, actNodeId;
//             try {
//                 const result = await this._addNode(
//                     nodeType,
//                     660 + (i * 260), 620,
//                     modelDisplayName, modelId, null, null
//                 );
//                 actDfId   = result.dfId;
//                 actNodeId = result.nodeId;
//             } catch (e) {
//                 console.warn(`Failed to add action node (${nodeType}):`, e);
//                 continue;
//             }
//             await new Promise(r => setTimeout(r, 80));
//
//             if (actNodeId) {
//                 const actionContext = {};
//                 if (nodeType === 'Mail') {
//                     actionContext.recipientSelection = this._resolveMailRecipientSelection(
//                         userQuery, act, modelTechnicalName, modelFieldDefs
//                     );
//                 } else if (nodeType === 'SMS') {
//                     actionContext.recipientSelection = this._resolveSmsRecipientSelection(
//                         userQuery, act, modelTechnicalName, modelFieldDefs
//                     );
//                 } else if (nodeType === 'Activity') {
//                     actionContext.assigneeSelection = this._resolveActivityAssigneeSelection(
//                         userQuery, act, modelTechnicalName, modelFieldDefs
//                     );
//                     actionContext.deadlineSelection = this._resolveActivityDeadlineSelection(
//                         userQuery, act
//                     );
//                 }
//
//                 const nodeData = this._buildActionNodeData(act, defaultActivityType, actionContext);
//                 if (nodeData) {
//                     try {
//                         await this.orm.write('node.struct', [actNodeId], nodeData);
//                     } catch (e) {
//                         console.warn(`Could not save config for ${nodeType} node:`, e);
//                     }
//                 }
//             }
//
//             if (actionParentDfId && actDfId) {
//                 this._connectNodes(actionParentDfId, actDfId, 'output_1');
//             }
//             await new Promise(r => setTimeout(r, 60));
//         }
//
//         // ── Step 12: Success message ───────────────────────────────────────
//         const condCount = aiData.conditions?.length ?? 0;
//         const actCount  = actions.length;
//         const summary =
//             `✓ Workflow built: ${aiData.trigger} on ${modelDisplayName}` +
//             (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
//             ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;
//
//         this._pushAiMessage(summary, { id: aiResponseId });
//     }
// }
//
// WorkFlowAutoOverride.template = "client_action.automation_view";
//
// registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });


// /** @odoo-module **/
// import { registry } from "@web/core/registry";
// import { useState } from "@odoo/owl";
// import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";
//
// // The ID used by the global `current_record` variable that WorkFlowAuto seeds
// // into env.globalVariables on startup.  Every record-selector field in Mail,
// // SMS, Activity and Write nodes uses this ID as its `value` key when the user
// // picks "current_record" from the dropdown.
// const CURRENT_RECORD_VAR_ID    = "global/variable/current/rec";
// const CURRENT_RECORD_VAR_NAME  = "current_record";
// const CURRENT_USER_VAR_ID      = "global/variable/current/user";
// const CURRENT_USER_VAR_NAME    = "current_user";
// const CURRENT_DATE_VAR_ID      = "global/variable/current/date";
// const CURRENT_DATE_VAR_NAME    = "current_date";
//
// class WorkFlowAutoOverride extends WorkFlowAuto {
//
//     setup() {
//         super.setup();
//         this._fieldCache = new Map();
//         this.state = useState({
//             // Base arrays expected by WorkFlowAuto
//             nodeDetails: [],
//             actions: [],
//
//             // AI Chat state
//             aiChatOpen: false,
//             aiInput: "",
//             aiMessages: [],
//         });
//     }
//
//     settingModelState(data) {
//         if (!data) return;
//         this.state.modelState = data.modelState || [];
//     }
//
//     openAiChat() {
//         this.state.aiChatOpen = !this.state.aiChatOpen;
//     }
//
//     _pushAiMessage(text, options = {}) {
//         const { id, type = 'info' } = options;
//         this.state.aiMessages.push({
//             from: 'ai',
//             text,
//             id,
//             type,
//         });
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Canvas helpers
//     // ─────────────────────────────────────────────────────────────────────────
//
//     /**
//      * Adds a node and returns both the backend nodeId and the drawflow canvas ID.
//      * Snapshots existing IDs before the call, then diffs after to find the new node.
//      */
//     async _addNode(name, posX, posY, selectedValue, record, action, type, triggerType) {
//         const before = new Set(
//             Object.values(this.editor.drawflow.drawflow.Home.data).map(n => n.id)
//         );
//
//         await this.addNodeToDrawFlow(name, posX, posY, selectedValue, record, action, type, triggerType);
//
//         const dfData = this.editor.drawflow.drawflow.Home.data;
//         const newNode = Object.values(dfData).find(n => !before.has(n.id));
//         if (!newNode) return { dfId: null, nodeId: null };
//
//         return { dfId: newNode.id, nodeId: newNode.data.nodeId };
//     }
//
//     /**
//      * Connects two drawflow nodes.
//      * outputClass defaults to 'output_1' (standard single-output port).
//      */
//     _connectNodes(outputDfId, inputDfId, outputClass = 'output_1', inputClass = 'input_1') {
//         if (!outputDfId || !inputDfId) return;
//         this.editor.addConnection(outputDfId, inputDfId, outputClass, inputClass);
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Condition tree builder
//     // ─────────────────────────────────────────────────────────────────────────
//
//     /**
//      * Converts the AI conditions array into the condition_tree_value structure
//      * that conditionNode reads on open.
//      *
//      * AI format:  [{ field: 'discount', operator: '>', value: 50 }]
//      *
//      * conditionNode uses fieldType:'record' with the global current_record variable
//      * so that code generation can resolve `current_record.<field>` correctly.
//      */
//     _buildConditionTreeValue(aiConditions, modelName, fieldDefs = {}) {
//         if (!aiConditions || !aiConditions.length) return null;
//
//         const conditions = aiConditions.map((cond) => ({
//             type: 'simple',
//             fieldType: 'record',
//             field: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path: cond.field,
//                 info: {
//                     fieldDef: this._getConditionFieldDef(modelName, cond.field, cond.value, fieldDefs),
//                     resModel: modelName,
//                 }
//             },
//             operator: this._normalizeConditionOperator(cond.operator),
//             value: {
//                 value: cond.value,
//                 fieldType: 'static',
//             },
//             logicalOperator: 'and',
//         }));
//
//         return [{ conditions, groupOperator: 'and' }];
//     }
//
//     /** Infer a conditionNode-compatible field type from the raw JS value. */
//     _guessFieldType(value) {
//         if (typeof value === 'boolean') return 'boolean';
//         if (typeof value === 'number') return 'float';
//         return 'char';
//     }
//
//     _getConditionFieldDef(modelName, fieldName, value, fieldDefs = {}) {
//         const fieldDef = fieldDefs?.[fieldName];
//         if (fieldDef) {
//             return {
//                 type: fieldDef.type,
//                 ...(fieldDef.relation ? { relation: fieldDef.relation } : {}),
//                 ...(fieldDef.selection ? { selection: fieldDef.selection } : {}),
//                 ...(fieldName ? { name: fieldName } : {}),
//             };
//         }
//         return {
//             type: this._guessFieldType(value),
//             ...(fieldName ? { name: fieldName } : {}),
//         };
//     }
//
//     _normalizeConditionOperator(operator) {
//         return operator === '==' ? '=' : (operator || '=');
//     }
//
//     _normalizeText(value) {
//         return String(value || '').toLowerCase();
//     }
//
//     _hasAnyToken(text, tokens) {
//         return tokens.some((token) => text.includes(token));
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Shared record-variable stub
//     // ─────────────────────────────────────────────────────────────────────────
//
//     /**
//      * Returns the {value, label} object that all record-selector fields
//      * (mail_record, sms_record, activity_record, write_selected_record) store
//      * when the user picks the global "current_record" variable.
//      *
//      * The shape is produced by each node's getRecords getter:
//      *   variables.push({ value: variable.id, label: variable.variable_name })
//      */
//     _currentRecordRef() {
//         return { value: CURRENT_RECORD_VAR_ID, label: CURRENT_RECORD_VAR_NAME };
//     }
//
//     _buildVariableSelection(variableId, variableName) {
//         return {
//             selectionType: 'variable',
//             value: {
//                 selectedVariable: variableId,
//                 pathValue: variableName,
//                 isVariable: true,
//             },
//         };
//     }
//
//     _buildStaticSelection(value) {
//         return {
//             selectionType: 'static',
//             value,
//         };
//     }
//
//     _computePathValue(path, fieldType) {
//         if (!path) return '';
//         if (fieldType === 'many2one') {
//             return `${path}.id`;
//         }
//         if (fieldType === 'many2many' || fieldType === 'one2many') {
//             return `${path}.ids`;
//         }
//         return path;
//     }
//
//     _buildCurrentRecordPath(sourceModel, path, fieldType = 'char', relation = null) {
//         return {
//             selectionType: 'record',
//             value: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path,
//                 pathValue: this._computePathValue(path, fieldType),
//                 info: {
//                     fieldDef: {
//                         type: fieldType,
//                         ...(relation ? { relation } : {}),
//                     },
//                     resModel: sourceModel,
//                 },
//             },
//         };
//     }
//
//     async _getModelFieldDefs(modelName) {
//         if (!modelName) return {};
//         if (!this._fieldCache.has(modelName)) {
//             this._fieldCache.set(
//                 modelName,
//                 this.orm.call(modelName, 'fields_get', [[], ['type', 'relation', 'string', 'selection']])
//                     .catch(() => ({}))
//             );
//         }
//         return await this._fieldCache.get(modelName);
//     }
//
//     _findFieldByCandidates(fieldDefs, candidates, allowedRelations = []) {
//         for (const candidate of candidates) {
//             const fieldDef = fieldDefs?.[candidate];
//             if (!fieldDef) continue;
//             if (!allowedRelations.length || allowedRelations.includes(fieldDef.relation || '')) {
//                 return { name: candidate, ...fieldDef };
//             }
//         }
//         return null;
//     }
//
//     _resolveMailRecipientSelection(queryText, act, modelName, fieldDefs) {
//         const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);
//         if (this._hasAnyToken(hintText, ['notify me', 'send me', 'mail me', 'email me', 'current user'])) {
//             return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//         }
//
//         const partnerField = this._findFieldByCandidates(
//             fieldDefs,
//             ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
//             ['res.partner']
//         );
//         const userField = this._findFieldByCandidates(
//             fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']
//         );
//         const employeeField = this._findFieldByCandidates(
//             fieldDefs,
//             ['employee_id', 'user_employee_id'],
//             ['hr.employee']
//         );
//
//         if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'responsible', 'owner', 'user']) && userField) {
//             return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//
//         if (partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//         if (userField) {
//             return this._buildCurrentRecordPath(modelName, `${userField.name}.partner_id`, 'many2one', 'res.partner');
//         }
//         if (employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveSmsRecipientSelection(queryText, act, modelName, fieldDefs) {
//         const hintText = this._normalizeText(`${queryText} ${act?.recipient_role || ''}`);
//         if (this._hasAnyToken(hintText, ['notify me', 'send me', 'text me', 'sms me', 'current user'])) {
//             return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//         }
//
//         const partnerField = this._findFieldByCandidates(
//             fieldDefs,
//             ['partner_id', 'commercial_partner_id', 'contact_id', 'customer_id', 'vendor_id', 'supplier_id'],
//             ['res.partner']
//         );
//         const userField = this._findFieldByCandidates(
//             fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']
//         );
//         const employeeField = this._findFieldByCandidates(
//             fieldDefs,
//             ['employee_id', 'user_employee_id'],
//             ['hr.employee']
//         );
//
//         if (this._hasAnyToken(hintText, ['employee', 'staff']) && employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         if (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'responsible', 'owner', 'user']) && userField) {
//             return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         }
//         if (this._hasAnyToken(hintText, ['customer', 'client', 'partner', 'vendor', 'supplier', 'contact']) && partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//
//         if (partnerField) {
//             return this._buildCurrentRecordPath(modelName, partnerField.name, 'many2one', 'res.partner');
//         }
//         if (userField) {
//             return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         }
//         if (employeeField) {
//             return this._buildCurrentRecordPath(modelName, `${employeeField.name}.work_contact_id`, 'many2one', 'res.partner');
//         }
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveActivityAssigneeSelection(queryText, act, modelName, fieldDefs) {
//         const hintText = this._normalizeText(`${queryText} ${act?.assignee_role || ''}`);
//         const userField = this._findFieldByCandidates(
//             fieldDefs,
//             ['user_id', 'assigned_user_id', 'responsible_id', 'manager_id', 'salesperson_id', 'owner_id'],
//             ['res.users']
//         );
//
//         if (
//             (this._hasAnyToken(hintText, ['manager', 'salesperson', 'assigned user', 'responsible', 'owner', 'user'])
//                 || act?.assignee_role === 'assigned_user')
//             && userField
//         ) {
//             return this._buildCurrentRecordPath(modelName, userField.name, 'many2one', 'res.users');
//         }
//
//         return this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME);
//     }
//
//     _resolveActivityDeadlineSelection(queryText, act) {
//         const explicitDate = String(act?.deadline || '').trim();
//         if (/^\d{4}-\d{2}-\d{2}$/.test(explicitDate)) {
//             return this._buildStaticSelection(explicitDate);
//         }
//
//         const hintText = this._normalizeText(queryText);
//         if (this._hasAnyToken(hintText, ['today', 'current date'])) {
//             return this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME);
//         }
//
//         return this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME);
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Node data builders  (one per action type)
//     // ─────────────────────────────────────────────────────────────────────────
//
//     /**
//      * Warning node — fields read by WarningNode.validateForm():
//      *   label          (required, non-empty string)
//      *   warning_type   'error' | 'notification'
//      *   warning        selection: UserError | ValidationError | AccessError |
//      *                             MissingError | AccessDenied | CacheMiss |
//      *                             RedirectWarning
//      *   warning_text   (required, non-empty string)
//      */
//     _buildWarningNodeData(act) {
//         return {
//             label:        act.label        || "Warning",
//             warning_type: "error",
//             warning:      "UserError",
//             warning_text: act.message      || "An error has occurred.",
//         };
//     }
//
//     /**
//      * Mail node — fields read by MailNode.validateForm():
//      *   label           (required)
//      *   mail_isTemplate false  → custom mail (we always pre-fill custom)
//      *   mail_record     { value: varId, label: varName }  — required for code-gen
//      *   mail_subject    { value: <string>, selectionType: 'static' }
//      *   mail_body       plain string  (node.struct field is Json but mailNode
//      *                   stores/reads it as a raw string via fieldState.mail_body)
//      *   mail_to         [{ value: [], selectionType: 'static' }]
//      *                   Kept as empty-static: partner IDs cannot be resolved
//      *                   from free-text at canvas-build time.  The user fills this
//      *                   in; every other field will already be populated.
//      *
//      * Note: mail_record is mandatory for generateCode() even when
//      * mail_isTemplate is false (the template branch reads it too).
//      */
//     _buildMailNodeData(act, context = {}) {
//         const subject = act.subject || act.summary || "Notification";
//         const body    = act.body    || act.message  || "";
//         return {
//             label:           act.label || "Send Mail",
//             mail_isTemplate: false,
//             mail_record:     this._currentRecordRef(),
//             mail_subject:    this._buildStaticSelection(subject),
//             mail_body:       body,
//             mail_to:         [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
//         };
//     }
//
//     /**
//      * SMS node — fields read by SmsNode.validateForm():
//      *   label            (required)
//      *   sms_isTemplate   false → custom SMS
//      *   sms_record       { value: varId, label: varName }
//      *   sms_message      plain string
//      *   sms_partner_ids  [{ value: [], selectionType: 'static' }]
//      *                    Same reasoning as mail_to — left empty for the user.
//      */
//     _buildSmsNodeData(act, context = {}) {
//         const message = act.message || act.body || "";
//         return {
//             label:          act.label || "Send SMS",
//             sms_isTemplate: false,
//             sms_record:     this._currentRecordRef(),
//             sms_message:    message,
//             sms_partner_ids: [context.recipientSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME)],
//         };
//     }
//
//     /**
//      * Activity node — fields read by ActivityNode.validateForm():
//      *   label             (required)
//      *   activity_record   { value: varId, label: varName }  (required)
//      *   activity_type     { id, name }  — resolved live from mail.activity.type
//      *                     We pre-fill with the first "To-Do" / generic type found.
//      *                     The lookup happens asynchronously in sendAiMessage so
//      *                     this builder receives the resolved object directly.
//      *   activity_summary  string  (required)
//      *   activity_deadline { value: false, selectionType: 'static' }
//      *                     Left empty — the user must pick a date/expression.
//      *   activity_user     { value: '', selectionType: 'static' }
//      *                     Left empty — the user must pick the assignee.
//      */
//     _buildActivityNodeData(act, activityType, context = {}) {
//         const summary = act.summary || act.message || "Follow up";
//         return {
//             label:             act.label || "Activity",
//             activity_record:   this._currentRecordRef(),
//             activity_type:     activityType || null,   // resolved by caller
//             activity_summary:  summary,
//             activity_deadline: context.deadlineSelection || this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME),
//             activity_user:     context.assigneeSelection || this._buildVariableSelection(CURRENT_USER_VAR_ID, CURRENT_USER_VAR_NAME),
//         };
//     }
//
//     /**
//      * Write node — fields read by WriteNode.validateForm():
//      *   label                (required — validated separately by the label bus event)
//      *   write_selected_record  { value: varId, label: varName }
//      *   write_field_value    JSON string: array of tree items
//      *                        [ { id, path, value, type, selectionType } ]
//      *
//      *   The AI provides { field, value } — we convert that into the minimal
//      *   tree-node shape that WriteNode.settingTreeData() / generateCode() expect.
//      *   selectionType defaults to 'static' so no variable lookup is needed.
//      */
//     _buildWriteNodeData(act) {
//         const treeItem = {
//             id:            Date.now(),
//             path:          act.field  || "",
//             value:         act.value  !== undefined ? act.value : "",
//             type:          this._guessFieldType(act.value),
//             selectionType: 'static',
//         };
//         return {
//             label:                act.label || "Write Record",
//             write_selected_record: this._currentRecordRef(),
//             write_field_value:    JSON.stringify([treeItem]),
//         };
//     }
//
//     /**
//      * Dispatcher — returns the node.struct payload for the given action type.
//      * activityType is only used for the Activity branch.
//      */
//     _buildActionNodeData(act, activityType, context = {}) {
//         switch (act.type) {
//             case 'Warning':  return this._buildWarningNodeData(act);
//             case 'Mail':     return this._buildMailNodeData(act, context);
//             case 'SMS':      return this._buildSmsNodeData(act, context);
//             case 'Activity': return this._buildActivityNodeData(act, activityType, context);
//             case 'Write':    return this._buildWriteNodeData(act);
//             default:         return act.label ? { label: act.label } : null;
//         }
//     }
//
//     // ─────────────────────────────────────────────────────────────────────────
//     // Main send handler
//     // ─────────────────────────────────────────────────────────────────────────
//
//     async sendAiMessage() {
//         if (!this.state.aiInput) return;
//
//         const userQuery = this.state.aiInput;
//         const userId = this.state.aiMessages.length;
//         this.state.aiMessages.push({ from: 'user', text: userQuery, id: userId });
//
//         const aiResponseId = userId + 1;
//         let aiData;
//
//         try {
//             const result = await this.orm.call('chat.bot', 'my_python_method', [userQuery]);
//             aiData = typeof result === 'string' ? JSON.parse(result) : result;
//         } catch (e) {
//             console.error('AI call failed:', e);
//             const rpcMessage = e?.data?.message || e?.message || 'Unknown RPC error.';
//             this._pushAiMessage(`AI call failed: ${rpcMessage}`, { id: aiResponseId, type: 'error' });
//             return;
//         }
//
//         if (aiData?.error) {
//             const errorText = [aiData.error, aiData.details, aiData.raw]
//                 .filter(Boolean)
//                 .join(' | ');
//             this._pushAiMessage(errorText, { id: aiResponseId, type: 'error' });
//             return;
//         }
//
//         if (!aiData?.object) {
//             this._pushAiMessage(
//                 'The model was not found in the AI response. Please install the required module and try again.',
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         // ── 1. Resolve Odoo model ──────────────────────────────────────────
//         const modelName = aiData.object.trim();
//         const res = await this.orm.searchRead(
//             'ir.model',
//             [['model', 'ilike', modelName]],
//             ['id', 'display_name', 'model']
//         );
//         if (!res?.length) {
//             this._pushAiMessage(
//                 `Model "${modelName}" was not found. Please install the required module and try again.`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//         const modelId = res[0].id;
//         const modelTechnicalName = res[0].model;
//         const modelFieldDefs = await this._getModelFieldDefs(modelTechnicalName);
//
//         // ── 2. Pre-resolve activity type (needed before nodes are built) ───
//         // We look up the default "To-Do" (or first available) mail.activity.type
//         // so Activity nodes can be fully pre-configured without further async
//         // work inside _buildActivityNodeData.
//         let defaultActivityType = null;
//         const hasActivity = (aiData.actions || []).some(a => a.type === 'Activity');
//         if (hasActivity) {
//             try {
//                 // Prefer "To-Do" (email) activity type as the generic default.
//                 let actTypes = await this.orm.searchRead(
//                     'mail.activity.type',
//                     [['name', 'ilike', 'to-do']],
//                     ['id', 'name'],
//                     { limit: 1 }
//                 );
//                 if (!actTypes.length) {
//                     // Fall back to the very first activity type available.
//                     actTypes = await this.orm.searchRead(
//                         'mail.activity.type',
//                         [],
//                         ['id', 'name'],
//                         { limit: 1 }
//                     );
//                 }
//                 if (actTypes.length) {
//                     defaultActivityType = { id: actTypes[0].id, name: actTypes[0].name };
//                 }
//             } catch (e) {
//                 console.warn('Could not fetch mail.activity.type:', e);
//             }
//         }
//
//         // ── 3. Set up the primary model node ──────────────────────────────
//         await this.onSelectPrimary([{ id: modelId, display_name: res[0].display_name, model: res[0].model }]);
//         await new Promise(r => setTimeout(r, 120));
//
//         const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
//             .find(n => n.data.type === 'model');
//         const modelDfId = modelDfNode ? modelDfNode.id : null;
//
//         // ── 4. Resolve trigger work.function record ────────────────────────
//         const TRIGGER_FUNC_NAMES = {
//             'On Create': 'create',
//             'On Write':  'write',
//             'On Unlink': 'unlink',
//         };
//         const funcName = TRIGGER_FUNC_NAMES[aiData.trigger] || 'create';
//
//         const triggerFunctions = await this.orm.searchRead(
//             'work.function',
//             [['func_name', '=', funcName]],
//             ['id', 'name', 'trigger_type']
//         );
//         if (!triggerFunctions.length) {
//             this._pushAiMessage(
//                 `Trigger function "${funcName}" was not found in the database.`,
//                 { id: aiResponseId, type: 'error' }
//             );
//             return;
//         }
//
//         const triggerFn   = triggerFunctions[0];
//         const actionId    = String(triggerFn.id);
//         const triggerType = triggerFn.trigger_type;
//
//         // ── 5. Add trigger node ────────────────────────────────────────────
//         this.state.nodeDetails = this.state.nodeDetails || [];
//         const { dfId: triggerDfId } = await this._addNode(
//             aiData.trigger,
//             538, 340,
//             res[0].display_name,
//             modelId,
//             actionId,
//             'trigger',
//             triggerType
//         );
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── 6. Connect model → trigger ─────────────────────────────────────
//         if (modelDfId && triggerDfId) {
//             this._connectNodes(modelDfId, triggerDfId);
//         }
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── 7. Add Condition node (only when AI returned conditions) ───────
//         let conditionDfId   = null;
//         let conditionNodeId = null;
//
//         if (aiData.conditions && aiData.conditions.length > 0) {
//             const { dfId: cDfId, nodeId: cNodeId } = await this._addNode(
//                 'Condition',
//                 538, 480,
//                 res[0].display_name,
//                 modelId,
//                 null,
//                 null
//             );
//             conditionDfId   = cDfId;
//             conditionNodeId = cNodeId;
//
//             if (triggerDfId && conditionDfId) {
//                 this._connectNodes(triggerDfId, conditionDfId);
//             }
//             await new Promise(r => setTimeout(r, 80));
//
//             if (conditionNodeId) {
//                 const conditionTreeValue = this._buildConditionTreeValue(
//                     aiData.conditions,
//                     modelTechnicalName,
//                     modelFieldDefs
//                 );
//                 if (conditionTreeValue) {
//                     try {
//                         await this.orm.write('node.struct', [conditionNodeId], {
//                             label: "Condition",
//                             condition_tree_value: conditionTreeValue,
//                         });
//                     } catch (e) {
//                         console.warn('Could not save condition_tree_value:', e);
//                     }
//                 }
//             }
//         }
//
//         // ── 8. Add action nodes ────────────────────────────────────────────
//         // Every action connects from:
//         //   • output_1 of the Condition node (true branch) — when conditions exist
//         //   • output_1 of the trigger node                 — when no conditions
//         //
//         // Actions are placed side by side (parallel fan-out).
//         const actionParentDfId  = conditionDfId ?? triggerDfId;
//         const actionOutputClass = 'output_1';
//
//         const actions = aiData.actions || [];
//         for (let i = 0; i < actions.length; i++) {
//             const act      = actions[i];
//             const nodeType = act?.type || 'Warning';
//
//             const { dfId: actDfId, nodeId: actNodeId } = await this._addNode(
//                 nodeType,
//                 660 + (i * 240), 620,
//                 res[0].display_name,
//                 modelId,
//                 null,
//                 null
//             );
//             await new Promise(r => setTimeout(r, 80));
//
//             // Write the fully pre-configured data to node.struct so that
//             // every configurable field is already populated when the user
//             // opens the node panel — no field will be blank or missing.
//             if (actNodeId) {
//                 const actionContext = {};
//                 if (nodeType === 'Mail') {
//                     actionContext.recipientSelection = this._resolveMailRecipientSelection(
//                         userQuery,
//                         act,
//                         modelTechnicalName,
//                         modelFieldDefs
//                     );
//                 } else if (nodeType === 'SMS') {
//                     actionContext.recipientSelection = this._resolveSmsRecipientSelection(
//                         userQuery,
//                         act,
//                         modelTechnicalName,
//                         modelFieldDefs
//                     );
//                 } else if (nodeType === 'Activity') {
//                     actionContext.assigneeSelection = this._resolveActivityAssigneeSelection(
//                         userQuery,
//                         act,
//                         modelTechnicalName,
//                         modelFieldDefs
//                     );
//                     actionContext.deadlineSelection = this._resolveActivityDeadlineSelection(
//                         userQuery,
//                         act
//                     );
//                 }
//
//                 const nodeData = this._buildActionNodeData(act, defaultActivityType, actionContext);
//                 if (nodeData) {
//                     try {
//                         await this.orm.write('node.struct', [actNodeId], nodeData);
//                     } catch (e) {
//                         console.warn(`Could not save config for ${nodeType} node:`, e);
//                     }
//                 }
//             }
//
//             if (actionParentDfId && actDfId) {
//                 this._connectNodes(actionParentDfId, actDfId, actionOutputClass);
//             }
//             await new Promise(r => setTimeout(r, 60));
//         }
//
//         // ── 9. Confirm message ─────────────────────────────────────────────
//         const condCount = aiData.conditions?.length ?? 0;
//         const actCount  = actions.length;
//         const summary =
//             `✓ Workflow built: ${aiData.trigger} on ${res[0].display_name}` +
//             (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
//             ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;
//
//         this._pushAiMessage(summary, { id: aiResponseId });
//         this.state.aiInput = "";
//     }
// }
//
// WorkFlowAutoOverride.template = "client_action.automation_view";
//
// registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });
//







// /** @odoo-module **/
// import { registry } from "@web/core/registry";
// import { useState } from "@odoo/owl";
// import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";
//
// class WorkFlowAutoOverride extends WorkFlowAuto {
//
//     setup() {
//         super.setup();
//         this.state = useState({
//             // Base arrays expected by WorkFlowAuto
//             nodeDetails: [],
//             actions: [],
//
//             // AI Chat state
//             aiChatOpen: false,
//             aiInput: "",
//             aiMessages: [],
//         });
//     }
//
//     settingModelState(data) {
//         if (!data) return;
//         this.state.modelState = data.modelState || [];
//     }
//
//     openAiChat() {
//         this.state.aiChatOpen = !this.state.aiChatOpen;
//         console.log('AI Chat Open:', this.state.aiChatOpen);
//     }
//
//     /**
//      * Adds a node and returns both the backend nodeId and the drawflow canvas ID.
//      * Snapshots existing IDs before the call, then diffs after to find the new node.
//      */
//     async _addNode(name, posX, posY, selectedValue, record, action, type, triggerType) {
//         const before = new Set(
//             Object.values(this.editor.drawflow.drawflow.Home.data).map(n => n.id)
//         );
//
//         await this.addNodeToDrawFlow(name, posX, posY, selectedValue, record, action, type, triggerType);
//
//         // The newly added node is the one whose drawflow ID was not present before
//         const dfData = this.editor.drawflow.drawflow.Home.data;
//         const newNode = Object.values(dfData).find(n => !before.has(n.id));
//         if (!newNode) return { dfId: null, nodeId: null };
//
//         return { dfId: newNode.id, nodeId: newNode.data.nodeId };
//     }
//
//     /**
//      * Connects two drawflow nodes.
//      * outputClass defaults to 'output_1' (standard single-output port).
//      * For Condition nodes use 'output_1' for the TRUE branch.
//      */
//     _connectNodes(outputDfId, inputDfId, outputClass = 'output_1', inputClass = 'input_1') {
//         if (!outputDfId || !inputDfId) return;
//         this.editor.addConnection(outputDfId, inputDfId, outputClass, inputClass);
//     }
//
//     /**
//      * Converts the AI conditions array into the condition_tree_value structure
//      * that conditionNode reads on open.
//      *
//      * AI format:  [{ field: 'discount', operator: '>', value: 50 }]
//      *
//      * conditionNode uses fieldType:'record' with the global current_record variable
//      * so that code generation can resolve `current_record.<field>` correctly.
//      */
//     _buildConditionTreeValue(aiConditions) {
//         if (!aiConditions || !aiConditions.length) return null;
//
//         // 'current_record' is always registered as the global record variable
//         const CURRENT_RECORD_VAR_ID = "global/variable/current/rec";
//
//         const conditions = aiConditions.map((cond, index) => ({
//             type: 'simple',
//             fieldType: 'record',
//             field: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path: cond.field,
//                 info: {
//                     fieldDef: {
//                         // Guess the field type from the value so code-gen picks
//                         // the right comparison template (number → float branch).
//                         type: this._guessFieldType(cond.value),
//                     }
//                 }
//             },
//             operator: cond.operator,
//             value: {
//                 value: cond.value,
//                 fieldType: 'static',
//             },
//             logicalOperator: index === 0 ? 'and' : 'and',
//         }));
//
//         return [{ conditions, groupOperator: 'and' }];
//     }
//
//     /** Infer a conditionNode-compatible field type from the raw value. */
//     _guessFieldType(value) {
//         if (typeof value === 'boolean') return 'boolean';
//         if (typeof value === 'number') return 'float';
//         return 'char';
//     }
//
//     /**
//      * Builds the node.struct write payload for a Warning action node.
//      *
//      * Stores:
//      *   - label          : shown on the canvas card
//      *   - warning_type   : 'error' (raises a UserError — simplest/most common)
//      *   - warning        : 'UserError' (the exception class)
//      *   - warning_text   : the message from the AI, or a sensible default
//      *
//      * The user can open the node and change any of these values; we just
//      * pre-fill so the node is not completely blank.
//      */
//     _buildWarningNodeData(act) {
//         const message = act.message || "Warning: condition triggered";
//         return {
//             label: act.label || "Warning",
//             warning_type: "error",
//             warning: "UserError",
//             warning_text: message,
//         };
//     }
//
//     /**
//      * Builds the node.struct write payload for a Mail action node.
//      *
//      * We set mail_isTemplate = false (custom mail) and pre-populate:
//      *   - label
//      *   - mail_subject  : { value: '<subject>', selectionType: 'static' }
//      *   - mail_body     : plain text body string
//      *   - mail_to       : [ { value: [], selectionType: 'static' } ]
//      *     (empty recipient — user must fill in; we cannot resolve 'manager' etc.
//      *      to actual partner IDs without more context)
//      *
//      * mail_record is intentionally left unset because at canvas-build time we do
//      * not yet know which variable the user will bind the record to.  The user
//      * opens the node and selects it; all other fields will already be filled.
//      */
//     _buildMailNodeData(act) {
//         const subject = act.subject || act.summary || "Notification";
//         const body    = act.body    || act.message  || "";
//         return {
//             label:           act.label || "Send Mail",
//             mail_isTemplate: false,
//             mail_subject:    { value: subject, selectionType: 'static' },
//             mail_body:       body,
//             mail_to:         [{ value: [], selectionType: 'static' }],
//         };
//     }
//
//     /**
//      * Builds the node.struct write payload for an SMS action node.
//      *
//      * Sets sms_isTemplate = false (custom SMS) and pre-populates:
//      *   - label
//      *   - sms_message : the message text from the AI
//      */
//     _buildSmsNodeData(act) {
//         const message = act.message || act.body || "";
//         return {
//             label:          act.label || "Send SMS",
//             sms_isTemplate: false,
//             sms_message:    message,
//         };
//     }
//
//     /**
//      * Builds the node.struct write payload for an Activity action node.
//      *
//      * activity_user and activity_deadline use the { value, selectionType }
//      * shape that ActivityNode._ensureSelectionFieldShape expects.
//      * We leave them as empty-static so the node opens without errors,
//      * and the user fills in the actual values.
//      *
//      * activity_summary is pre-filled from the AI response.
//      */
//     _buildActivityNodeData(act) {
//         const summary = act.summary || act.message || "Follow up";
//         return {
//             label:             act.label || "Activity",
//             activity_summary:  summary,
//             // Deadline and user must be selected by the user;
//             // we pre-create the correct shape so the node doesn't crash on open.
//             activity_deadline: { value: false,  selectionType: 'static' },
//             activity_user:     { value: '',     selectionType: 'static' },
//         };
//     }
//
//     /**
//      * Returns a node.struct data payload for the given action type.
//      * Returns null for action types we don't need to pre-configure.
//      */
//     _buildActionNodeData(act) {
//         switch (act.type) {
//             case 'Warning':  return this._buildWarningNodeData(act);
//             case 'Mail':     return this._buildMailNodeData(act);
//             case 'SMS':      return this._buildSmsNodeData(act);
//             case 'Activity': return this._buildActivityNodeData(act);
//             default:         return act.label ? { label: act.label } : null;
//         }
//     }
//
//     async sendAiMessage() {
//         if (!this.state.aiInput) return;
//
//         const userId = this.state.aiMessages.length;
//         this.state.aiMessages.push({ from: 'user', text: this.state.aiInput, id: userId });
//
//         const aiResponseId = userId + 1;
//         let aiData;
//
//         try {
//             const result = await this.orm.call('chat.bot', 'my_python_method', [this.state.aiInput]);
//             aiData = typeof result === 'string' ? JSON.parse(result) : result;
//         } catch (e) {
//             console.error('AI call failed:', e);
//             this.state.aiMessages.push({ from: 'ai', text: 'AI call failed', id: aiResponseId });
//             return;
//         }
//
//         if (!aiData?.object) {
//             this.state.aiMessages.push({ from: 'ai', text: "No model returned by AI", id: aiResponseId });
//             return;
//         }
//
//         // ── 1. Resolve Odoo model ─────────────────────────────────────────────
//         const modelName = aiData.object.trim();
//         const res = await this.orm.searchRead(
//             'ir.model',
//             [['model', 'ilike', modelName]],
//             ['id', 'display_name', 'model']
//         );
//         if (!res?.length) {
//             this.state.aiMessages.push({ from: 'ai', text: `Model "${modelName}" not found`, id: aiResponseId });
//             return;
//         }
//         const modelId = res[0].id;
//
//         // ── 2. Set up the primary model node ─────────────────────────────────
//         await this.onSelectPrimary([{ id: modelId, display_name: res[0].display_name, model: res[0].model }]);
//         await new Promise(r => setTimeout(r, 120));
//
//         // Find the model node's drawflow ID
//         const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
//             .find(n => n.data.type === 'model');
//         const modelDfId = modelDfNode ? modelDfNode.id : null;
//
//         // ── 3. Resolve trigger work.function record ───────────────────────────
//         // The AI returns trigger labels like "On Create", "On Write", "On Unlink".
//         // work.function.func_name stores: 'create', 'write', 'unlink'
//         const TRIGGER_FUNC_NAMES = {
//             'On Create': 'create',
//             'On Write':  'write',
//             'On Unlink': 'unlink',
//         };
//         const funcName = TRIGGER_FUNC_NAMES[aiData.trigger] || 'create';
//
//         const triggerFunctions = await this.orm.searchRead(
//             'work.function',
//             [['func_name', '=', funcName]],
//             ['id', 'name', 'trigger_type']
//         );
//
//         if (!triggerFunctions.length) {
//             this.state.aiMessages.push({ from: 'ai', text: `Trigger function "${funcName}" not found in DB`, id: aiResponseId });
//             return;
//         }
//
//         const triggerFn   = triggerFunctions[0];
//         const actionId    = String(triggerFn.id);    // work.function DB id
//         const triggerType = triggerFn.trigger_type;  // 'create' | 'write' | 'unlink'
//
//         // ── 4. Add the trigger node ───────────────────────────────────────────
//         this.state.nodeDetails = this.state.nodeDetails || [];
//         const { dfId: triggerDfId } = await this._addNode(
//             aiData.trigger,          // e.g. "On Create" — becomes the node label/ttype
//             538, 340,
//             res[0].display_name,
//             modelId,
//             actionId,
//             'trigger',
//             triggerType
//         );
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── 5. Connect model → trigger ────────────────────────────────────────
//         if (modelDfId && triggerDfId) {
//             this._connectNodes(modelDfId, triggerDfId);
//         }
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── 6. Add Condition node (only when AI returned conditions) ──────────
//         let conditionDfId  = null;
//         let conditionNodeId = null;
//
//         if (aiData.conditions && aiData.conditions.length > 0) {
//             const { dfId: cDfId, nodeId: cNodeId } = await this._addNode(
//                 'Condition',
//                 538, 480,
//                 res[0].display_name,
//                 modelId,
//                 null,
//                 null
//             );
//             conditionDfId   = cDfId;
//             conditionNodeId = cNodeId;
//
//             // Connect trigger → condition
//             if (triggerDfId && conditionDfId) {
//                 this._connectNodes(triggerDfId, conditionDfId);
//             }
//             await new Promise(r => setTimeout(r, 80));
//
//             // Persist condition_tree_value so the node shows pre-filled rules
//             if (conditionNodeId) {
//                 const conditionTreeValue = this._buildConditionTreeValue(aiData.conditions);
//                 if (conditionTreeValue) {
//                     try {
//                         await this.orm.write('node.struct', [conditionNodeId], {
//                             condition_tree_value: conditionTreeValue,
//                         });
//                     } catch (e) {
//                         console.warn('Could not save condition_tree_value:', e);
//                     }
//                 }
//             }
//         }
//
//         // ── 7. Add action nodes ───────────────────────────────────────────────
//         // Every action connects from:
//         //   • output_1 of the Condition node (true branch)  — when conditions exist
//         //   • output_1 of the trigger node                  — when no conditions
//         //
//         // Actions are placed SIDE BY SIDE (parallel), NOT chained sequentially.
//         const actionParentDfId  = conditionDfId ?? triggerDfId;
//         const actionOutputClass = 'output_1';   // Condition output_1 = TRUE branch
//
//         const actions = aiData.actions || [];
//         for (let i = 0; i < actions.length; i++) {
//             const act = actions[i];
//             const nodeType = act?.type || 'Warning';
//
//             const { dfId: actDfId, nodeId: actNodeId } = await this._addNode(
//                 nodeType,
//                 660 + (i * 220), 620,
//                 res[0].display_name,
//                 modelId,
//                 null,
//                 null
//             );
//             await new Promise(r => setTimeout(r, 80));
//
//             // ── FIX: Write pre-filled configuration data to node.struct ──────
//             // This is the key fix: without this, every action node opens
//             // completely blank.  We write all fields the AI gave us (message,
//             // summary, subject, etc.) plus sensible defaults for required fields
//             // (warning_type, mail_isTemplate, etc.) so the node is functional
//             // even before the user touches its configuration panel.
//             if (actNodeId) {
//                 const nodeData = this._buildActionNodeData(act);
//                 if (nodeData) {
//                     try {
//                         await this.orm.write('node.struct', [actNodeId], nodeData);
//                     } catch (e) {
//                         console.warn(`Could not save config for ${nodeType} node:`, e);
//                     }
//                 }
//             }
//
//             // Each action connects from the SAME parent (parallel fan-out)
//             if (actionParentDfId && actDfId) {
//                 this._connectNodes(actionParentDfId, actDfId, actionOutputClass);
//             }
//             await new Promise(r => setTimeout(r, 60));
//         }
//
//         // ── 8. Confirm message ────────────────────────────────────────────────
//         const condCount = aiData.conditions?.length ?? 0;
//         const actCount  = actions.length;
//         const summary =
//             `✓ Workflow built: ${aiData.trigger} on ${res[0].display_name}` +
//             (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
//             ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;
//
//         this.state.aiMessages.push({ from: 'ai', text: summary, id: aiResponseId });
//         this.state.aiInput = "";
//     }
// }
//
// WorkFlowAutoOverride.template = "client_action.automation_view";
//
// registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });
//
//

// /** @odoo-module **/
// import { registry } from "@web/core/registry";
// import { useState } from "@odoo/owl";
// import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";
//
// class WorkFlowAutoOverride extends WorkFlowAuto {
//
//     setup() {
//         super.setup();
//         this.state = useState({
//             // Base arrays expected by WorkFlowAuto
//             nodeDetails: [],
//             actions: [],
//
//             // AI Chat state
//             aiChatOpen: false,
//             aiInput: "",
//             aiMessages: [],
//         });
//     }
//
//     settingModelState(data) {
//         if (!data) return;
//         this.state.modelState = data.modelState || [];
//     }
//
//     openAiChat() {
//         this.state.aiChatOpen = !this.state.aiChatOpen;
//         console.log('AI Chat Open:', this.state.aiChatOpen);
//     }
//
//     /**
//      * Adds a node and returns both the backend nodeId and the drawflow canvas ID.
//      * Snapshots existing IDs before the call, then diffs after to find the new node.
//      */
//     async _addNode(name, posX, posY, selectedValue, record, action, type, triggerType) {
//         const before = new Set(
//             Object.values(this.editor.drawflow.drawflow.Home.data).map(n => n.id)
//         );
//
//         await this.addNodeToDrawFlow(name, posX, posY, selectedValue, record, action, type, triggerType);
//
//         // The newly added node is the one whose drawflow ID was not present before
//         const dfData = this.editor.drawflow.drawflow.Home.data;
//         const newNode = Object.values(dfData).find(n => !before.has(n.id));
//         if (!newNode) return { dfId: null, nodeId: null };
//
//         return { dfId: newNode.id, nodeId: newNode.data.nodeId };
//     }
//
//     /**
//      * Connects two drawflow nodes.
//      * outputClass defaults to 'output_1' (standard single-output port).
//      * For Condition nodes use 'output_1' for the TRUE branch.
//      */
//     _connectNodes(outputDfId, inputDfId, outputClass = 'output_1', inputClass = 'input_1') {
//         if (!outputDfId || !inputDfId) return;
//         this.editor.addConnection(outputDfId, inputDfId, outputClass, inputClass);
//     }
//
//     /**
//      * Converts the AI conditions array into the condition_tree_value structure
//      * that conditionNode reads on open.
//      *
//      * AI format:  [{ field: 'discount', operator: '>', value: 50 }]
//      *
//      * conditionNode uses fieldType:'record' with the global current_record variable
//      * so that code generation can resolve `current_record.<field>` correctly.
//      */
//     _buildConditionTreeValue(aiConditions) {
//         if (!aiConditions || !aiConditions.length) return null;
//
//         // 'current_record' is always registered as the global record variable
//         const CURRENT_RECORD_VAR_ID = "global/variable/current/rec";
//
//         const conditions = aiConditions.map((cond, index) => ({
//             type: 'simple',
//             fieldType: 'record',
//             field: {
//                 record: CURRENT_RECORD_VAR_ID,
//                 path: cond.field,
//                 info: {
//                     fieldDef: {
//                         // Guess the field type from the value so code-gen picks
//                         // the right comparison template (number → float branch).
//                         type: this._guessFieldType(cond.value),
//                     }
//                 }
//             },
//             operator: cond.operator,
//             value: {
//                 value: cond.value,
//                 fieldType: 'static',
//             },
//             logicalOperator: index === 0 ? 'and' : 'and',
//         }));
//
//         return [{ conditions, groupOperator: 'and' }];
//     }
//
//     /** Infer a conditionNode-compatible field type from the raw value. */
//     _guessFieldType(value) {
//         if (typeof value === 'boolean') return 'boolean';
//         if (typeof value === 'number') return 'float';
//         return 'char';
//     }
//
//     async sendAiMessage() {
//         if (!this.state.aiInput) return;
//
//         const userId = this.state.aiMessages.length;
//         this.state.aiMessages.push({ from: 'user', text: this.state.aiInput, id: userId });
//
//         const aiResponseId = userId + 1;
//         let aiData;
//
//         try {
//             const result = await this.orm.call('chat.bot', 'my_python_method', [this.state.aiInput]);
//             aiData = typeof result === 'string' ? JSON.parse(result) : result;
//         } catch (e) {
//             console.error('AI call failed:', e);
//             this.state.aiMessages.push({ from: 'ai', text: 'AI call failed', id: aiResponseId });
//             return;
//         }
//
//         if (!aiData?.object) {
//             this.state.aiMessages.push({ from: 'ai', text: "No model returned by AI", id: aiResponseId });
//             return;
//         }
//
//         // ── 1. Resolve Odoo model ─────────────────────────────────────────────
//         const modelName = aiData.object.trim();
//         const res = await this.orm.searchRead(
//             'ir.model',
//             [['model', 'ilike', modelName]],
//             ['id', 'display_name', 'model']
//         );
//         if (!res?.length) {
//             this.state.aiMessages.push({ from: 'ai', text: `Model "${modelName}" not found`, id: aiResponseId });
//             return;
//         }
//         const modelId = res[0].id;
//
//         // ── 2. Set up the primary model node ─────────────────────────────────
//         await this.onSelectPrimary([{ id: modelId, display_name: res[0].display_name, model: res[0].model }]);
//         await new Promise(r => setTimeout(r, 120));
//
//         // Find the model node's drawflow ID
//         const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
//             .find(n => n.data.type === 'model');
//         const modelDfId = modelDfNode ? modelDfNode.id : null;
//
//         // ── 3. Resolve trigger work.function record ───────────────────────────
//         // The AI returns trigger labels like "On Create", "On Write", "On Unlink".
//         // work.function.func_name stores: 'create', 'write', 'unlink'  (NOT 'on_create' etc.)
//         const TRIGGER_FUNC_NAMES = {
//             'On Create': 'create',
//             'On Write':  'write',
//             'On Unlink': 'unlink',
//         };
//         const funcName = TRIGGER_FUNC_NAMES[aiData.trigger] || 'create';
//
//         const triggerFunctions = await this.orm.searchRead(
//             'work.function',
//             [['func_name', '=', funcName]],
//             ['id', 'name', 'trigger_type']
//         );
//
//         if (!triggerFunctions.length) {
//             this.state.aiMessages.push({ from: 'ai', text: `Trigger function "${funcName}" not found in DB`, id: aiResponseId });
//             return;
//         }
//
//         const triggerFn = triggerFunctions[0];
//         const actionId   = String(triggerFn.id);       // work.function DB id
//         const triggerType = triggerFn.trigger_type;    // 'create' | 'write' | 'unlink'
//
//         // ── 4. Add the trigger node ───────────────────────────────────────────
//         this.state.nodeDetails = this.state.nodeDetails || [];
//         const { dfId: triggerDfId } = await this._addNode(
//             aiData.trigger,          // e.g. "On Create"  — becomes the node label/ttype
//             538, 340,
//             res[0].display_name,
//             modelId,
//             actionId,
//             'trigger',
//             triggerType
//         );
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── 5. Connect model → trigger ────────────────────────────────────────
//         if (modelDfId && triggerDfId) {
//             this._connectNodes(modelDfId, triggerDfId);
//         }
//         await new Promise(r => setTimeout(r, 80));
//
//         // ── 6. Add Condition node (only when AI returned conditions) ──────────
//         // conditionDfId is stored separately so ALL actions can connect from it.
//         let conditionDfId = null;
//         let conditionNodeId = null;
//
//         if (aiData.conditions && aiData.conditions.length > 0) {
//             const { dfId: cDfId, nodeId: cNodeId } = await this._addNode(
//                 'Condition',
//                 538, 480,
//                 res[0].display_name,
//                 modelId,
//                 null,
//                 null
//             );
//             conditionDfId  = cDfId;
//             conditionNodeId = cNodeId;
//
//             // Connect trigger → condition
//             if (triggerDfId && conditionDfId) {
//                 this._connectNodes(triggerDfId, conditionDfId);
//             }
//             await new Promise(r => setTimeout(r, 80));
//
//             // Persist condition data directly on node.struct so the node shows
//             // the pre-filled conditions when the user opens its configuration.
//             if (conditionNodeId) {
//                 const conditionTreeValue = this._buildConditionTreeValue(aiData.conditions);
//                 if (conditionTreeValue) {
//                     try {
//                         await this.orm.write('node.struct', [conditionNodeId], {
//                             condition_tree_value: conditionTreeValue,
//                         });
//                     } catch (e) {
//                         console.warn('Could not save condition_tree_value:', e);
//                     }
//                 }
//             }
//         }
//
//         // ── 7. Add action nodes ───────────────────────────────────────────────
//         // Every action connects from:
//         //   • output_1 of the Condition node  (true branch)  — when conditions exist
//         //   • output_1 of the trigger node                   — when no conditions
//         //
//         // Actions are placed SIDE BY SIDE (parallel), NOT chained sequentially.
//         // Each connects independently from the same parent output.
//         const actionParentDfId   = conditionDfId   ?? triggerDfId;
//         const actionOutputClass  = 'output_1';   // Condition output_1 = TRUE branch
//
//         const actions = aiData.actions || [];
//         for (let i = 0; i < actions.length; i++) {
//             const act = actions[i];
//             const { dfId: actDfId } = await this._addNode(
//                 act?.type || 'Warning',
//                 660 + (i * 220), 620,
//                 res[0].display_name,
//                 modelId,
//                 null,
//                 null
//             );
//             await new Promise(r => setTimeout(r, 80));
//
//             // Each action connects from the SAME parent (parallel fan-out)
//             if (actionParentDfId && actDfId) {
//                 this._connectNodes(actionParentDfId, actDfId, actionOutputClass);
//             }
//             await new Promise(r => setTimeout(r, 60));
//         }
//
//         // ── 8. Confirm message ────────────────────────────────────────────────
//         const condCount   = aiData.conditions?.length ?? 0;
//         const actCount    = actions.length;
//         const summary =
//             `✓ Workflow built: ${aiData.trigger} on ${res[0].display_name}` +
//             (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
//             ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;
//
//         this.state.aiMessages.push({ from: 'ai', text: summary, id: aiResponseId });
//         this.state.aiInput = "";
//     }
// }
//
// WorkFlowAutoOverride.template = "client_action.automation_view";
//
// registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });
