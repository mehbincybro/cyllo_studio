/** @odoo-module */
import { Component, xml, useState, onWillStart, onMounted, useRef, onWillUnmount, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {
    conditionFields,
    warningFields,
    searchFields,
    createFields,
    writeFields,
    functionCallFields,
    variableFields,
    codeFields,
    mailFields,
    FollowerFields,
    smsFields,
    ActivityFields,
    MappedFields,
    AssignmentFields
} from "./fields";
import {
    icons,
 } from "./icons";
import { SearchNode } from "./components/searchNode/searchNode";
import { jsonrpc } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";
import { WarningNode } from "./components/warningNode/warningNode";
import { CreateNode } from "./components/createNode/createNode";
import { FunctionCallNode } from "./components/functionCallNode/functionCallNode";
import { CodeNode } from "./components/xCodeNode/codeNode";
import { WriteNode } from "./components/writeNode/writeNode";
import { MailNode } from "./components/mailNode/mailNode";
import { FollowerNode } from "./components/FollowerNode/followerNode";
import { SmsNode } from "./components/xsmsNode/smsNode";
import { ConditionNode } from "./components/xconditionNode/conditionNode";
import { ActivityNode } from "./components/ActivityNode/activityNode";
import {PYTHON_KEYWORDS} from "./components/Assists/utils/utils";
import { removeNodeIdFromVariables } from "./utils/utils"


const MODAL_CONFIGS = {
    'Warning': {
        component: WarningNode,
        fields: warningFields,
    },
    'Create': {
        component: CreateNode,
        fields: createFields,
    },
    'Write': {
        component: WriteNode,
        fields: writeFields,
    },
    'Button Click': {
        component: FunctionCallNode,
        fields: functionCallFields,
    },
    'Code': {
        component: CodeNode,
        fields: codeFields,
    },
    'Search':{
        component:SearchNode,
        fields:searchFields,
    },
    'Condition': {
        component: ConditionNode,
        fields: conditionFields,
    },
    'Mail': {
        component: MailNode,
        fields: mailFields,
    },
    'SMS': {
        component: SmsNode,
        fields: smsFields,
    },
    'Follower': {
        component: FollowerNode,
        fields: FollowerFields,
    },
    'Activity': {
        component: ActivityNode,
        fields: ActivityFields
    },
};

export class ModelComponent extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.root = useRef("root");
        this.notification = useService("notification");
        this.env.context.addEventListener("UPDATE-ME", this.updateMe.bind(this))
        this.env.bus.addEventListener("UPDT-PRIMARY", ({detail}) => {
            this.props.primary_model_id = detail.model_id
        });
        this.env.bus.addEventListener("UPDATE-VARIABLE-USAGE", ({detail: { variable, node}}) => {
            const updatedVariable = this.env.variables.context.variables.find(item => item.id === variable);
            !updatedVariable.usedIn.includes(node) && updatedVariable.usedIn.push(node);
            this.env.bus.trigger("UPDATE-VARIABLE-STATE");
        });
        this.env.bus.addEventListener("CHANGE-LABEL",({detail: {label,nodeId}}) => {
            if(this.props.nodeId === nodeId){
                this.state.label = label
            }
        })
        this.env.bus.addEventListener("OPEN:MODAL",({detail}) => {
            if (this.props.nodeId === detail.nodeId) {
                this.openConfigModal()
            }
        })
        this.env.bus.addEventListener("FIND:NODE:VARIABLE:USED",this.handleFindNodeVariableUsed.bind(this))
        this.env.bus.addEventListener("FLOW:VALIDATION", ({detail: { nodeIds }}) => {
            if (nodeIds.includes(this.props.nodeId)) {
                this.state.error = true;
            }
            setTimeout(() => {
                if (owl.status(this) !== "destroyed") {
                    this.state.error = false;
                }
            }, 5000)
        });
        this.state = useState({
            model: {},
            resId: 0,
            context: {},
            error: false,
            label: "",
            findUsage: false,
        })
        this.orm = useService("orm");
        onWillStart(this.manageNodeData);
        onMounted(async() => {
            const label = await this.orm.read("node.struct", [this.props.nodeId], ["label"])
            if (label && label[0]){
            this.state.label = label[0].label
            }
            this.state.context = this.context;
        })
        onWillUnmount(() => {
            this.env.bus.removeEventListener("FIND:NODE:VARIABLE:USED", this.handleFindNodeVariableUsed.bind(this));
        })
    }

    handleFindNodeVariableUsed = (event) => {
        const {detail} = event;
        const isCondition = this.props.name === "Condition";
        const parentDiv = this.getParentDiv();
        this.state.findUsage = false;
        this.toggleParentClass(parentDiv, false);
        if (this.props.nodeId === detail.nodeId) {
            if (isCondition) {
                this.toggleParentClass(parentDiv, true);
            } else {
                this.state.findUsage = true;
            }
            this.scheduleReset(parentDiv);
        }
    }
    getParentDiv() {
        return this.root.el?.offsetParent?.offsetParent;
    }
    toggleParentClass(parentDiv, add) {
        if (parentDiv) {
            parentDiv.classList[add ? 'add' : 'remove']('cy-find-usage');
        }
    }
    scheduleReset(parentDiv) {
        setTimeout(() => {
            if (owl.status(this) !== "destroyed") {
                this.state.findUsage = false;
                this.toggleParentClass(parentDiv, false);
            }
        }, 5000);
    }

    async nameGet() {
        const [resId, modelName] = this.props.model
        this.state.resId = resId
        return await this.orm.read(modelName, [resId], ["display_name"])
    }

    async manageNodeData() {
        if (this.props.model.length) {
            const data = await this.nameGet()
            this.state.model = data[0]
        }
        else {
            this.state.model.display_name = this.props.name;
        }
    }
    updateMe() {
        this.state.context = this.context;
    }

    get automationIdentifiers () {
        const allVariables = [...this.variableContext.variables, ...this.env.globalVariables.context.variables]
        const identifiers = allVariables.map(item => item.variable_name)
        return { pythonKeywords: [...PYTHON_KEYWORDS], variableNames: [...identifiers] };
    }
    async openConfigModal() {
        const modalConfig = MODAL_CONFIGS[this.props.name];
        if (modalConfig) {
            const { component, fields } = modalConfig;
            const props = {
                title: this.props.name,
                name: this.props.name,
                id: this.props.nodeId,
                fields,
                onConfirm: this.onConfirm.bind(this),
                updateImports: this.props.updateImports,
                position: "end",
                width: "65%",
                backdrop: true,
                identifiers: this.automationIdentifiers,
                variables: this.getVariables
            };
            if (this.props.name === 'Create') {
                props.primaryModelId = this.props.primary_model_id;
                props.trigger = this.triggerName()
                props.nodeName = this.props.name.toLowerCase()
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    this.updateVariable(fieldState);
                }
                props.display_name = "The Create Modal helps users effortlessly create records within the model using dynamic content."

            } else if (this.props.name === 'Write') {
                props.modelState = this.env.globalContext().modelState;
                props.modelName = this.env.globalContext().modelName;
                props.primaryModelId = this.props.primary_model_id;
                props.trigger = this.triggerName()
                props.nodeName = this.props.name.toLowerCase()
                props.display_name = "The Write Modal helps users to easily update and save values."
            } else if (this.props.name === 'Button Click') {
                const res_model = await this.orm.read('ir.model', [this.props.primary_model_id], ['model']);
                const functions = await this.fetchFunctions(res_model[0].model);
                props.resModel = res_model ? res_model[0].model : res_model[0].model;
                props.functions = functions;
                props.trigger = this.allTriggerName()
                props.display_name = "The Button Click Modal lets users quickly access and manage all button and cog menu functions."
            } else if(this.props.name === 'Code') {
                props.display_name = "The Code Modal provides an interface for users to write and execute Python code directly"
            } else if(this.props.name === 'Search') {
                const fields = searchFields.map(field => field.name);
                const searchFieldData = await this.orm.read('node.struct', [this.props.nodeId], fields)
                const modelIdToSearch = searchFieldData[0].model_id ? searchFieldData[0].model_id[0] : res_model[0].id;
                const [{ model: modelName }] = await this.orm.read('ir.model', [modelIdToSearch], ['model']);
                props.resModel = modelName ? modelName : res_model[0].model;
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    this.updateVariable(fieldState);
                }
                props.display_name = "The Search Modal helps users quickly find and retrieve specific nodes by using dynamic search criteria."
            } else if (this.props.name === "Condition") {
                const [{model: modelName}] = await this.orm.read('ir.model', [this.props.primary_model_id], ['model'])
                props.resModel = modelName ? modelName : res_model[0].model;
                props.display_name = "The Condition Modal lets users add and apply different conditions to customize and control functionality"
            } else if (this.props.name === "Mail") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Mail Modal provides an interface for users to compose and send emails easily"
            }
            else if(this.props.name === "SMS") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name= "The SMS Modal allows users to compose and send text messages efficiently."
            }else if (this.props.name === "Follower") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Followers Modal enables users to manage followers to records or entities"
            }
            else if (this.props.name === "Warning"){
                props.display_name = "The Warning Modal allows users to configure and display warning messages to alert users about important information"
            } else if (this.props.name === "Activity") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Activity Modal enables users to manage Activity"
            }
            this.dialogService.add(component, props);
        } else {
            // TODO: Handle unknown modal type
        }
    }

    async fetchFunctions(model) {
        return await jsonrpc('cyllo_auto_work/find/functions', {
            model,
        });
    }

    updateContext(code) {
        const context = this.context;
        const currentNode = context.nodes.find(node => node.nodeId === this.props.nodeId);
        currentNode.code = code;
        this.env.bus.trigger("UPDATE-CODE")
    }
    updateVariableUsage(usedVariables) {
        const nodeId = this.props.nodeId;
        const contextVariables = this.variableContext.variables;
        removeNodeIdFromVariables(contextVariables, nodeId)
        // Add nodeId to newly used variables
        Object.keys(usedVariables).forEach(varId => {
            const variable = contextVariables.find(v => v.id === varId);
            if (variable && variable.usedIn) {
                if (!variable.usedIn.includes(nodeId)) {
                    variable.usedIn.push(nodeId);
                }
            }
        });
    }

    updateVariable(fieldState) {
        const { model_id, search_variable } = fieldState;
            const variable = this.variableContext.variables.find(item => item.id === search_variable.id);
            if (variable) {
                variable.modelId = model_id;
                variable.variable_type = search_variable.variable_type;
                variable.variable_name = search_variable.variable_name;
            } else {
                this.env.variables.setContext({variables : [...this.variableContext.variables || [], owl.reactive({...search_variable,  scopeId: this.props.nodeId, class: this.buttonClass})]})
            }
        this.env.bus.trigger("UPDATE-VARIABLE-STATE");
    }

    async updateNode(fieldState, code) {
        await this.orm.call('node.struct', 'save_data', [this.props.nodeId, {...fieldState, code}]);
    }

    raiseNotification(text, type) {
        this.env.services.effect.add({
                title: "Success",
                message: _t(text),
                type: "notification_panel",
                notificationType: type,
            });
    }

    async onConfirm (fieldState, code, usedVariables) {
        this.updateContext(code)
        await this.updateNode(fieldState, code);
        this.updateVariableUsage(usedVariables)
        this.raiseNotification("Record Saved...!", "success");
    }

    triggerName(){
        const [, trigger_word] = this.env.globalContext().trigger.split(' ');
        return trigger_word?.toLowerCase();
    }

    allTriggerName(){
        const trigger_word = this.env.globalContext().trigger;
        return trigger_word?.toLowerCase();
    }

    deleteNode() {
        this.env.bus.trigger("DELETE:NODE:BY:CLICK", { nodeId: this.props.nodeId,});
    }

    get getVariables() {
        const getScopeIds = (node, nodeIds = [], visited = new Set()) => {
            if (!node || visited.has(node.nodeId)) return nodeIds;
            visited.add(node.nodeId);
            nodeIds.push(node.nodeId);
            if (node.left) {
                getScopeIds(node.left, nodeIds, visited);
            }
            return nodeIds;
        };

        const currentContext = this.context;
        const allVariables = this.variableContext.variables;
        let currentNode = currentContext.nodes.find(item => item.nodeId === this.props.nodeId);

        const scopeIds = getScopeIds(currentNode, []);
        const filteredVariables = allVariables.filter(variable => scopeIds.includes(variable.scopeId));

        return [...this.env.globalVariables.context.variables, ...filteredVariables];
    }

    get context() {
        return this.env.context.context;
    }
    getIconSrc() {
        if (this.props.type !== 'action'){
             if (this.props.type == 'model'){
                    return icons['Model']
                }
            const displayName = this.state.model.display_name;
            return icons[displayName] || '';
        }

        else{
            return icons['Action']
        }
    }
    get variableContext() {
        return this.env.variables.context;
    }

    static template = xml`
        <div t-ref="root" t-attf-class="node-container {{this.state.findUsage ? 'cy-find-usage' : ''}}" style="position: relative">
            <t t-if="this.state.label">
                <div class="cy-w-info-node">
                    <span class="">
                        <t t-out="this.state.label"/>
                    </span>
                </div>
            </t>
            <div class="title-box d-flex align-items-center justify-content-center p-2 position-relative">
                 <span class="w-auto-node-icon">
                 <img t-att-src="getIconSrc()" draggable="false"/>

                 </span>
                <t t-if="state.model.display_name === 'Condition'">
                    Condition
                </t>
                <t t-else="">
                    <t t-out="state.model.display_name"/>
                </t>
                <span
                    t-if="props.type === 'action_to_do'"
                    class="settings-icon"
                    t-on-click="openConfigModal"
                >
                    <i class="ri-edit-2-fill"></i>
                </span>
                <div class="delete-icon position-absolute" t-on-click="deleteNode">
                    <i class="ri-close-line delete-icon" aria-hidden="true"></i>
                </div>
            </div>
            <div t-attf-class="cy-validation-tooltip {{this.state.error ? 'show' : ''}}">
                <span class="tooltip-text">
                    Not configured!
                </span>
            </div>
            <t t-if="state.model.display_name === 'Condition'">
                <div class="condition-tooltip-container">
                    <span>Success</span>
                    <span>Failed</span>
                    <span>Default</span>
                </div>
            </t>
        </div>`;
}
