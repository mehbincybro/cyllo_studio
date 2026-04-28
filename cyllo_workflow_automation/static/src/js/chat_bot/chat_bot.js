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
        this.state = useState({
            nodeDetails: [],
            actions: [],
            aiChatOpen: false,
            aiInput: "",
            aiMessages: [],
            aiLoading: false,
            chatPos: { right: 100, bottom: 80 },
            iconPos: { right: 100, bottom: 20 },
        });
    }

    // ─── Icon drag-to-reposition (chat box follows the icon) ────────────────

    _onIconMouseDown(ev) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();

        const startX      = ev.clientX;
        const startY      = ev.clientY;
        const startRight  = this.state.iconPos.right;
        const startBottom = this.state.iconPos.bottom;
        const vpW = window.innerWidth;
        const vpH = window.innerHeight;
        const ICON_SIZE   = 50;
        const BOX_W       = 340;
        const BOX_H       = 440;

        let didDrag = false;

        const onMove = (moveEv) => {
            const dx = moveEv.clientX - startX;
            const dy = moveEv.clientY - startY;
            if (!didDrag && Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
            didDrag = true;

            const newRight  = Math.max(0, Math.min(vpW - ICON_SIZE, startRight  - dx));
            const newBottom = Math.max(0, Math.min(vpH - ICON_SIZE, startBottom - dy));
            this.state.iconPos = { right: newRight, bottom: newBottom };

            const boxRight  = newRight;
            const boxBottom = newBottom + ICON_SIZE + 8;
            this.state.chatPos = {
                right:  Math.max(0, Math.min(vpW - BOX_W, boxRight)),
                bottom: Math.max(0, Math.min(vpH - BOX_H, boxBottom)),
            };
        };

        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup',   onUp);
            if (didDrag) return;
            this.openAiChat();
        };

        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup',   onUp);
    }

    _stopBubble(ev) {
        ev.stopPropagation();
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

    _pushAiMessage(text, options = {}) {
        const { type = 'info' } = options;
        this.state.aiMessages.push({ from: 'ai', text, id: _nextMsgId(), type });
        this._scrollChatToBottom();
    }

    _scrollChatToBottom() {
        Promise.resolve().then(() => {
            const el = this.__owl__?.refs?.aiChatOutput;
            if (el) el.scrollTop = el.scrollHeight;
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
        if (!uniqueIds.length) return;
        requestAnimationFrame(() => requestAnimationFrame(() => {
            const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
            const nodes = uniqueIds.map((id) => flowData[id]).filter(Boolean);
            if (!nodes.length || typeof this.getViewportBoundsForNodes !== 'function') return;

            const viewport = this.getViewportBoundsForNodes(nodes);
            if (!viewport) return;

            const targetZoom   = 1;
            const drawBoardEl  = this.drawBoard?.el;
            if (!drawBoardEl || typeof this.getNodeCanvasBounds !== 'function') return;

            const bounds = nodes.reduce((acc, node) => {
                const nodeBounds = this.getNodeCanvasBounds(node);
                if (!nodeBounds) return acc;
                return {
                    minX: Math.min(acc.minX, nodeBounds.left),
                    minY: Math.min(acc.minY, nodeBounds.top),
                    maxX: Math.max(acc.maxX, nodeBounds.right),
                    maxY: Math.max(acc.maxY, nodeBounds.bottom),
                };
            }, { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });

            if (!Number.isFinite(bounds.minX)) return;

            const viewportWidth  = drawBoardEl.clientWidth;
            const viewportHeight = drawBoardEl.clientHeight;
            const width          = Math.max(1, bounds.maxX - bounds.minX);
            const height         = Math.max(1, bounds.maxY - bounds.minY);
            const targetX        = Math.max(48, (viewportWidth  - width)  / 2) - bounds.minX;
            const targetY        = Math.max(32, (viewportHeight - height) / 2) - bounds.minY;

            this.initialViewport = { canvas_x: targetX, canvas_y: targetY, zoom: targetZoom };

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
    // Resolve a dotted field path to its final fieldDef
    // e.g. "order_line.product_uom_qty" on "sale.order"
    //   -> walks: sale.order.order_line (one2many -> sale.order.line)
    //          -> sale.order.line.product_uom_qty (float)
    //   -> returns { type: 'float', name: 'product_uom_qty',
    //                resModel: 'sale.order.line',
    //                fullPath: 'order_line.product_uom_qty' }
    // ─────────────────────────────────────────────────────────────────────────

    async _resolveFieldPath(rootModel, fieldPath) {
        const parts = fieldPath.split('.');
        let currentModel = rootModel;
        let currentFieldDefs = await this._getModelFieldDefs(currentModel);
        let resolvedFieldDef = null;

        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            const fieldDef = currentFieldDefs?.[part];

            if (!fieldDef) {
                // Field not found at this level — return best-effort info
                return {
                    type: 'char',
                    name: part,
                    resModel: currentModel,
                    fullPath: fieldPath,
                    relation: null,
                    notFound: true,
                };
            }

            if (i === parts.length - 1) {
                // This is the final field in the path
                resolvedFieldDef = {
                    type: fieldDef.type,
                    name: part,
                    resModel: currentModel,
                    fullPath: fieldPath,
                    relation: fieldDef.relation || null,
                    selection: fieldDef.selection || null,
                };
            } else {
                // Intermediate relational field — walk into its related model
                if (!fieldDef.relation) {
                    // Can't traverse further — not a relational field
                    return {
                        type: fieldDef.type,
                        name: part,
                        resModel: currentModel,
                        fullPath: fieldPath,
                        relation: null,
                    };
                }
                currentModel = fieldDef.relation;
                currentFieldDefs = await this._getModelFieldDefs(currentModel);
            }
        }

        return resolvedFieldDef || { type: 'char', name: parts[parts.length - 1], resModel: rootModel, fullPath: fieldPath };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Activity type resolver
    // ─────────────────────────────────────────────────────────────────────────

    async _resolveActivityType(act) {
        const typeName = (act.activity_type_name || '').trim();

        const trySearch = async (domain) => {
            try {
                const rows = await this.orm.searchRead(
                    'mail.activity.type', domain, ['id', 'name'], { limit: 1 }
                );
                return rows.length ? { id: rows[0].id, name: rows[0].name } : null;
            } catch {
                return null;
            }
        };

        if (typeName) {
            const exact = await trySearch([['name', '=', typeName]]);
            if (exact) return exact;
            const ilike = await trySearch([['name', 'ilike', typeName]]);
            if (ilike) return ilike;
        }

        const todo = await trySearch([['name', '=', 'To-Do']]);
        if (todo) return todo;
        const todoIlike = await trySearch([['name', 'ilike', 'to-do']]);
        if (todoIlike) return todoIlike;

        return await trySearch([]);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Condition tree builder — handles both simple and dotted field paths
    // ─────────────────────────────────────────────────────────────────────────

    async _buildConditionTreeValue(aiConditions, modelName, fieldDefs = {}) {
        if (!aiConditions || !aiConditions.length) return null;

        const conditions = await Promise.all(aiConditions.map(async (cond) => {
            const fieldPath = cond.field || '';
            const isDotted  = fieldPath.includes('.');

            let resolvedFieldDef;
            let condResModel = modelName;

            if (isDotted) {
                // Walk the dotted path to get the real field type and model
                const resolved = await this._resolveFieldPath(modelName, fieldPath);
                resolvedFieldDef = {
                    type:     resolved.type,
                    name:     resolved.name,
                    ...(resolved.relation  ? { relation:  resolved.relation  } : {}),
                    ...(resolved.selection ? { selection: resolved.selection } : {}),
                };
                condResModel = resolved.resModel;
            } else {
                // Direct field on the root model
                const fieldDef = fieldDefs?.[fieldPath];
                if (fieldDef) {
                    resolvedFieldDef = {
                        type: fieldDef.type,
                        name: fieldPath,
                        ...(fieldDef.relation  ? { relation:  fieldDef.relation  } : {}),
                        ...(fieldDef.selection ? { selection: fieldDef.selection } : {}),
                    };
                } else {
                    resolvedFieldDef = {
                        type: this._guessFieldType(cond.value),
                        name: fieldPath,
                    };
                }
            }

            return {
                type: 'simple',
                fieldType: 'record',
                field: {
                    record: CURRENT_RECORD_VAR_ID,
                    path:   fieldPath,
                    info: {
                        fieldDef: resolvedFieldDef,
                        resModel: condResModel,
                    },
                },
                operator: this._normalizeConditionOperator(cond.operator),
                value: {
                    value:     cond.value,
                    fieldType: 'static',
                },
                logicalOperator: 'and',
            };
        }));

        return [{ conditions, groupOperator: 'and' }];
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
        return this._buildVariableSelection(CURRENT_DATE_VAR_ID, CURRENT_DATE_VAR_NAME);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Node data builders (one per action type)
    // ─────────────────────────────────────────────────────────────────────────

    _buildWarningNodeData(act) {
        const warningType = act.warning_type || 'error';

        if (warningType === 'notification') {
            const VALID_NOTIFICATION_TYPES = ['info', 'success', 'warning', 'danger'];
            const notificationType = VALID_NOTIFICATION_TYPES.includes(act.notification_type)
                ? act.notification_type
                : 'info';

            return {
                label:               act.label              || "Notification",
                warning_type:        'notification',
                notification_type:   notificationType,
                notification_title:  act.notification_title || act.label || "Notification",
                warning_text:        act.message            || "",
                notification_sticky: act.sticky === true,
            };
        }

        const VALID_ERRORS = ['UserError', 'ValidationError', 'AccessError', 'MissingError', 'AccessDenied', 'CacheMiss', 'RedirectWarning'];
        const warning = VALID_ERRORS.includes(act.warning) ? act.warning : 'UserError';

        return {
            label:        act.label   || "Warning",
            warning_type: 'error',
            warning:      warning,
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

    _buildActivityNodeData(act, context = {}) {
        const summary      = act.summary || act.message || "Follow up";
        const activityType = context.resolvedActivityType || null;
        return {
            label:             act.label || "Activity",
            activity_record:   this._currentRecordRef(),
            activity_type:     activityType,
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

        if (!relationModel || !normalizedValues.length) return [];

        const numericIds = normalizedValues
            .map((value) => typeof value === 'number' ? value : (typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : null))
            .filter((value) => Number.isInteger(value));
        if (numericIds.length === normalizedValues.length) return numericIds;

        const resolvedIds = [];
        for (const value of normalizedValues) {
            if (typeof value === 'number') { resolvedIds.push(value); continue; }

            let records = [];
            const candidateDomains = [
                [['name', '=', value]],
                [['display_name', '=', value]],
                [['name', 'ilike', value]],
                [['display_name', 'ilike', value]],
            ];

            for (const domain of candidateDomains) {
                try { records = await this.orm.searchRead(relationModel, domain, ['id'], { limit: 1 }); } catch { records = []; }
                if (records.length) break;
            }

            if (!records.length && createIfMissing) {
                try {
                    const [createdId] = await this.orm.create(relationModel, [{ name: value }]);
                    if (createdId) records = [{ id: createdId }];
                } catch { records = []; }
            }

            if (records.length) resolvedIds.push(records[0].id);
        }

        return [...new Set(resolvedIds)];
    }

    async _buildWriteNodeData(act, modelName, fieldDefs = {}) {
        const fieldDef      = fieldDefs?.[act.field] || {};
        let resolvedValue   = act.value !== undefined ? act.value : "";
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

    async _buildActionNodeData(act, context = {}) {
        switch (act.type) {
            case 'Warning':  return this._buildWarningNodeData(act);
            case 'Mail':     return this._buildMailNodeData(act, context);
            case 'SMS':      return this._buildSmsNodeData(act, context);
            case 'Activity': return this._buildActivityNodeData(act, context);
            case 'Write':    return this._buildWriteNodeData(act, context.modelName, context.fieldDefs || {});
            default:         return act.label ? { label: act.label } : null;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Enter-key handler for the chat input
    // ─────────────────────────────────────────────────────────────────────────

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
        if (!userQuery || this.state.aiLoading) return;

        const userMsgId = _nextMsgId();
        this.state.aiMessages.push({ from: 'user', text: userQuery, id: userMsgId, type: 'info' });
        this.state.aiInput   = "";
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
                this._pushAiMessage(`AI call failed: ${rpcMessage}`, { type: 'error' });
                return;
            }

            // ── Step 2: Validate AI response ─────────────────────────────────
            if (aiData?.error) {
                const errorText = [aiData.error, aiData.details].filter(Boolean).join(' — ');
                this._pushAiMessage(errorText, { type: 'error' });
                return;
            }

            if (!aiData?.object) {
                this._pushAiMessage('No model was returned by the AI. Please rephrase your query.', { type: 'error' });
                return;
            }
            if (!aiData?.trigger) {
                this._pushAiMessage('No trigger was returned by the AI. Please rephrase your query.', { type: 'error' });
                return;
            }
            if (!aiData?.actions?.length) {
                this._pushAiMessage('No actions were returned by the AI. Please rephrase your query.', { type: 'error' });
                return;
            }

            // ── Step 3: Resolve Odoo model ───────────────────────────────────
            const modelName = aiData.object.trim();
            let res;
            try {
                res = await this.orm.searchRead('ir.model', [['model', '=', modelName]], ['id', 'display_name', 'model']);
                if (!res?.length) {
                    res = await this.orm.searchRead('ir.model', [['model', 'ilike', modelName]], ['id', 'display_name', 'model']);
                }
            } catch (e) {
                this._pushAiMessage(`Failed to search for model "${modelName}": ${e?.message || e}`, { type: 'error' });
                return;
            }

            if (!res?.length) {
                this._pushAiMessage(`Model "${modelName}" was not found. Please install the required module and try again.`, { type: 'error' });
                return;
            }

            const modelId            = res[0].id;
            const modelTechnicalName = res[0].model;
            const modelDisplayName   = res[0].display_name;

            // ── Step 4: Fetch field definitions ───────────────────────────────
            const modelFieldDefs = await this._getModelFieldDefs(modelTechnicalName);

            // ── Step 5: Set up the primary model node ─────────────────────────
            try {
                await this.onSelectPrimary([{ id: modelId, display_name: modelDisplayName, model: modelTechnicalName }]);
            } catch (e) {
                this._pushAiMessage(`Failed to set up model node: ${e?.message || e}`, { type: 'error' });
                return;
            }
            await new Promise(r => setTimeout(r, 150));

            const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
                .find(n => n.data.type === 'model');
            const modelDfId = modelDfNode ? modelDfNode.id : null;
            const createdNodeDfIds = modelDfId ? [modelDfId] : [];

            // ── Step 6: Resolve trigger work.function ─────────────────────────
            const TRIGGER_FUNC_NAMES = { 'On Create': 'create', 'On Write': 'write', 'On Unlink': 'unlink' };
            const funcName = TRIGGER_FUNC_NAMES[aiData.trigger] || 'create';

            let triggerFunctions;
            try {
                triggerFunctions = await this.orm.searchRead(
                    'work.function', [['func_name', '=', funcName]], ['id', 'name', 'trigger_type']
                );
            } catch (e) {
                this._pushAiMessage(`Failed to search trigger functions: ${e?.message || e}`, { type: 'error' });
                return;
            }

            if (!triggerFunctions.length) {
                this._pushAiMessage(`Trigger function "${funcName}" was not found in the database.`, { type: 'error' });
                return;
            }

            const triggerFn   = triggerFunctions[0];
            const actionId    = String(triggerFn.id);
            const triggerType = triggerFn.trigger_type;

            // ── Step 7: Add trigger node ──────────────────────────────────────
            this.state.nodeDetails = this.state.nodeDetails || [];
            let triggerDfId;
            try {
                const result = await this._addNode(
                    aiData.trigger, 538, 340, modelDisplayName, modelId, actionId, 'trigger', triggerType
                );
                triggerDfId = result.dfId;
                if (triggerDfId) createdNodeDfIds.push(triggerDfId);
            } catch (e) {
                this._pushAiMessage(`Failed to add trigger node: ${e?.message || e}`, { type: 'error' });
                return;
            }
            await new Promise(r => setTimeout(r, 100));

            // ── Step 8: Connect model → trigger ───────────────────────────────
            if (modelDfId && triggerDfId) this._connectNodes(modelDfId, triggerDfId);
            await new Promise(r => setTimeout(r, 80));

            // ── Step 9: Add Condition node ─────────────────────────────────────
            let conditionDfId   = null;
            let conditionNodeId = null;

            if (aiData.conditions && aiData.conditions.length > 0) {
                try {
                    const { dfId: cDfId, nodeId: cNodeId } = await this._addNode(
                        'Condition', 538, 480, modelDisplayName, modelId, null, null
                    );
                    conditionDfId   = cDfId;
                    conditionNodeId = cNodeId;
                    if (conditionDfId) createdNodeDfIds.push(conditionDfId);
                } catch (e) {
                    console.warn('Failed to add Condition node:', e);
                }

                if (triggerDfId && conditionDfId) this._connectNodes(triggerDfId, conditionDfId);
                await new Promise(r => setTimeout(r, 80));

                if (conditionNodeId) {
                    // _buildConditionTreeValue is now async — awaited here
                    const conditionTreeValue = await this._buildConditionTreeValue(
                        aiData.conditions, modelTechnicalName, modelFieldDefs
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

            // ── Step 10: Add action nodes ──────────────────────────────────────
            const actionParentDfId = conditionDfId ?? triggerDfId;
            const actions          = aiData.actions || [];

            for (let i = 0; i < actions.length; i++) {
                const act      = actions[i];
                const nodeType = act?.type || 'Warning';

                let actDfId, actNodeId;
                try {
                    const result = await this._addNode(
                        nodeType, 660 + (i * 260), 620, modelDisplayName, modelId, null, null
                    );
                    actDfId   = result.dfId;
                    actNodeId = result.nodeId;
                    if (actDfId) createdNodeDfIds.push(actDfId);
                } catch (e) {
                    console.warn(`Failed to add action node (${nodeType}):`, e);
                    continue;
                }
                await new Promise(r => setTimeout(r, 80));

                if (actNodeId) {
                    const actionContext = {
                        modelName: modelTechnicalName,
                        fieldDefs: modelFieldDefs,
                    };

                    if (nodeType === 'Mail') {
                        actionContext.recipientSelection = this._resolveMailRecipientSelection(
                            userQuery, act, modelTechnicalName, modelFieldDefs
                        );
                    } else if (nodeType === 'SMS') {
                        actionContext.recipientSelection = this._resolveSmsRecipientSelection(
                            userQuery, act, modelTechnicalName, modelFieldDefs
                        );
                    } else if (nodeType === 'Activity') {
                        actionContext.resolvedActivityType = await this._resolveActivityType(act);
                        actionContext.assigneeSelection    = this._resolveActivityAssigneeSelection(
                            userQuery, act, modelTechnicalName, modelFieldDefs
                        );
                        actionContext.deadlineSelection    = this._resolveActivityDeadlineSelection(
                            userQuery, act
                        );
                    }

                    const nodeData = await this._buildActionNodeData(act, actionContext);
                    if (nodeData) {
                        try {
                            await this.orm.write('node.struct', [actNodeId], nodeData);
                        } catch (e) {
                            console.warn(`Could not save config for ${nodeType} node:`, e);
                        }
                    }
                }

                if (actionParentDfId && actDfId) this._connectNodes(actionParentDfId, actDfId, 'output_1');
                await new Promise(r => setTimeout(r, 60));
            }

            // ── Step 11: Success message ───────────────────────────────────────
            const condCount = aiData.conditions?.length ?? 0;
            const actCount  = actions.length;
            const summary =
                `✓ Workflow built: ${aiData.trigger} on ${modelDisplayName}` +
                (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
                ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;

            this._focusAiWorkflow(createdNodeDfIds);
            this._pushAiMessage(summary);

        } finally {
            this.state.aiLoading = false;
        }
    }
}

WorkFlowAutoOverride.template = "client_action.automation_view";

registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });