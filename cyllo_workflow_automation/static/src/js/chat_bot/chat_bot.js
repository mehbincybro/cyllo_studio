/** @odoo-module **/
import { registry } from "@web/core/registry";
import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";
const { onMounted, onWillUnmount } = owl;

// Global variable IDs (must match what WorkFlowAuto seeds into env.globalVariables)
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
        const actionContext = this.props?.action?.context;
        const hasContextId  = actionContext && (actionContext.rec_id || actionContext.id);
        if (!hasContextId && this.id) {
            this.saveManually(null);
            this.id = null;
            this.action.doAction({
                type:      "ir.actions.act_window",
                res_model: "work.auto",
                views:     [[false, "workflowCard"], [false, "list"], [false, "form"]],
                target:    "main",
                name:      "Workflow Automation",
            });
            return;
        }

        this._fieldCache = new Map();
        // Extend the parent's reactive state — never reassign this.state entirely
        // or parent properties (actions, model_id, …) will be wiped and template
        // getters like usedTriggerNames.length will crash with undefined.length.
        Object.assign(this.state, {
            aiChatOpen: false,
            aiInput: "",
            aiMessages: [],
            aiLoading: false,
            chatPos: { right: 100, bottom: 80 },
            iconPos: { right: 100, bottom: 20 },
        });

        this._handleAiChatOutsideClick = this._handleAiChatOutsideClick.bind(this);
        onMounted(() => {
            document.addEventListener("mousedown", this._handleAiChatOutsideClick);
        });
        onWillUnmount(() => {
            document.removeEventListener("mousedown", this._handleAiChatOutsideClick);
        });
    }

    static ICON_SIZE = 56;
    static BOX_W     = 520;
    static BOX_H     = 620;

    _onPanelHeaderMouseDown(ev) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();

        const startX      = ev.clientX;
        const startY      = ev.clientY;
        const startRight  = this.state.chatPos.right;
        const startBottom = this.state.chatPos.bottom;
        const vpW = window.innerWidth;
        const vpH = window.innerHeight;
        const { ICON_SIZE, BOX_W, BOX_H } = WorkFlowAutoOverride;

        const onMove = (moveEv) => {
            const dx       = moveEv.clientX - startX;
            const dy       = moveEv.clientY - startY;
            const newRight  = Math.max(0, Math.min(vpW - BOX_W, startRight  - dx));
            const newBottom = Math.max(0, Math.min(vpH - BOX_H, startBottom - dy));
            this.state.chatPos = { right: newRight, bottom: newBottom };
            // Keep icon centred below the panel
            this.state.iconPos = {
                right:  newRight + Math.round((BOX_W - ICON_SIZE) / 2),
                bottom: Math.max(0, newBottom - ICON_SIZE - 8),
            };
        };

        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup',   onUp);
        };

        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup',   onUp);
    }

    // Icon click/drag — click toggles chat; drag moves icon + panel

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
        const { ICON_SIZE, BOX_W, BOX_H } = WorkFlowAutoOverride;
        let didDrag = false;

        const onMove = (moveEv) => {
            const dx = moveEv.clientX - startX;
            const dy = moveEv.clientY - startY;
            if (!didDrag && Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
            didDrag = true;
            const newRight  = Math.max(0, Math.min(vpW - ICON_SIZE, startRight  - dx));
            const newBottom = Math.max(0, Math.min(vpH - ICON_SIZE, startBottom - dy));
            this.state.iconPos = { right: newRight, bottom: newBottom };
            // Keep panel centred above icon
            this.state.chatPos = {
                right:  Math.max(0, Math.min(vpW - BOX_W, newRight - Math.round((BOX_W - ICON_SIZE) / 2))),
                bottom: Math.max(0, Math.min(vpH - BOX_H, newBottom + ICON_SIZE + 8)),
            };
        };

        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup',   onUp);
            if (!didDrag) this.openAiChat();
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

    _handleAiChatOutsideClick(ev) {
        if (!this.state.aiChatOpen) {
            return;
        }
        const chatBox = this.__owl__?.refs?.aiChatBox;
        const chatIcon = this.__owl__?.refs?.aiChatIcon;
        const target = ev.target;
        if (chatBox?.contains(target) || chatIcon?.contains(target)) {
            return;
        }
        this.state.aiChatOpen = false;
    }

    // UI helpers

    _pushAiMessage(text, options = {}) {
        const { type = 'info' } = options;
        this.state.aiMessages.push({ from: 'ai', text, id: _nextMsgId(), type });
        this._scrollChatToBottom();
    }

    _showAiError(error, fallback = "Request failed. Please try again.") {
        const raw = typeof error === "string" ? error : error?.data?.message || error?.message || error?.error || error?.details || "";
        const text = String(raw).toLowerCase();
        const message = text.includes("quota")
            ? "AI request failed: quota limit expired."
            : text.includes("rate limit")
                ? "AI request failed: rate limit exceeded."
                : raw || fallback;
        this._pushAiMessage(message, { type: 'error' });
    }

    _scrollChatToBottom() {
        Promise.resolve().then(() => {
            const el = this.__owl__?.refs?.aiChatOutput;
            if (el) el.scrollTop = el.scrollHeight;
        });
    }

    _isAiUpdateIntent(query) {
        const text = this._normalizeText(query);
        return text.startsWith('also ') ||
            text.startsWith('add ') ||
            text.startsWith('add a ') ||
            text.startsWith('add an ') ||
            text.startsWith('additionally ') ||
            text.startsWith('in addition ') ||
            text.includes('add a new node') ||
            text.includes('new node') ||
            text.includes('continue this workflow') ||
            text.includes('continue this flow') ||
            text.includes('same workflow') ||
            text.includes('this workflow') ||
            text.includes('that warning') ||
            text.includes('success message') ||
            [
            ' also ',
            ' add ',
            ' along with ',
            ' in addition ',
            ' additionally ',
            ' too ',
        ].some((token) => ` ${text} `.includes(token));
    }

    _isAiRemoveIntent(query) {
        const text = this._normalizeText(query);
        return text.startsWith('remove ') ||
            text.startsWith('delete ') ||
            text.includes(' remove ') ||
            text.includes(' delete ') ||
            text.includes(' remove the ') ||
            text.includes(' delete the ');
    }

    _getActionTypeFromQuery(query) {
        const text = this._normalizeText(query);
        const actionMap = [
            ['reuse automation', 'Reuse Automation'],
            ['activity', 'Activity'],
            ['warning', 'Warning'],
            ['mail', 'Mail'],
            ['sms', 'SMS'],
            ['window', 'Window'],
            ['follower', 'Follower'],
            ['code', 'Code'],
            ['button click', 'Button Click'],
        ];
        const matched = actionMap.find(([keyword]) => text.includes(keyword));
        return matched ? matched[1] : null;
    }

    async _removeExistingActionNode(query) {
        const targetType = this._getActionTypeFromQuery(query);
        if (!targetType) {
            this._pushAiMessage('I could not determine which node type to remove. Mention the exact node, for example: remove Activity or delete Warning.', { type: 'error' });
            return true;
        }

        const flowData = this.getCurrentFlowData();
        const candidates = Object.values(flowData || {}).filter((node) =>
            node?.data?.type === 'action_to_do' && node?.data?.name === targetType
        );

        if (!candidates.length) {
            this._pushAiMessage(`No ${targetType} node was found in the current workflow.`, { type: 'error' });
            return true;
        }

        if (candidates.length > 1) {
            this._pushAiMessage(`There are multiple ${targetType} nodes in this workflow. Please be more specific before I remove one.`, { type: 'error' });
            return true;
        }

        this.editor.removeNodeId(`node-${candidates[0].id}`);
        await new Promise((resolve) => setTimeout(resolve, 80));
        this._pushAiMessage(`✓ Removed ${targetType} from the current workflow.`);
        return true;
    }

    _getOutputChildren(node, flowData, outputClass = 'output_1') {
        const connections = node?.outputs?.[outputClass]?.connections || [];
        return connections.map((connection) => flowData[connection.node]).filter(Boolean);
    }

    _getAiUpdateContext() {
        const flowData = this.getCurrentFlowData();
        const nodes = Object.values(flowData || {});
        if (!nodes.length) return null;

        const modelNodes = nodes.filter((node) => node.data?.type === 'model');
        const triggerNodes = nodes.filter((node) => node.data?.type === 'action');

        if (modelNodes.length !== 1 || triggerNodes.length !== 1) {
            return {
                error: "AI update mode currently supports workflows with exactly one model node and one trigger node.",
            };
        }

        const modelNode = modelNodes[0];
        const triggerNode = triggerNodes[0];
        const branchChildren = this._getOutputChildren(triggerNode, flowData);
        const branchBlocks = branchChildren.filter((node) => ['Condition', 'Loop'].includes(node.data?.name));
        if (branchBlocks.length) {
            return {
                error: "AI update mode currently supports direct trigger-to-action workflows only. Condition/Loop branch editing is not enabled yet.",
            };
        }

        const existingActions = branchChildren
            .filter((node) => node.data?.type === 'action_to_do')
            .map((node) => node.data?.name)
            .filter(Boolean);

        const triggerLabelMap = {
            create: 'On Create',
            write: 'On Write',
            unlink: 'On Unlink',
        };

        return {
            mode: 'update',
            object: this.state.model_name || modelNode.data?.model?.[1] || '',
            trigger: triggerNode.data?.ttype || triggerLabelMap[triggerNode.data?.trigger_type] || 'On Write',
            existing_actions: existingActions,
            modelId: this.state.model_id,
            modelDisplayName: this.state.model,
            modelTechnicalName: this.state.model_name,
            parentDfId: triggerNode.id,
            parentNode: triggerNode,
            siblingNodes: branchChildren.filter((node) => node.data?.type === 'action_to_do'),
        };
    }

    _isGenericReusablePrompt(query) {
        const text = this._normalizeText(query);
        const hasGenericRecordLanguage =
            text.includes('a record') ||
            text.includes('any record') ||
            text.includes('when record') ||
            text.includes('when a record') ||
            text.includes('when any record');
        const modelKeywords = [
            'sale order', 'sales order', 'purchase order', 'invoice', 'bill',
            'contact', 'partner', 'product', 'employee', 'lead', 'task',
            'stock picking', 'manufacturing order', 'expense', 'leave',
            'time off', 'payslip', 'ticket',
        ];
        const mentionsSpecificModel = modelKeywords.some((keyword) => text.includes(keyword));
        return hasGenericRecordLanguage && !mentionsSpecificModel;
    }

    _getAiReusableCreateContext() {
        if (!this.state.isGenericReusable) return null;
        const flowData = this.getCurrentFlowData();
        const nodes = Object.values(flowData || {});
        const modelNodes = nodes.filter((node) => node.data?.type === 'model');
        if (modelNodes.length) return null;
        return {
            mode: 'reusable_create',
        };
    }

    _getCanvasScreenPoint(canvasX, canvasY) {
        const rect = this.editor.precanvas.getBoundingClientRect();
        return {
            x: canvasX * this.editor.zoom + rect.x,
            y: canvasY * this.editor.zoom + rect.y,
        };
    }

    _getAppendActionPosition(context, index) {
        const siblings = [...(context.siblingNodes || [])].sort((left, right) => {
            const topDiff = Number(left.pos_y || 0) - Number(right.pos_y || 0);
            return topDiff || (Number(left.pos_x || 0) - Number(right.pos_x || 0));
        });
        const lastSibling = siblings[siblings.length - 1];
        const baseX = Number(lastSibling?.pos_x ?? context.parentNode?.pos_x ?? 0);
        const baseY = Number(lastSibling?.pos_y ?? context.parentNode?.pos_y ?? 0);
        const desiredX = siblings.length ? baseX : baseX + 280;
        const desiredY = baseY + 180 + (index * 180);
        return this._getCanvasScreenPoint(desiredX, desiredY);
    }

    async _configureAiActionNode(actNodeId, nodeType, act, userQuery, context = {}) {
        if (!actNodeId) return;

        const actionContext = {
            modelName: context.modelTechnicalName,
            fieldDefs: context.fieldDefs || {},
        };

        if (nodeType === 'Mail') {
            actionContext.recipientSelection = this._resolveMailRecipientSelection(
                userQuery, act, context.modelTechnicalName, context.fieldDefs || {}
            );
        } else if (nodeType === 'SMS') {
            actionContext.recipientSelection = this._resolveSmsRecipientSelection(
                userQuery, act, context.modelTechnicalName, context.fieldDefs || {}
            );
        } else if (nodeType === 'Activity') {
            actionContext.resolvedActivityType = await this._resolveActivityType(act);
            actionContext.assigneeSelection = this._resolveActivityAssigneeSelection(
                userQuery, act, context.modelTechnicalName, context.fieldDefs || {}
            );
            actionContext.deadlineSelection = this._resolveActivityDeadlineSelection(userQuery, act);
        } else if (nodeType === 'Reuse Automation') {
            const resolved = await this._resolveReusableAutomationId(act);
            if (!resolved) {
                const searchName = act.reuse_automation_name || '(unknown)';
                this._pushAiMessage(
                    `Could not find a reusable workflow named "${searchName}". The node was added but its automation reference is empty.`,
                    { type: 'error' }
                );
            }
            actionContext.resolvedAutomation = resolved || null;
        }

        const nodeData = await this._buildActionNodeData(act, actionContext);
        if (nodeData) {
            await this.orm.write('node.struct', [actNodeId], nodeData);
        }
    }

    async _appendActionsToWorkflow(actions, context, userQuery) {
        const createdNodeDfIds = [];
        const fieldDefs = await this._getModelFieldDefs(context.modelTechnicalName);

        for (let i = 0; i < actions.length; i++) {
            const act = actions[i];
            const nodeType = act?.type || 'Warning';
            const pos = this._getAppendActionPosition(context, i);

            let result;
            try {
                result = await this._addNode(
                    nodeType,
                    pos.x,
                    pos.y,
                    context.modelDisplayName,
                    context.modelId,
                    null,
                    null
                );
            } catch (e) {
                console.warn(`Failed to append action node (${nodeType}):`, e);
                continue;
            }

            const { dfId: actDfId, nodeId: actNodeId } = result || {};
            if (actDfId) {
                createdNodeDfIds.push(actDfId);
                this._connectNodes(context.parentDfId, actDfId, 'output_1');
            }

            try {
                await this._configureAiActionNode(actNodeId, nodeType, act, userQuery, {
                    modelTechnicalName: context.modelTechnicalName,
                    fieldDefs,
                });
            } catch (e) {
                console.warn(`Could not save config for appended ${nodeType} node:`, e);
            }

            await new Promise((resolve) => setTimeout(resolve, 60));
        }

        if (createdNodeDfIds.length) {
            await this.autoSaveDrawFlow();
            this._focusAiWorkflow(createdNodeDfIds);
        }

        return createdNodeDfIds;
    }

    // Canvas helpers

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

    // Field definitions cache

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

    // Resolve a dotted field path to its final fieldDef
    // e.g. "order_line.product_uom_qty" on "sale.order"
    //   -> walks: sale.order.order_line (one2many -> sale.order.line)
    //          -> sale.order.line.product_uom_qty (float)
    //   -> returns { type: 'float', name: 'product_uom_qty',
    //                resModel: 'sale.order.line',
    //                fullPath: 'order_line.product_uom_qty' }

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

    // Activity type resolver

    async _resolveActivityType(act) {
        const typeName = (act.activity_type_name || '').trim();
        const aliases = {
            'phone call': ['Call', 'Phone Call', 'Phone'],
            'call': ['Call', 'Phone Call', 'Phone'],
            'phone': ['Call', 'Phone Call', 'Phone'],
            'email': ['Email'],
            'e-mail': ['Email'],
            'meeting': ['Meeting'],
            'to-do': ['To-Do', 'To Do', 'Todo'],
            'to do': ['To-Do', 'To Do', 'Todo'],
            'todo': ['To-Do', 'To Do', 'Todo'],
            'upload document': ['Upload Document', 'Document'],
            'document': ['Upload Document', 'Document'],
        };

        const trySearch = async (domain) => {
            try {
                const rows = await this.orm.searchRead(
                    'mail.activity.type', domain, ['id', 'name'], { limit: 1 }
                );
                return rows.length ? { id: rows[0].id, name: rows[0].name, display_name: rows[0].name } : null;
            } catch {
                return null;
            }
        };

        if (typeName) {
            const candidates = aliases[typeName.toLowerCase()] || [typeName];
            for (const candidate of candidates) {
                const exact = await trySearch([['name', '=', candidate]]);
                if (exact) return exact;
            }
            for (const candidate of candidates) {
                const ilike = await trySearch([['name', 'ilike', candidate]]);
                if (ilike) return ilike;
            }
        }

        const todo = await trySearch([['name', '=', 'To-Do']]);
        if (todo) return todo;
        const todoIlike = await trySearch([['name', 'ilike', 'to-do']]);
        if (todoIlike) return todoIlike;

        return await trySearch([]);
    }

    // Condition tree builder — handles both simple and dotted field paths

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

    // Selection / variable builders

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

    // Recipient / assignee / deadline resolvers

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

    // Node data builders (one per action type)

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

    // Reuse Automation resolver — finds the work.auto ID by name

    async _resolveReusableAutomationId(act) {
        const searchName = (act.reuse_automation_name || '').trim();
        if (!searchName) return null;

        const trySearch = async (domain) => {
            try {
                const rows = await this.orm.searchRead(
                    'work.auto',
                    domain,
                    ['id', 'name'],
                    { limit: 1 }
                );
                return rows.length ? rows[0] : null;
            } catch {
                return null;
            }
        };

        // 1. Exact name match among reusable (generic) automations
        let found = await trySearch([
            ['is_reusable', '=', true],
            ['reuse_scope', '=', 'generic'],
            ['active', '=', true],
            ['name', '=', searchName],
        ]);
        if (found) return found;

        // 2. Case-insensitive partial match
        found = await trySearch([
            ['is_reusable', '=', true],
            ['reuse_scope', '=', 'generic'],
            ['active', '=', true],
            ['name', 'ilike', searchName],
        ]);
        if (found) return found;

        // 3. Any reusable automation with that name (non-generic scope)
        found = await trySearch([
            ['is_reusable', '=', true],
            ['active', '=', true],
            ['name', 'ilike', searchName],
        ]);
        return found;
    }

    _buildReuseAutomationNodeData(act, resolvedAutomation) {
        return {
            label:                act.label || resolvedAutomation?.name || 'Reuse Automation',
            reused_work_auto_id:  resolvedAutomation ? resolvedAutomation.id : null,
            reused_variable:      null,
        };
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
            case 'Warning':           return this._buildWarningNodeData(act);
            case 'Mail':              return this._buildMailNodeData(act, context);
            case 'SMS':               return this._buildSmsNodeData(act, context);
            case 'Activity':          return this._buildActivityNodeData(act, context);
            case 'Write':             return this._buildWriteNodeData(act, context.modelName, context.fieldDefs || {});
            case 'Reuse Automation':  return this._buildReuseAutomationNodeData(act, context.resolvedAutomation || null);
            default:                  return act.label ? { label: act.label } : null;
        }
    }

    // Enter-key handler for the chat input

    onAiInputKeydown(ev) {
        if (ev.key === 'Enter' && !ev.shiftKey) {
            ev.preventDefault();
            this.sendAiMessage();
        }
    }

    // Main send handler

    async sendAiMessage() {
        const userQuery = (this.state.aiInput || '').trim();
        if (!userQuery || this.state.aiLoading) return;

        const userMsgId = _nextMsgId();
        this.state.aiMessages.push({ from: 'user', text: userQuery, id: userMsgId, type: 'info' });
        this.state.aiInput   = "";
        this.state.aiLoading = true;
        this._scrollChatToBottom();

        const genericReusableIntent = this._isGenericReusablePrompt(userQuery);
        if (genericReusableIntent && !this.state.isGenericReusable) {
            const flowData = this.getCurrentFlowData();
            const executableNodes = Object.values(flowData || {}).filter((node) => node.data?.type !== 'model');
            if (executableNodes.length) {
                this.state.aiLoading = false;
                this._pushAiMessage(
                    'This prompt looks like a reusable workflow request, but the current canvas already has workflow steps. Start from a clean workflow or enable Reusable before building.',
                    { type: 'error' }
                );
                return;
            }
            await this.toggleReusable();
            await new Promise((resolve) => setTimeout(resolve, 80));
        }

        if (this._isAiRemoveIntent(userQuery)) {
            this.state.aiLoading = false;
            await this._removeExistingActionNode(userQuery);
            return;
        }

        let aiData;
        const updateContext = this._isAiUpdateIntent(userQuery) ? this._getAiUpdateContext() : null;
        const reusableCreateContext = !updateContext ? this._getAiReusableCreateContext() : null;

        if (updateContext?.error) {
            this.state.aiLoading = false;
            this._pushAiMessage(updateContext.error, { type: 'error' });
            return;
        }

        try {
            // Call AI backend
            try {
                const aiContext = updateContext || reusableCreateContext || null;
                const result = await this.orm.call('chat.bot', 'my_python_method', [userQuery, aiContext]);
                aiData = typeof result === 'string' ? JSON.parse(result) : result;
            } catch (e) {
                console.error('AI call failed:', e);
                this._showAiError(e, "AI request failed. Please try again.");
                return;
            }

            // Validate AI response
            if (!aiData || typeof aiData !== "object") {
                this._showAiError(null, "The AI returned an invalid response. Please try again.");
                return;
            }
            if (aiData?.error) {
                this._showAiError([aiData.error, aiData.details, aiData.message].filter(Boolean).join(' — '), "The AI returned an error.");
                return;
            }

            if (!aiData?.actions?.length) {
                this._pushAiMessage('No actions were returned by the AI. Please rephrase your query.', { type: 'error' });
                return;
            }

            if (updateContext) {
                const createdNodeDfIds = await this._appendActionsToWorkflow(aiData.actions, updateContext, userQuery);
                if (!createdNodeDfIds.length) {
                    this._pushAiMessage('No new action nodes were appended. Please rephrase your request.', { type: 'error' });
                    return;
                }
                this._pushAiMessage(
                    `✓ Workflow updated: appended ${createdNodeDfIds.length} action${createdNodeDfIds.length > 1 ? 's' : ''} to ${updateContext.trigger} on ${updateContext.modelDisplayName}.`
                );
                return;
            }

            if (!reusableCreateContext && !aiData?.object) {
                this._pushAiMessage('No model was returned by the AI. Please rephrase your query.', { type: 'error' });
                return;
            }
            if (!aiData?.trigger) {
                this._pushAiMessage('No trigger was returned by the AI. Please rephrase your query.', { type: 'error' });
                return;
            }

            let modelId = this.state.model_id || null;
            let modelTechnicalName = this.state.model_name || '';
            let modelDisplayName = this.state.model || '';
            let modelFieldDefs = {};
            let modelDfId = null;
            const createdNodeDfIds = [];

            if (!reusableCreateContext) {
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

                modelId = res[0].id;
                modelTechnicalName = res[0].model;
                modelDisplayName = res[0].display_name;

                // Fetch field definitions
                modelFieldDefs = await this._getModelFieldDefs(modelTechnicalName);

                // Set up the primary model node
                try {
                    await this.onSelectPrimary([{ id: modelId, display_name: modelDisplayName, model: modelTechnicalName }]);
                } catch (e) {
                    this._pushAiMessage(`Failed to set up model node: ${e?.message || e}`, { type: 'error' });
                    return;
                }
                await new Promise(r => setTimeout(r, 150));

                const modelDfNode = Object.values(this.editor.drawflow.drawflow.Home.data)
                    .find(n => n.data.type === 'model');
                modelDfId = modelDfNode ? modelDfNode.id : null;
                if (modelDfId) createdNodeDfIds.push(modelDfId);
            }

            // Resolve trigger work.function
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

            // Add trigger node
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

            // Connect model → trigger
            if (modelDfId && triggerDfId) this._connectNodes(modelDfId, triggerDfId);
            await new Promise(r => setTimeout(r, 80));

            // Add Condition node
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

            // Add action nodes
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
                    } else if (nodeType === 'Reuse Automation') {
                        const resolved = await this._resolveReusableAutomationId(act);
                        if (!resolved) {
                            const searchName = act.reuse_automation_name || '(unknown)';
                            this._pushAiMessage(
                                `⚠ Could not find a reusable workflow named "${searchName}". ` +
                                `Make sure the automation exists, is marked as reusable, and is active. ` +
                                `The node was added but its automation reference is empty.`,
                                { type: 'error' }
                            );
                        }
                        actionContext.resolvedAutomation = resolved || null;
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

            // Success message
            const condCount = aiData.conditions?.length ?? 0;
            const actCount  = actions.length;
            const summary =
                `✓ Workflow built: ${aiData.trigger}` +
                (reusableCreateContext ? `` : ` on ${modelDisplayName}`) +
                (condCount ? ` → Condition (${condCount} rule${condCount > 1 ? 's' : ''})` : '') +
                ` → ${actCount} action${actCount !== 1 ? 's' : ''}.`;

            this._focusAiWorkflow(createdNodeDfIds);
            this._pushAiMessage(summary);

        } catch (e) {
            console.error('Unexpected AI workflow error:', e);
            this._showAiError(e, "Something went wrong while processing the AI response.");
        } finally {
            this.state.aiLoading = false;
        }
    }
}

WorkFlowAutoOverride.template = "client_action.automation_view";

registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });
