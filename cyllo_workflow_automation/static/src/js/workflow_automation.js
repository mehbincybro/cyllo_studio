/** @odoo-module */
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
const { useState, onWillStart, Component, onMounted, useRef, mount, useEffect, onWillUnmount } = owl;
import { useSaveContext } from './useSaveContext'
import { ModelComponent } from "./workflow_nodes";
import { Record } from "@web/model/record";
import Context from "./context";
import { variableFields } from "./fields.js";
import { VariableNode } from "./components/variableNode/variableNode.js";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationPopup } from "@cyllo_web/js/popups/popups";
import { PYTHON_KEYWORDS } from "./components/Assists/utils/utils";
import { FoldOut } from "./automationComponents/FoldOut/FoldOut";
import { VariableItem } from "./automationComponents/VariableItem/VariableItem";
import { VariableDetails } from "./automationComponents/VariableDetails/VariableDetails";
import { removeNodeIdFromVariables, settingInitialContext } from "./utils/utils"
import { CustomTrigger } from "./components/customTriggers/customTriggers";
import { WorkPager } from "./components/Assists/workPager/workPager";
import { SaveLoading } from "./components/Assists/effect/saveLoading/saveLoading";
import { HistoryManager } from "./utils/historyManager";
import { cloneState } from "./utils/stateClone";

const BUTTON_CLASSES = [
    'btn-info', 'btn-primary', 'btn-warning', 'btn-secondary', 'btn-success', 'btn-danger'
]

const GLOBAL_IMPORTS = [{
    "childStatement": [
        {
            "statement": "fields"
        }
    ],
    "importStatement": "from odoo import"
}, {
    "childStatement": [
        {
            "statement": "request"
        }
    ],
    "importStatement": "from odoo.http import"
}]

function errorVibration() {
    if ('vibrate' in navigator) {
        // Try to vibrate
        navigator.vibrate([100, 50, 100]);
        // Check if vibration actually occurred
        setTimeout(() => {
            if (navigator.vibrate && !navigator.vibrate(0)) {
            } else {
                // fallbackVibration();
            }
        }, 300);
    } else {
        // fallbackVibration();
    }
}

function playErrorSound() {
    return new Promise((resolve) => {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        // Use a triangle wave for a softer but still distinctive sound
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(440, audioCtx.currentTime); // Start at A4

        // Reduce the gain for lower volume
        gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.start();

        // Subtle frequency modulation
        oscillator.frequency.exponentialRampToValueAtTime(330, audioCtx.currentTime + 0.2); // Drop to E4
        oscillator.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.4); // Back to A4

        setTimeout(() => {
            oscillator.stop();
            resolve();
        }, 500);
    });
}


export class WorkFlowAuto extends Component {

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.action = useService("action");
        this.uiService = useService("ui");
        this.data = {};
        owl.useSubEnv({
            globalContext: this.getContext.bind(this),
            context: new Context({}),
            variables: new Context({}),
            globalVariables: new Context({
                variables: [
                    owl.reactive({
                        id: "global/variable/current/rec",
                        variable_name: "current_record",
                        variable_value: "records",
                        variable_type: "record"
                    }),
                    owl.reactive({
                        id: "global/variable/workflow/stack",
                        variable_name: "__workflow_stack__",
                        variable_value: "[]",
                        variable_type: "list"
                    }),
                ]
            })
        })


        this.env.bus.addEventListener("UPDATE-CODE", this.updateCode.bind(this));
        this.env.bus.addEventListener("UPDATE-VARIABLE-STATE", () => {
            this.state.variables = [...this.env.variables.context.variables]
        });

        this.env.bus.addEventListener("DELETE:NODE:BY:CLICK", ({ detail }) => {
            const data = this.editorValue[0].flow_data?.drawflow?.Home?.data
            if (data) {
                const node = Object.values(data).find(item => item.data.nodeId === detail.nodeId)
                owl.status(this) !== 'destroyed' && this.deleteNode(node);
            }
        });

        this.state = useState({
            actions: [],
            model_id: 0,
            model: '',
            secondary_model: "",
            sec_model_id: "",
            nodeDetails: [],
            modelState: [],
            selectedNodeID: undefined,
            variables: [],
            code: "",
            imports: [],
            block: true,
            modelSelectable: false,
            trigger: "",
            other_blk: false,
            name: "",
            nameError: false,
            selectedVariable: undefined,
            customTrigger: false,
            recordList: [],
            saveLoading: false,
            // Cron schedule fields (used when trigger is time-based)
            cronMode: '',
            cronTime: 0,
            cronDay: 1,
            cronMonth: 1,
            triggerType: "",
            // Field change fields (used when trigger is field_change)
            watchedFieldId: false,
            watchedFieldName: "",
            canUndo: false,
            canRedo: false,
        })

        this.history = new HistoryManager(100);
        this.isRestoring = false;

        this.initialLoad = true;
        const { id } = useSaveContext();
        this.id = id;
        this.editorState = useState({
            value: []
        });
        this.drawBoardState = useState({
            edit: true,
        });
        this.mainBtn = useRef("mainBtn");
        this.root = useRef("root");
        this.drawBoard = useRef("drawBoard");
        this.inputNameRef = useRef("inputNameRef")
        this.mainBlk = useRef("mainBlk");

        useEffect((value) => {
            if (value) {
                !this.initialLoad && this.write({
                    variables: this.getSerializableVariables(),
                    imports: this.getSerializableImports()
                });
                this.initialLoad = false;
            }
        }, () => [this.state.variables, this.imports]);

        useEffect((modelId) => {
            const cur_rec = this.env.globalVariables.context.variables.find(item => item.variable_name === "current_record")
            cur_rec.modelId = this.state.model_id;
            cur_rec.modelName = this.state.model_name;
        }, () => [this.state.model_id, this.state.model_name])

        useEffect((nodeId) => {
            this.state.block = true;
            if (nodeId) {
                if (this.currentNode.data.type === "action_to_do") this.state.block = false;
            }
        }, () => [this.state.selectedNodeID])

        useEffect(() => {
            this.env.bus.trigger("TOGGLE_NAVBAR:HIDE", { show: false })
            return () => {
                this.env.bus.trigger("TOGGLE_NAVBAR:HIDE", { show: true })
            }
        });

        onWillStart(async () => {
            this.state.recordList = await this.orm.search("work.auto", [])
            this.state.actions = await this.orm.searchRead('work.function', [], ['name', 'id', 'icon', 'model_id', 'func_name', 'trigger_type'])
            const recordId = this.id;
            if (recordId) {
                const data = await this.orm.read('work.auto', [recordId], ['name', 'variables', 'imports', 'code', 'trigger_type']);
                if (data.length > 0) {
                    let [{ name, variables, imports, code, trigger_type }] = data

                    imports = imports || GLOBAL_IMPORTS

                    this.state.variables = variables ? variables : [];
                    this.state.name = name;
                    this.state.imports = [...imports];
                    this.state.code = code;
                    this.state.triggerType = trigger_type || "";
                    this.env.variables.setContext({ variables: [...this.state.variables] });
                }
            } else {
                this.state.imports = [...GLOBAL_IMPORTS];
            }
            await this.loadData();
            await this.setModelState();
            await settingInitialContext.call(this);

            if (this.editorState.value.length > 0 && this.editorState.value[0].flow_data) {
                Object.entries(this.editorState.value[0].flow_data.drawflow?.Home?.data || {}).forEach(([key, value]) => {
                    if (value.data.ttype) {
                        this.state.trigger = value.data.ttype
                    }
                    if (value.data.trigger_type) {
                        this.state.triggerType = value.data.trigger_type;
                    }
                });
            }

            if (recordId) {
                // Load cron schedule fields so the inline panel shows existing values
                const cronData = await this.orm.read('work.auto', [recordId],
                    ['time_trigger_mode', 'time_trigger_time', 'time_trigger_day', 'time_trigger_month']);
                if (cronData.length) {
                    const { time_trigger_mode, time_trigger_time, time_trigger_day, time_trigger_month } = cronData[0];
                    this.state.cronMode = time_trigger_mode || '';
                    this.state.cronTime = time_trigger_time || 0;
                    this.state.cronDay = time_trigger_day || 1;
                    this.state.cronMonth = time_trigger_month || 1;
                }

                // Load watched field for field_change workflows
                const fieldChangeData = await this.orm.read('work.auto', [recordId], ['field_id']);
                if (fieldChangeData.length && fieldChangeData[0].field_id) {
                    const [id, name] = fieldChangeData[0].field_id;
                    this.state.watchedFieldId = id;
                    this.state.watchedFieldName = name;
                }
            }

            this.env.bus.trigger("onclickMenuBar", { isCollapse: true })
            window.addEventListener('keydown', this.onKeyDown.bind(this));
        });

        onWillUnmount(() => {
            window.removeEventListener('keydown', this.onKeyDown.bind(this));
        });

        onMounted(async () => {
            const globalVariables = await this.getGlobalVariables()
            this.env.globalVariables.setContext({ variables: [...this.env.globalVariables.context.variables, ...globalVariables] });
            this.inputNameRef.el.focus();
            this.uiService.block();
            setTimeout(() => {
                if (owl.status(this) !== "destroyed") {
                    this.uiService.unblock()
                }
            }, 1000);

            const preRender = (component, props, options) => {
                return {
                    component, props, options
                };
            };

            const renderFunc = (obj, ref) => {
                const { component, props, options } = obj;
                this.state.nodeDetails.push({ ...obj, ref });
                this.data = { ...obj, ref };
            };
            const owlC = { version: 3, h: preRender, render: renderFunc };
            this.editor = new Drawflow(this.drawBoard.el, owlC);

            this.editor.contextmenu = (e) => {
                if (
                    this.editor.dispatch("contextmenu", e),
                    e.preventDefault(),
                    "fixed" === this.editor.editor_mode || "view" === this.editor.editor_mode
                ) {
                    return false;
                }

                if (this.editor.precanvas.getElementsByClassName("drawflow-delete").length) {
                    this.editor.precanvas.getElementsByClassName("drawflow-delete")[0].remove();
                }

                if (this.editor.connection_selected && this.editor.connection_selected.parentElement.classList.length > 1) {
                    const deleteDiv = document.createElement("div");
                    deleteDiv.classList.add("drawflow-delete", "ri-delete-bin-6-line");
                    // deleteDiv.innerHTML = "x";
                    const precanvasRect = this.editor.precanvas.getBoundingClientRect();
                    const precanvasHeight = this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom);
                    const precanvasWidth = this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom);

                    deleteDiv.style.top = `${e.clientY * precanvasHeight - precanvasRect.y * precanvasHeight}px`;
                    deleteDiv.style.left = `${e.clientX * precanvasWidth - precanvasRect.x * precanvasWidth}px`;
                    this.editor.precanvas.appendChild(deleteDiv);
                }

            }

            this.isRestoring = true;
            try {
                if (this.editorState.value[0] && this.editorState.value[0].flow_data) {
                    this.registerNodes();
                    this.editor.start();
                    this.manageData();

                    // Critical: Initialize history with the loaded state directly from the database
                    // to ensure S0 (initial state) is never empty or corrupted.
                    const initialState = cloneState({
                        drawflow: this.editorState.value[0].flow_data,
                        variables: this.state.variables,
                        context: this.env.context.context,
                        imports: this.state.imports,
                    });
                    this.history.init(initialState);
                } else {
                    this.editor.start();
                    this.history.init(this.getHistorySnapshot());
                }
                this.updateHistoryState();
            } finally {
                this.isRestoring = false;
            }

            this.editor.on('nodeRemoved', async (id) => {
                this.state.selectedNodeID = undefined;
                const flowData = this.editor.drawflow.drawflow.Home.data;
                const node = Object.values(flowData).find(node => node.id === +id)
                if (node) {
                    this.env.context.deleteNode(node.data.nodeId);
                    this.removeVariables(node.data.nodeId);
                    this.removeImports(node.data.nodeId)
                    this.removeNodeIdFromVariables(node.data.nodeId);
                }
                this.saveHistory();
                if (node) {
                    await this.orm.unlink("node.struct", [node.data.nodeId]);
                }
                await this.autoSaveDrawFlow();
            });

            this.editor.on('nodeCreated', async (id) => {
                this.contextUpdateNodeCreation(id);
                this.saveHistory();
                await this.autoSaveDrawFlow();
            });

            this.editor.on('nodeMoved', async (id) => {
                this.saveHistoryDebounced();
                if (this.moveDbTimeout) clearTimeout(this.moveDbTimeout);
                this.moveDbTimeout = setTimeout(async () => {
                    await this.autoSaveDrawFlow();
                }, 1000);
            });
            this.editor.on('connectionCreated', async (data) => {
                const { input_class, input_id, output_class, output_id } = data;
                const inputId = +input_id;
                const outputId = +output_id;
                if (!this.canConnect(inputId, outputId, output_class)) {
                    this.editor.removeSingleConnection(outputId, inputId, output_class, input_class, true);
                    return;
                }
                this.contextUpdateConnection(data, true);
                this.saveHistory();
                await this.autoSaveDrawFlow();
                const node = Object.values(this.editor.drawflow.drawflow.Home.data).filter(item => item.id === parseInt(input_id))
                const name = node[0].data.name
                const nodeId = node[0].data.nodeId
                this.env.bus.trigger("OPEN:MODAL", { name, nodeId });
            });

            this.editor.on('connectionRemoved', async (data) => {
                this.contextUpdateConnection(data, false)
                this.saveHistory();
                await this.autoSaveDrawFlow();
            });

            this.editor.on('nodeSelected', (id) => {
                this.state.selectedNodeID = id;
            });

            this.editor.on('nodeUnselected', (val) => {
                this.state.selectedNodeID = undefined
            });

            this.editor.on('keydown', (e) => {
                if (e.key === "Delete") {
                    if (this.currentNode) {
                        this.deleteNode(this.currentNode);
                    }
                }
            });

        })
    }

    removeNodeIdFromVariables(nodeId) {
        const contextVariables = this.env.variables.context.variables
        removeNodeIdFromVariables(contextVariables, nodeId);
    }

    async getGlobalVariables() {
        const models = ["res.users", "res.company"]
        const modelData = await this.orm.searchRead("ir.model", [["model", "in", models]], ["model"])
        const variables = modelData.map(item => {
            if (item.model === "res.users") {
                return {
                    id: "global/variable/current/user",
                    variable_name: "current_user",
                    modelId: item.id,
                    modelName: item.model,
                    variable_type: "record",
                    variable_value: "env.user"
                }
            } else if (item.model === "res.company") {
                return {
                    id: "global/variable/current/company",
                    variable_name: "current_company",
                    modelId: item.id,
                    modelName: item.model,
                    variable_type: "record",
                    variable_value: "env.company"
                }
            }
        })
        const dateVars = [
            {
                id: "global/variable/current/date",
                variable_name: "current_date",
                variable_type: "date",
                variable_value: "fields.date.today()"
            },
            {
                id: "global/variable/current/datetime",
                variable_name: "current_datetime",
                variable_type: "datetime",
                variable_value: "fields.Datetime.now()"
            },
        ]
        return [...variables, ...dateVars];
    }

    get recordList() {
        return this.state.recordList
    }

    get currentRecord() {
        return this.id
    }

    /** True when the active trigger fires on a field-value change. */
    get isFieldChangeTrigger() {
        return this.state.triggerType === 'field_change';
    }

    /**
     * True when the active trigger is time-based.
     * Used by the XML template to hide Create/Write blocks and show the
     * inline Cron Schedule configuration panel.
     */
    get isTimeTrigger() {
        return this.state.triggerType === 'time';
    }

    get model_blk() {
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const modelNode = Object.values(flowData).find(node => node.data?.type === "model");
        return !modelNode;
    }

    get trigger_blk() {
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const actionNode = Object.values(flowData).find(node => node.data?.type === "action");
        const modelNode = Object.values(flowData).find(node => node.data?.type === "model");
        return !!modelNode && !actionNode;
    }

    get other_blk() {
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const actionNode = Object.values(flowData).find(node => node.data?.type === "action");
        return !!actionNode;
    }

    /**
     * Write a single cron schedule field to work.auto and keep the local
     * state in sync.  The backend write() override calls create_cron()
     * automatically, so no extra RPC is needed.
     *
     * @param {string} field  – one of: time_trigger_mode/time/day/month
     * @param {*}      value  – the new value
     */
    async setCronField(field, value) {
        const stateKey = {
            time_trigger_mode: 'cronMode',
            time_trigger_time: 'cronTime',
            time_trigger_day: 'cronDay',
            time_trigger_month: 'cronMonth',
        }[field];
        if (stateKey) this.state[stateKey] = value;
        await this.orm.write('work.auto', [this.id], { [field]: value });
    }

    /**
     * Saves the selected watched field to work.auto.
     * `current_record` in the global variables context already represents the
     * triggering record, so no extra variable registration is needed.
     *
     * @param {number} fieldId   – id of the selected ir.model.fields record
     * @param {string} fieldName – user-visible field name / label
     */
    async setWatchedField(fieldId, fieldName) {
        this.state.watchedFieldId = fieldId || false;
        this.state.watchedFieldName = fieldName || "";
        await this.orm.write('work.auto', [this.id], { field_id: fieldId || false });
    }

    deleteNode(node) {
        const variablesInScope = this.env.variables.context.variables.filter(variable => variable.scopeId === node.data.nodeId);
        const isUsed = variablesInScope.some(item =>
            item.usedIn.length > 1 || (item.usedIn.length === 1 && item.usedIn[0] !== node.data.nodeId)
        );
        if (isUsed) {
            const message = "You can't delete the node. Because the variables with in this scope is used in some other nodes.";
            this.dialogService.add(ConfirmationPopup, {
                title: "Oops!", message: message,
                confirmText: "Ok, Got it", showCancel: false,
                image: "cyllo_workflow_automation/static/src/img/warning_popup.png"
            });
            return
        }

        const dialogConfigs = {
            'model': {
                body: _t("While deleting this node, All the nodes will be Removed"),
                onConfirm: async () => {
                    await this.resetStatesWhenClear();
                }
            },
            'action': {
                body: _t("Do you want to delete the node. The variables with in this scope is also deleted."),
                onConfirm: async () => {
                    this.editor.removeNodeId(`node-${node.id}`);
                    this.state.trigger_blk = true;
                    this.state.other_blk = false;
                    this.state.trigger = ""
                }
            },
            'default': {
                body: _t("Do you want to delete the node. The variables with in this scope is also deleted."),
                onConfirm: async () => {
                    this.editor.removeNodeId(`node-${node.id}`);
                }
            }
        };
        const config = dialogConfigs[node.data.type] || dialogConfigs.default;
        this.dialogService.add(ConfirmationPopup, {
            title: "Confirm Action", message: config.body, confirmText: "Yes, proceed",
            cancelText: "No, cancel", onConfirm: config.onConfirm, onCancel: () => {
            },
            lottie: true, lottiePath: "cyllo_workflow_automation/static/src/img/lottie-warning.json",
        });
    }

    async clearModelNodeData(node) {
        this.editor.clearModuleSelected();
        this.orm.call('work.auto', 'clear_all_nodes', [this.id]);
        this.env.variables.setContext({ variables: [] });
        this.env.context.setContext({ nodes: [] });
        Object.assign(this.state, {
            variables: [], code: "", imports: [], model_blk: true,
            trigger_blk: false, other_blk: false, model: "", model_id: false,
        });
    }

    canConnect(inputId, outputId, outputClass) {
        const flowNodes = Object.values(this.editorValue[0].flow_data.drawflow.Home.data);
        const outPutNode = flowNodes.find(node => node.id === outputId);
        const inPutNode = flowNodes.find(node => node.id === inputId);
        if (!outPutNode || !inPutNode) {
            return false;
        }
        if ((outPutNode.data.type === "model" && inPutNode.data.type !== "action") || (inPutNode.data.type === "action" && outPutNode.data.type !== "model")) {
            return false
        }
        const hasOutputConnection = outputClass === "output_1" ?
            (outPutNode.outputs?.output_1?.connections.length > 0) : outputClass === "output_2" ? (outPutNode.outputs?.output_2?.connections.length > 0) : (outPutNode.outputs?.output_3?.connections.length > 0)
        const hasInputConnection =
            (inPutNode.inputs?.input_1?.connections.length > 0)
        return !hasOutputConnection && !hasInputConnection;
    }

    selectTab(value) {
        this.state.block = value === 'block';
    }

    contextUpdateNodeCreation(id) {
        const flowData = this.editor.drawflow.drawflow.Home.data;
        const flowNodes = Object.values(flowData)
        const createdNode = flowNodes.find(node => node.id === id);
        if (!createdNode) return;
        const nodeId = createdNode.data.nodeId;
        const isParent = createdNode.name === "Condition" || createdNode.name === "Loop"
        //TODO: Handle Context
        const currentContext = this.env.context.context
        const nodes = currentContext?.nodes || []
        const isLoop = createdNode.name === "Loop";
        this.env.context.setContext({
            nodes: [...nodes, {
                nodeId,
                parent: null,
                left: null,
                right: null,
                child1: isParent ? { left: null, right: null, code: "pass" } : null,
                child2: null,
                isParent,
                isLoop,
                code: ""
            }]
        })
    }

    contextUpdateConnection(data, creation) {
        // TODO: Handle Context
        const { output_id, input_id } = data;
        const flowData = this.editor.drawflow.drawflow.Home.data;
        const nodes = Object.values(flowData)
        const inputNode = nodes.find(node => node.id == input_id)
        const outputNode = nodes.find(node => node.id == output_id)
        if (!inputNode || !outputNode) return;
        const currentContext = this.env.context.context
        const context_input_node = currentContext.nodes.find(node => node.nodeId === inputNode.data.nodeId)
        const context_output_node = currentContext.nodes.find(node => node.nodeId === outputNode.data.nodeId)
        context_input_node.left = creation ? context_output_node : null
        if (context_output_node.isParent) {
            const conditionNode = nodes.find(item => item.data.nodeId === context_output_node.nodeId);
            const child1 = conditionNode.outputs.output_1;
            const child2 = conditionNode.outputs.output_2;
            const right = conditionNode.outputs.output_3;
            if (child1.connections.length > 0 && child1.connections[0].node == inputNode.id) {
                const childId = child1.connections[0].node
                const childNode = nodes.find(item => item.id == childId);
                const ctxNode = currentContext.nodes.find(item => item.nodeId == childNode.data?.nodeId);
                context_output_node.child1 = creation ? ctxNode : { left: null, right: null, code: "pass" }
            }
            if (child2.connections.length > 0 && child2.connections[0].node == inputNode.id) {
                const childId = child2.connections[0].node
                const childNode = nodes.find(item => item.id == childId);
                const ctxNode = currentContext.nodes.find(item => item.nodeId == childNode.data?.nodeId);
                context_output_node.child2 = creation ? ctxNode : null
            }
            if (right.connections.length > 0 && right.connections[0].node == inputNode.id) {
                const childId = right.connections[0].node
                const childNode = nodes.find(item => item.id == childId);
                const ctxNode = currentContext.nodes.find(item => item.nodeId == childNode.data?.nodeId);
                context_output_node.right = creation ? ctxNode : null
            }
        } else context_output_node.right = creation ? context_input_node : null
    }

    registerNodes() {
        Object.values(this.editorState.value[0].flow_data?.drawflow?.Home?.data).forEach(item => {
            const uniqueIdentifier = item.name + '__' + item.data.nodeId
            this.editor.registerNode(uniqueIdentifier, ModelComponent, item.data, {});
        })
    }

    async onClickNewRule() {
        const rule = await this.orm.create("work.auto", [{ 'name': 'Automation rule' }])
        const action = {
            type: "ir.actions.client",
            tag: "automation_view",
            context: {
                id: rule[0]
            }
        }
        const message = _t("You are already in a new record")
        this.deleteEmptyRecord(action, message)
    }

    onClickMenuBar() {
        this.env.bus.trigger('onclickMenuBar')
    }

    async setModelState() {
        if (!this.id) return;
        const data = await this.orm.read("work.auto", [this.id], ['model_id']);
        if (data.length > 0) {
            const modelData = data[0].model_id;
            if (modelData) {
                const model_res = await this.orm.read("ir.model", [modelData[0]], ['model']);
                if (model_res.length > 0) {
                    this.state.model_id = modelData[0];
                    this.state.model = modelData[1];
                    this.state.model_name = model_res[0].model;
                }
            }
        }
    }

    get editorValue() {
        return this.editorState.value
    }

    get buttonClass() {
        const randomNumber = Math.floor(Math.random() * 7);
        return BUTTON_CLASSES[randomNumber];
    }

    get titleAccessibleVariables() {
        if (!this.currentNode || this.currentNode?.data.model.length > 0) return ""
        return "Accessible Variables " + this.currentNode.name
    }

    get globalVariablesContext() {
        return this.env.globalVariables.context.variables || []
    }

    get accessibleVariables() {
        if (!this.state.selectedNodeID) return [];
        const getAllLeftNodeIds = (node, nodeIds = [], visited = new Set()) => {
            if (!node || visited.has(node.nodeId)) return nodeIds;
            visited.add(node.nodeId);
            nodeIds.push(node.nodeId);
            return getAllLeftNodeIds(node.left, nodeIds, visited);
        };
        const currentNodeId = this.currentNode?.data?.nodeId;
        const currentContext = this.env.context.context || {};
        const allVariables = this.env.variables.context.variables || [];
        const contextNodes = currentContext.nodes || [];
        let selectedNode = contextNodes.find(
            item => item.nodeId === currentNodeId
        );
        const scopeIds = getAllLeftNodeIds(selectedNode);
        const filteredVariables = allVariables || [];
        const accessibleVariables = filteredVariables.filter(variable =>
            scopeIds.includes(variable.scopeId)
        );
        return accessibleVariables;
    }

    manageData() {
        if (this.editorValue.length && this.editorValue[0].flow_data) {
            this.importData(this.editorValue[0].flow_data)
            this.state.nodeDetails.forEach(node => {
                const { component, props, ref } = node;
                if (!ref || !ref.isConnected) {
                    return;
                }
                props.updateImports = this.updateImportStatements.bind(this);
                this.mountComponent(component, ref, props);
            })
        }
    }

    async loadData() {
        if (this.id) {
            this.editorState.value = await this.orm.read('work.auto', [this.id]);
            if (this.editorState.value[0] && this.editorState.value[0].flow_data.drawflow) {
                // No longer needed to set block states here as they are now reactive getters
            }
        } else {
            this.editorState.value = await this.orm.searchRead('work.auto', [], [], { limit: 1 })
        }
    }

    importData(data) {
        this.editor.import(data)
    }

    zoomOut() {
        this.editor.zoom_out();
    }

    zoomReset() {
        this.editor.zoom_reset();
    }

    zoomIn() {
        this.editor.zoom_in();
    }

    changeMode() {
        this.drawBoardState.edit = !this.drawBoardState.edit;
        this.editor.editor_mode = this.drawBoardState.edit ? 'edit' : 'fixed';
        this.env.services.effect.add({
            message: this.drawBoardState.edit ? "Unlocked!" : 'Locked!',
            locked: true,
            type: "save_confetti",
        });
    }

    async clearModuleSelected() {
        this.dialogService.add(ConfirmationPopup, {
            title: _t("Are you sure"),
            message: _t("Are you sure you want to clear? All the nodes will be deleted permanently."),
            confirmText: _t("Yes, proceed"),
            cancelText: _t("No, cancel"),
            onConfirm: this.resetStatesWhenClear.bind(this),
            onCancel: () => {
            },
            lottie: true,
            lottiePath: "cyllo_workflow_automation/static/src/img/delete-lottie.json",
        });
    }

    async resetStatesWhenClear() {
        this.orm.call('work.auto', 'clear_all_nodes', [this.id]);
        this.env.variables.setContext({ variables: [] });
        this.env.context.setContext({ nodes: [] });
        this.editor.clearModuleSelected();
        this.autoSaveDrawFlow().then(() => {
            Object.assign(this.state, {
                variables: [],
                code: "",
                imports: GLOBAL_IMPORTS,
                model: "",
                model_id: false,
                selectedNodeID: undefined,
            });
        });
    }

    changeModule(module) {
        this.editor
    }

    extractBackendInfo() {
        const { data: mainData } = this.editor.drawflow.drawflow.Home
        const model_data = Object.values(mainData).find(({ data }) => data?.type === "model")
        const action_data = Object.values(mainData).find(({ data }) => data?.type === "action")
        let backendData = { code: this.state.code, variables: this.state.variables }
        if (model_data) {
            backendData = {
                ...backendData,
                model_id: model_data.data.model[0]
            }
        }
        if (action_data) {
            backendData = {
                ...backendData,
                function_id: action_data.data.model[0]
            }
        }
        return backendData
    }

    getHistorySnapshot() {
        const snapshot = {
            drawflow: this.editor.export(),
            variables: this.state.variables,
            context: this.env.context.context,
            imports: this.state.imports,
        };
        return cloneState(snapshot);
    }

    saveHistory() {
        if (this.isRestoring) return;
        this.history.save(this.getHistorySnapshot());
        this.updateHistoryState();
    }

    saveHistoryDebounced() {
        if (this.isRestoring) return;
        if (this.moveTimeout) clearTimeout(this.moveTimeout);
        this.moveTimeout = setTimeout(() => {
            this.saveHistory();
        }, 300);
    }

    undo() {
        if (this.history.canUndo()) {
            const state = this.history.undo();
            this.restoreHistoryState(state);
        }
    }

    redo() {
        if (this.history.canRedo()) {
            const state = this.history.redo();
            this.restoreHistoryState(state);
        }
    }

    restoreHistoryState(snapshot) {
        if (!snapshot || !snapshot.drawflow) {
            console.error("Attempted to restore invalid history state:", snapshot);
            return;
        }
        this.isRestoring = true;
        try {
            const { drawflow, variables, context, imports } = snapshot;
            this.editor.import(drawflow);
            if (this.editorState.value[0]) {
                this.editorState.value[0].flow_data = drawflow;
            }

            this.state.variables = variables;
            this.env.variables.setContext({ variables: [...variables] });

            this.env.context.setContext(context);

            this.state.imports = imports;

            this.state.nodeDetails = [];
            this.registerNodes();
            this.manageData();
            this.updateHistoryState();
            this.autoSaveDrawFlow();
            this.updateCode();
        } finally {
            this.isRestoring = false;
        }
        // Since we imported, we might need to re-register nodes or fix Owl components
        // Drawflow import usually reconstructs the HTML but the Owl components need to be alive.
        // In this implementation, the components are managed via state.nodeDetails
        // and registerNode. Re-importing might require some orchestration if Owl components
        // get destroyed. However, Drawflow OWL integration often handles this.
    }

    updateHistoryState() {
        this.state.canUndo = this.history.canUndo();
        this.state.canRedo = this.history.canRedo();
    }

    onKeyDown(e) {
        if (e.ctrlKey || e.metaKey) {
            const key = e.key.toLowerCase();
            if (key === 'y') {
                e.preventDefault();
                this.redo();
            } else if (key === 'z') {
                e.preventDefault();
                this.undo();
            }
        }
    }

    get automationIdentifiers() {
        const identifiers = this.env.variables.context.variables.map(item => item.variable_name)
        return { pythonKeywords: [...PYTHON_KEYWORDS], variableNames: [...identifiers] };
    }

    async onSave() {
        const { isValid, error, nodeIds } = this.validateFlow();
        const nameValidation = this.validateName();
        if (!isValid || !nameValidation.isValid) {
            this.handleValidationErrors(isValid, nameValidation, nodeIds, error);
            return;
        }
        try {
            this.state.saveLoading = true
            await this.saveData();
            this.state.saveLoading = false
            this.showSuccessMessage();
        } catch (error) {
            this.showErrorMessage(error);
        }
    }

    get saveClass() {
        return this.state.model ? 'btn btn-primary' : 'btn btn-secondary'
    }

    validateName() {
        const name = this.state.name.trim();
        return {
            isValid: name !== "" && name !== "Automation rule",
            error: 'Add the correct name'
        };
    }

    handleValidationErrors(isFlowValid, nameValidation, nodeIds, err) {
        if (!isFlowValid && nodeIds) {
            this.env.bus.trigger("FLOW:VALIDATION", { nodeIds });
        }
        if (!nameValidation.isValid) {
            this.showNameError();
        }
        const errorMessage = [nameValidation.error, err].filter(Boolean).join(", ");
        this.showErrorMessage(errorMessage);
    }

    showNameError() {
        this.inputNameRef.el.focus();
        this.state.nameError = true;
        setTimeout(() => {
            if (owl.status(this) !== "destroyed") this.state.nameError = false;
        }, 5000);
    }

    onCreateTrigger() {
        this.state.customTrigger = true
    }

    async saveData() {
        this.updateCode();
        const data = this.editor.export();
        const newData = this.extractBackendInfo();
        // newData.image = await this.generateImage();
        const ttype = Object.values(data.drawflow.Home.data).some(item => item.data.ttype == 'On Unlink')
        await this.orm.call('work.auto', 'save_data', [this.id, data, this.state.name, ttype], newData);
    }

    showSuccessMessage() {
        this.env.services.effect.add({
            message: "Great job! Record saved.",
            type: "save_confetti",
        });
    }

    showErrorMessage(error) {
        this.env.services.effect.add({
            title: "Flow validation failed",
            message: "Unable to save the record.",
            description: error,
            type: "notification_panel",
            notificationType: "error",
        });
        errorVibration();
    }

    updateName(newName) {
        this.state.name = newName;
        // You might also want to save this to the server here
    }

    validateFlow() {
        const validationArray = [];
        const nodes = this.env.context?.context?.nodes || [];

        if (nodes.length === 0) {
            return { isValid: false, error: "Please create a workflow" };
        }

        const flow = this.editorValue?.[0]?.flow_data?.drawflow?.Home;
        if (!flow || !flow.data) {
            console.error("Flow data is missing in editorValue:", this.editorValue);
            return { isValid: false, error: "Flow data not found" };
        }

        const { data } = flow;

        for (const node of nodes) {
            const nodeData = Object.values(data).find(
                (item) => item.data.nodeId === node.nodeId
            );

            if (!nodeData) {
                console.warn(`Skipping node ${node.nodeId}, not found in flow data`);
                continue; // prevents crash if node was deleted or not synced
            }

            // Validation: check if node requires configuration
            if (!node.code) {
                if (["action", "model"].includes(nodeData.data.type)) {
                    continue; // skip types that don’t need validation
                }
                validationArray.push([nodeData.data.name, nodeData.data.nodeId]);
            }
        }

        if (validationArray.length > 0) {
            const errors = validationArray.map((item) => item[0]);
            const nodeIds = validationArray.map((item) => item[1]);
            const errorMessage =
                errors.length === 1
                    ? `${errors[0]} is not configured`
                    : `${errors.slice(0, -1).join(", ")} and ${errors[errors.length - 1]
                    } are not configured`;

            return { isValid: false, nodeIds, error: errorMessage };
        }

        return { isValid: true, error: "" };
    }

    get Image() {
        return this.state.image
    }

    setImage(image) {
        this.state.image = image
    }

    getRecordId() {
        const id = Number(this.id);
        return Number.isInteger(id) && id > 0 ? id : null;
    }

    write(data) {
        const recordId = this.getRecordId();
        if (!recordId) {
            return;
        }
        owl.status(this) !== 'destroyed' && this.orm.write("work.auto", [recordId], data);
    }

    removeImports(nodeId) {
        for (const imps of this.imports) {
            imps.childStatement = imps.childStatement.filter(item => item.nodeId !== nodeId);
        }
        this.updateCode();
    }

    updateImportStatements(statement) {
        const { parent, child, nodeId } = statement;
        const statementObj = this.imports.find(item => item.importStatement === parent);
        if (statementObj) {
            const childObject = statementObj.childStatement.find(item => item.nodeId === nodeId)
            if (!childObject) {
                statementObj.childStatement.push({ statement: child, nodeId: nodeId });
                this.state.imports = [...this.imports]
            } else {
                childObject.statement = child;
            }
        } else {
            this.state.imports = [...this.imports, {
                importStatement: parent,
                childStatement: [{ statement: child, nodeId: nodeId }]
            }]
        }
    }

    triggerFileInput(actionId) {
        document.getElementById(`file-input-${actionId}`).click();
    }

    handleFileUpload(event, actionId) {
        const file = event.target.files[0];
        if (file && file.type === 'image/svg+xml') {
            const reader = new FileReader();
            reader.onload = (e) => {
                const action = this.state.actions.find(a => a.id === actionId);
                if (action) {
                    action.customIcon = e.target.result;
                    this.render(); // Trigger a re-render to show the new icon
                }
            };
            reader.readAsDataURL(file);
        } else {
            // Handle invalid file type
            alert('Please upload an SVG file.');
        }
    }

    get importStateMent() {
        let importStatements = "";
        for (let statement of this.imports) {
            const childStatements = statement.childStatement.map(item => {
                return item.statement;
            });
            const statementSet = new Set(childStatements.filter(Boolean))
            if (statement.childStatement.length > 0) {
                importStatements += `${statement.importStatement} ${Array.from(statementSet).join(', ')}\n`
            }
        }
        return importStatements;
    }

    get imports() {
        return this.state.imports || [];
    }

    updateCode() {
        let node = structuredClone(this.env.context.context?.nodes)[0];
        const variables = this.env.variables.context.variables;
        const globalVariables = this.env.globalVariables.context.variables;
        while (node?.left) {
            node = node.left
        }
        let codeLines = [];
        let indentationLevel = "";
        let parentArray = [];
        for (const variable of globalVariables) {
            if (variable.variable_name === 'current_record') {
                codeLines.push(`${variable.variable_name} = records if 'records' in globals() else env['${this.state.model_name}'].browse()`);
            } else {
                codeLines.push(`${variable.variable_name} = ${variable.variable_value}`);
            }
        }
        while (node) {
            const variablesInScope = variables.filter(item => item.scopeId === node.nodeId);

            for (const item of variablesInScope) {
                if (!item.code) continue;
                codeLines.push(`${indentationLevel}${item.code}`);
            }
            if (node.code) {
                const lines = node.code.split('\n');
                for (const line of lines) {
                    codeLines.push(`${indentationLevel}${line}`);
                }
            }

            if (node.isParent) {
                parentArray.push(node);
                indentationLevel += "    ";
                node = node.child1;
                continue;
            }
            if (!node.right) {
                const pNode = parentArray.pop();
                if (!pNode?.child2 && !pNode?.right) break;
                const condition = pNode?.child2 ? pNode?.child2.completed : pNode.right
                if (condition) {
                    indentationLevel = indentationLevel.slice(0, -4);
                    node = pNode?.right;
                } else if (pNode.isLoop) {
                    // Loop ended: no else block. De-indent and move on.
                    indentationLevel = indentationLevel.slice(0, -4);
                    node = pNode?.right;
                } else {
                    node = pNode?.child2;
                    pNode.child2.completed = true;
                    parentArray.push(pNode);
                    indentationLevel = indentationLevel.slice(0, -4);
                    if (pNode.else_setup_code) {
                        // Cron-mode condition: emit the complement recordset search and open
                        // a new independent `if` block so both branches always execute.
                        codeLines.push(`${indentationLevel}${pNode.else_setup_code}`);
                        const complementVar = pNode.else_setup_code.split('=')[0].trim();
                        codeLines.push(`${indentationLevel}if ${complementVar}:`);
                    } else {
                        // Standard condition: only one branch executes.
                        codeLines.push(`${indentationLevel}else:`);
                    }
                    indentationLevel += "    ";
                }

                continue;
            }
            node = node.right;
        }
        const combinedCode = codeLines.join('\n');
        const imports = this.importStateMent;
        this.state.code = imports + "\n" + combinedCode;
    }

    showCode() {
        this.state.showCode = true;
    }

    async autoSaveDrawFlow(values) {
        const flow_data = this.editor.export();
        this.editorState.value[0].flow_data = flow_data
        await this.write({ flow_data });
    }

    dragStart(event, type) {
        if (event.type === "touchstart") {
            const mobile_item_selec = event.target.closest(".drag-drawflow").getAttribute('data-node');
        } else {
            event.dataTransfer.setData("record", this.state.model_id);
            event.dataTransfer.setData("action", event.target.getAttribute('data-action'));
            event.dataTransfer.setData("node", event.target.getAttribute('data-node'));
            event.dataTransfer.setData("type", event.target.getAttribute('data-type'));
            event.dataTransfer.setData("trigger_type", event.target.getAttribute('data-trigger_type'));
        }
    }

    allowDrop(ev) {
        ev.preventDefault();
    }

    mountComponent(component, ref, props) {
        mount(component, ref, { props, env: this.env })
    }

    getContext() {
        return {
            modelName: this.state.model_name,
            modelState: this.state.modelState,
            trigger: this.state.trigger,
            // Exposes trigger type (e.g. 'time') so child components such as
            // the Condition node can adapt their UI for cron-mode workflows.
            triggerType: this.state.triggerType,
        }
    }

    get scope() {
        try {
            const scopeId = this.state.selectedVariable.scopeId
            const data = this.editorValue[0].flow_data?.drawflow?.Home?.data;
            const node = Object.values(data).find(item => item.data.nodeId === scopeId);
            return node || null
        } catch (e) {
            //TODO: handle error;
        }
    }

    get customTriggerProps() {
        const props = {
            back: this.resetCustomTrigger.bind(this),
            model: this.state.model_id,
            updateActions: this.updateActions.bind(this),
            triggers: this.state.actions
        }
        return props
    }

    resetCustomTrigger() {
        this.state.customTrigger = false
    }

    async updateActions() {
        this.state.actions = await this.orm.searchRead('work.function', [], ['name', 'id', 'icon', 'model_id', 'func_name', 'trigger_type'])
    }

    onCronFieldChange(field, ev, type = 'string') {
        let value = ev.target.value;
        if (type === 'float') value = parseFloat(value) || 0;
        if (type === 'int') value = parseInt(value) || 0;
        this.setCronField(field, value);
    }

    get variableDetailProps() {
        const props = {
            variable: this.state.selectedVariable,
            back: this.resetVariableSelection.bind(this),
            edit: this.editVariable.bind(this),
            delete: this.deleteVariable.bind(this),
            usedNodes: this.usedNodes
        }
        const scope = this.scope
        if (scope) props['scope'] = scope
        return props
    }

    get usedNodes() {
        const nodeIds = this.state.selectedVariable?.usedIn;
        if (nodeIds && nodeIds.length > 0) {
            const { data } = this.editorValue[0].flow_data.drawflow.Home;
            const nodes = Object.values(data).filter(item => nodeIds.includes(item.data.nodeId));
            return nodes;
        }
        return [];
    }

    get currentNode() {
        const { data } = this.editorValue[0].flow_data.drawflow.Home;
        const nodes = Object.values(data);
        return nodes.find(node => node.id == this.state.selectedNodeID);
    }

    get globalWithAccessibleVariables() {
        return [...this.globalVariables, ...this.accessibleVariables,]
    }

    get globalVariables() {
        return this.env.globalVariables.context.variables;
    }

    makeVariable() {
        if (!this.currentNode || this.currentNode?.data.model.length > 0) {
            const message = !this.currentNode ? "You can't create a variable without selecting any block." : "You cant create a variable for model and trigger block.";
            this.dialogService.add(ConfirmationPopup, {
                title: "Oops!",
                message: message,
                confirmText: "Ok, Got it",
                showCancel: false,
                image: "cyllo_workflow_automation/static/src/img/warning_popup.png"
            });

        } else {
            this.dialogService.add(VariableNode, {
                name: "Make Variable",
                fields: variableFields,
                variable: { scopeId: this.currentNode.data.nodeId },
                display_name: "Here you can create new variables. Name for this Variable that's unique within this automation.",
                variables: this.globalWithAccessibleVariables,
                identifiers: this.automationIdentifiers,
                onConfirm: (fieldState, code) => {
                    const currentVariableContext = this.env.variables.context;
                    const variables = currentVariableContext.variables || []
                    this.env.variables.setContext({
                        variables: [...variables, owl.reactive({
                            id: new Date().toISOString(),
                            modelId: undefined,
                            scopeId: this.currentNode.data.nodeId, ...fieldState,
                            class: this.buttonClass,
                            code,
                            usedIn: [],
                            delete: true,
                        })]
                    })
                    this.setVariableState(this.env.variables.context.variables);
                    this.saveHistory();
                }
            })
        }
    }

    editVariable(variable) {
        const { variable_name, variable_type, type, variable_value, scopeId } = variable
        const { data } = this.editorValue[0].flow_data.drawflow.Home;
        const nodes = Object.values(data);
        this.state.selectedNodeID = nodes.find(nod => nod.data.nodeId === scopeId).id;
        this.dialogService.add(VariableNode, {
            name: "Edit Variable",
            mode: "edit",
            variables: this.globalWithAccessibleVariables,
            display_name: "Here you can edit variables. Name for this Variable that's unique within this automation.",
            variable: { variable_name, variable_type, type, variable_value, scopeId },
            identifiers: this.automationIdentifiers,
            onConfirm: (fieldState, code) => {
                const currentVariableContext = this.env.variables.context;
                const variables = currentVariableContext.variables;
                const editedVariable = variables.find(item => item.id === variable.id);
                Object.assign(editedVariable, { ...fieldState, code })
                this.setVariableState(variables);
                this.saveHistory();
            }
        })
        this.state.selectedNodeID = undefined;
    }

    deleteVariable(variable) {
        //FiXME: WWW
        if (variable.usedIn.length > 0) {
            this.dialogService.add(ConfirmationPopup, {
                title: "Oops!",
                message: "Used variable. Clear dependencies before deleting.",
                confirmText: "Ok, Got it",
                showCancel: false,
                image: "cyllo_workflow_automation/static/src/img/warning_popup.png"
            });
        } else {
            const variables = this.state.variables.filter(item => item.id !== variable.id);
            this.setVariableState(variables)
            this.env.variables.setContext({ variables: [...variables] })
            this.saveHistory();
        }
    }

    selectVariable(variable) {
        this.state.selectedVariable = variable;
    }

    resetVariableSelection() {
        this.state.selectedVariable = undefined;
    }

    setVariableState(variables) {
        this.state.variables = [...variables]
    }

    removeVariables(nodeID) {
        const variables = this.state.variables.filter(item => item.scopeId !== nodeID);
        this.setVariableState(variables);
        this.env.variables.setContext({ variables: [...variables] })
    }

    getSerializableVariables() {
        const variables = this.state.variables || [];
        return variables.map(variable => ({ ...variable }));
    }

    getSerializableImports() {
        return this.imports.map(statement => ({
            importStatement: statement.importStatement,
            childStatement: (statement.childStatement || []).map(child => ({ ...child })),
        }));
    }

    async addNodeToDrawFlow(name, pos_x, pos_y, selectedValue, record, action, type, trigger_type) {
        if (this.editor.editor_mode === 'fixed') return false;
        // Calculate position
        pos_x = pos_x * (this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom)) - (this.editor.precanvas.getBoundingClientRect().x * (this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom)));
        pos_y = pos_y * (this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom)) - (this.editor.precanvas.getBoundingClientRect().y * (this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom)));
        // Create node in backend
        const nodeId = await this.createNodeInBackend(name, type);
        const cur_rec = this.env.globalVariables.context.variables.find(item => item.variable_name === "current_record")
        // Define common properties
        const commonProps = {
            name,
            nodeId,
            model: [],
            primary_model_id: this.state.model_id,
            primary_model_name: this.state.model_name,
            updateImports: this.updateImportStatements.bind(this),
            work_auto_id: this.id,
        };
        this.env.bus.trigger("UPDT-PRIMARY", { model_id: this.state.model_id })
        let specificProps = {};
        let label = name;
        let left = 1;
        let right = 1;
        switch (name) {
            case 'model':
                specificProps.type = name;
                specificProps.model = [parseInt(record), 'ir.model'];
                label = `model_${record} model_rec`;
                left = 0;
                cur_rec.modelId = this.state.model_id;
                cur_rec.modelName = this.state.model_name;
                break;
            case 'Search':
            case 'Create':
            case 'Write':
            case 'Filter':
            case 'Iteration':
            case 'Date':
            case 'Button Click':
            case 'Code':
            case 'Function Args':
            case 'Mail':
            case 'SMS':
            case 'Activity':
            case 'Follower':
            case 'Mapped':
            case 'Assignment':
                specificProps.type = "action_to_do";
                break;
            case 'Warning':
                specificProps.type = "action_to_do";
                left = 1;
                right = 0;
                break;
            case 'Condition':
            case 'Loop':
                specificProps.type = "action_to_do";
                right = 3;
                break;
            case 'Reuse Automation':
                specificProps.type = "action_to_do";
                break;
            default:
                specificProps.type = "action";
                specificProps.ttype = name;
                specificProps.trigger_type = trigger_type;
                specificProps.model = [parseInt(action), "work.function"];
                label = action;
                break;
        }

        // Merge specific properties with common properties
        const newProps = { ...commonProps, ...specificProps };
        const uniqueIdentifier = name + '__' + nodeId

        // Register node
        this.editor.registerNode(uniqueIdentifier, ModelComponent, newProps, {});

        // Add node to editor
        await this.editor.addNode(name, left, right, pos_x, pos_y, label, { ...newProps }, uniqueIdentifier, 3);

        // Update component
        let { component, ref, props } = this.data
        props = { ...props, ...newProps };
        this.mountComponent(component, ref, props);
    }

    drop(ev) {
        if (ev.type === "touchend") {
            var parentdrawflow = document.elementFromPoint(mobile_last_move.touches[0].clientX, mobile_last_move.touches[0].clientY).closest("#drawflow");
            if (parentdrawflow != null) {
                this.addNodeToDrawFlow(mobile_item_selec, mobile_last_move.touches[0].clientX, mobile_last_move.touches[0].clientY);
            }
            let mobile_item_selec = '';
        } else {
            ev.preventDefault();
            let data = ev.dataTransfer.getData("node");
            let record = ev.dataTransfer.getData("record");
            let action = ev.dataTransfer.getData("action");
            const type = ev.dataTransfer.getData("type");
            const trigger_type = ev.dataTransfer.getData("trigger_type");
            if (data && data !== 'null') {
                if (type === 'trigger') {
                    this.state.trigger = data;
                    this.state.triggerType = trigger_type;
                }
                this.mainBlk.el.querySelector("#trigger_blocks").classList.remove('show')
                const selectedValue = this.state.model;
                this.addNodeToDrawFlow(data, ev.clientX, ev.clientY, selectedValue, record, action, type, trigger_type);
            }
        }
    }

    async createNodeInBackend(name, type) {
        type = type === "null" ? "node" : type;
        const [id] = await this.orm.create(
            "node.struct",
            [
                {
                    name,
                    work_auto_id: this.id,
                    model_id: this.state.model_id,
                    type,
                },
            ],
        );
        return id;
    }

    async onSelectPrimary(ev) {
        if (!ev) return;
        // const model_data = await this.orm.read('ir.model', [ev[0].id], ['display_name', 'model']);
        const model_data = await this.orm.searchRead('ir.model', [["id", "=", ev[0].id]], ['display_name', 'model'])
        this.state.model = ev[0].display_name ? ev[0].display_name : model_data[0].display_name;
        this.state.model_id = ev[0].id;
        this.state.model_name = model_data[0].model;
        this.settingModelState(ev[0].id);
        await this.updatePrimaryModel(ev[0].id);
        const name = "model"
        const action = null
        const precanvasRect = this.editor.precanvas.getBoundingClientRect();
        const defaultX = precanvasRect.left + precanvasRect.width / 35;
        const defaultY = precanvasRect.top + precanvasRect.height / 5 - 8;
        this.addNodeToDrawFlow(name, defaultX, defaultY, this.state.model, this.state.model_id, action, "model")
    }

    updatePrimaryModel(model_id) {
        this.orm.write("work.auto", [this.id], { model_id });
    }

    settingModelState(model_id) {
        const modelState = this.state.modelState.filter(model => model.type !== 'primary')
        this.state.modelState = [{ id: 0, model_id, type: 'primary' }, ...modelState]
    }

    getDomain() {
        return []
    }

    async deleteEmpty() {
        if (!this.env.context.context.nodes.length) {
            await this.orm.unlink("work.auto", [this.id])
        }
    }
    deleteEmptyRecord(action, message) {
        if (!this.env.context.context.nodes.length) {
            this.dialogService.add(ConfirmationPopup, {
                title: _t("Are you sure"),
                message: message || _t("If you leave this page,This empty record will be deleted"),
                confirmText: _t("Yes, proceed"),
                cancelText: _t("No, cancel"),
                onConfirm: async () => {
                    await this.orm.unlink("work.auto", [this.id])
                    this.action.doAction(action)
                },
                onCancel: () => {
                },
            })
        } else {
            this.action.doAction(action)
        }
    }

    async navigatePage(navigateId) {
        const action = {
            type: "ir.actions.client",
            tag: "automation_view",
            context: {
                id: navigateId
            }
        }
        this.deleteEmptyRecord(action)

    }

    async handleClickBack(e) {
        e.preventDefault()
        // const domain = !this.env.context.context.nodes.length ? [['id', '!=', this.id]] : [];
        const action = {
            type: "ir.actions.act_window",
            res_model: "work.auto",
            views: [[false, "workflowCard"], [false, "list"], [false, "form"]],
            target: "main",
            name: "Workflow Automation",
            // domain,
            context: { delete_node_id: !this.env.context.context.nodes.length ? this.id : false }
        }
        const message = _t("If you go back, This record will be deleted");
        this.deleteEmptyRecord(action, message)
    }

    static components = {
        Many2XAutocomplete,
        Many2OneField,
        Record,
        VariableNode,
        Many2ManyTagsField,
        FoldOut,
        VariableItem,
        VariableDetails,
        CustomTrigger,
        WorkPager,
        SaveLoading
    }
}

WorkFlowAuto.template = "client_action.automation_view"
registry.category("actions").add("automation_view", WorkFlowAuto)
