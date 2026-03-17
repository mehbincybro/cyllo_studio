/** @odoo-module **/
import { useState } from "@odoo/owl";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";

export class ReusableAutomationNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.state = useState({
            automationOptions: [],
            automationMetadata: {},
        });
    }

    async fetchData() {
        await super.fetchData();
        await this.loadAutomations();
    }

    async loadAutomations() {
        const domain = [
            ['active', '=', true],
            ['is_reusable', '=', true],
            ['trigger_function_ids', '!=', false],
        ];
        if (this.props.primary_model_id) {
            domain.push(['model_id', '=', this.props.primary_model_id]);
        }
        if (this.props.work_auto_id) {
            domain.push(['id', '!=', this.props.work_auto_id]);
        }
        const records = await this.orm.searchRead('work.auto', domain, ['id', 'name', 'model_id']);
        const options = records.map(rec => {
            const modelName = rec.model_id?.[1] || '';
            return {
                value: rec.id,
                label: modelName ? `${rec.name} (${modelName})` : rec.name,
                model: modelName,
            };
        });
        const metadata = {};
        options.forEach(option => {
            metadata[option.value] = option;
        });
        this.state.automationOptions = options;
        this.state.automationMetadata = metadata;
    }

    get automationDropdownOptions() {
        return this.state.automationOptions;
    }

    get selectedAutomationModel() {
        const metadata = this.state.automationMetadata[this.fieldState.reused_work_auto_id];
        return metadata?.model || '';
    }

    get recordVariableOptions() {
        return this.variables
            .filter(variable => ['record', 'recordset'].includes(variable.variable_type))
            .map(variable => ({
                value: variable.id,
                label: `${variable.variable_name} (${variable.variable_type})`,
                variable,
            }));
    }

    onSelectAutomation(value) {
        this.fieldState.reused_work_auto_id = value;
        const metadata = this.state.automationMetadata[value];
        if (metadata) {
            const label = metadata.label;
            if (!this.fieldState?.label) {
                this.setLabel(label);
            }
        }
    }

    onSelectVariable(value) {
        const option = this.recordVariableOptions.find(opt => opt.value === value);
        if (option) {
            this.fieldState.reused_variable = option.variable;
            this.updateUsedVariables(option.variable.id);
        } else {
            this.fieldState.reused_variable = null;
        }
    }

    setLabel(value) {
        this.fieldState.label = value;
        this.env.bus.trigger("CHANGE-LABEL", { label: value, nodeId: this.props.id });
    }

    generateCode() {
        const automationId = this.fieldState.reused_work_auto_id;
        const variable = this.fieldState.reused_variable;
        if (!automationId || !variable) {
            return "";
        }
        this.props.updateImports({
            parent: 'import logging\n_logger = logging.getLogger(__name__)',
            child: '',
            nodeId: this.props.id,
        });
        const parentId = Number(this.props.work_auto_id || 0);
        const stackLines = parentId > 0 ? [`    cy_w_stack.append(${parentId})`] : [];
        const recordsExpr = this.getRecordsExpression(variable);
        const lines = [
            'try:',
            '    cy_w_stack = list(__workflow_stack__)',
            ...stackLines,
            `    env["work.auto"].browse(${automationId})._process({`,
            `        'records': ${recordsExpr},`,
            `        '__workflow_stack__': cy_w_stack,`,
            '    })',
            'except Exception as e:',
            `    _logger.error("Reusable automation node ${this.props.id} failed: %s", e)`
        ];
        return lines.join('\n');
    }

    getRecordsExpression(variable) {
        if (variable.variable_type === 'recordset') {
            return variable.variable_name;
        }
        const modelName = variable.modelName || this.props.primary_model_name;
        if (modelName) {
            return `env['${modelName}'].browse(${variable.variable_name}.id)`;
        }
        return variable.variable_name;
    }
}

ReusableAutomationNode.components = {
    ...ConfigurationBase.components,
    CustomDropdown,
};
ReusableAutomationNode.template = "ReusableAutomationNode";
