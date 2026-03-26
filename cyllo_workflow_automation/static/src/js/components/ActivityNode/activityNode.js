/** @odoo-module */
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";
import { getValueEditorInfo } from "@web/core/tree_editor/tree_editor_value_editors";
import { VariableSelector } from "../Assists/variableSelector/variableSelector"
import { FieldTypeDropdown } from "../Assists/fieldTypeDropdown/fieldTypeDropDown";
import { RecordPathSelector } from "../Assists/recordPathSelector/recordPathSelector";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
const { DateTime } = luxon;

export class ActivityNode extends ConfigurationBase {
    /**
     * ActivityNode class for handling configuration and logic related to activity nodes
     * in a workflow. It extends the ConfigurationBase class.
     */
    get getLabel() {
        return this.fieldState.label || ""
    }

    setLabel(ev) {
        this.fieldState.label = ev
        const label = ev
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId });
    }

    get getRecords() {
        let variables = []
        this.variables.forEach(variable => {
            ['record', 'recordset'].includes(variable.variable_type) && variable.modelId ? variables.push({
                value: variable.id,
                label: variable.variable_name
            }) : null
        })
        return variables
    }

    get getModel() {
        return this.fieldState.activity_record?.value || ""
    }

    updateObject(record) {
        this.fieldState.activity_record = this.getRecords.find((item) => item.value === record)
    }

    updateAssignee(value) {
        let mail_to = this.fieldState.activity_user || {}
        mail_to.value = value
        this.fieldState.activity_user = mail_to
    }
    /**
    * Retrieves component properties for specific fields like assignee or deadline.
    * @param {Object} info - Information object to extract properties from.
    * @param {String} field - The field type ('assignee' or 'deadline').
    * @returns {Object} - Extracted properties for the component.
    */

    getComponentProps(info, field) {
        const { value, update } = field === "assignee" ? {
            value: this.fieldState.activity_user?.value || false,
            update: (value) => this.updateAssignee(value)
        } : {
            value: this.getDeadline.value || false,
            update: (value) => this.updateDeadline(value)
        }
        return info.extractProps({ value, update })
    }

    /**
     * Retrieves variables for the given selection type and field type.
     * @param {String} selectionType - The selection type (e.g., 'variable', 'record').
     * @param {String} field - The field name ('assignee' or other).
     * @returns {Object} - Object containing variables and field information.
     */
    getVariablesField(selectionType, field) {
        let result;
        if (selectionType === 'variable') {
            result = {
                flVariables: field === "assignee" ? this.props.variables.filter(variable => variable.variable_type === 'record' && variable.modelName === "res.users") :
                    this.props.variables.filter(variable => variable.variable_type === 'date'),
                fieldInfo: field === "assignee" ? {
                    fieldDef: {
                        type: "many2one",
                        relation: "res.users",
                    }
                } : { fieldDef: { type: 'date' } }
            };
        } else if (selectionType === 'record') {
            result = {
                flVariables: this.props.variables.filter(variable => variable.variable_type === "record"),
                fieldInfo: field === "assignee" ? {
                    resModel: this.modelState.model['model'],
                    fieldDef: {
                        type: 'many2one',
                        relation: 'res.users',
                    }
                } : { fieldDef: { type: 'date' } }
            };
        } else {
            result = {
                fieldInfo: {
                    fieldDef: field === "assignee" ? {
                        type: "many2one",
                        relation: "res.users",
                    } : { type: 'date' }
                }
            };
        }
        return result
    }

    /**
     * Retrieves editor information based on the field type and selection type.
     * @param {Object} field - The field object.
     * @param {String} type - The field type ('assignee' or other).
     * @returns {Object} - Editor information for rendering the field.
     */
    getValueEditorInfo(field, type) {
        const selectionType = field.selectionType ? field.selectionType : ''
        const operator = '='
        const { flVariables, fieldInfo } = this.getVariablesField(selectionType, type)
        let editorValue = getValueEditorInfo(fieldInfo.fieldDef, operator);
        if (selectionType === "variable") {
            return {
                component: VariableSelector,
                extractProps: ({ value, update }) => {
                    return {
                        value,
                        update,
                        allVariable: true,
                        variables: flVariables
                    }
                }
            }
        } else if (selectionType === "record") {
            return {
                component: RecordPathSelector,
                extractProps: ({ value, update }) => {
                    return {
                        value,
                        update,
                        variables: flVariables,
                        fieldInfo,
                    }
                }
            }
        }
        return editorValue
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }

    toggleIncludeVariable(value, field) {
        if (field === 'user') {
            if (![value, undefined].includes(this.fieldState.activity_user.selectionType)) {
                this.fieldState.activity_user = { value: '', selectionType: value }
            } else this.fieldState.activity_user.selectionType = value;
        } else {
            if (![value, undefined].includes(this.fieldState.activity_deadline.selectionType)) {
                this.fieldState.activity_deadline = { value: false, selectionType: value }
            } else this.fieldState.activity_deadline.selectionType = value;
        }
    }

    get getDeadline() {
        !this.fieldState.activity_deadline ? this.fieldState.activity_deadline = {} : false
        return this.fieldState.activity_deadline
    }

    updateDeadline(value) {
        this.fieldState.activity_deadline.value = value
    }

    updateActivityType(ev) {
        this.fieldState.activity_type = ev[0]
    }

    setSummary(value) {
        this.fieldState.activity_summary = value
    }

    getUserId(activity_user) {
        if (activity_user.selectionType === "variable") {
            return `${activity_user.value.pathValue}.id`
        } else if (activity_user.selectionType === "record") {
            const record = this.props.variables.find((item) => item.id === activity_user.value.record)
            return `${record.variable_name}.${activity_user.value.pathValue}`
        }
        return `${activity_user.value}`
    }

    getDeadLineValue(activity_deadline) {
        if (activity_deadline.selectionType === "variable") {
            return `${activity_deadline.value.pathValue}`
        } else if (activity_deadline.selectionType === "record") {
            const record = this.props.variables.find((item) => item.id === activity_deadline.value.record)
            return `${record.variable_name}.${activity_deadline.value.pathValue}`
        }
        return `"${activity_deadline.value}"`
    }

    generateCode() {
        const { activity_type, activity_summary, activity_deadline, activity_user, activity_record } = this.fieldState
        const user_id = this.getUserId(activity_user)
        const deadline = this.getDeadLineValue(activity_deadline)
        const record = this.props.variables.find((variable) => variable.id === activity_record.value)
        let code = ''
        const recordExpr = activity_record.label;
        const scheduleArgs = `date_deadline = ${deadline},activity_type_id = ${activity_type.id},summary = """${activity_summary}""", user_id = ${user_id}`;
        const logCall = `_logger.warning('Activity node skipped: %s', exc)`;
        if (record.variable_type === 'record') {
            code = `
try:
    _act_target = ${recordExpr}
    _safe_schedule_activity(_act_target, ${scheduleArgs})
except Exception as exc:
    ${logCall}
`
        } else {
            code = `
try:
    _act_records = ${recordExpr}
    _safe_schedule_activity(_act_records, ${scheduleArgs})
except Exception as exc:
    ${logCall}
`
        }
        return code || "";
    }

    getValidationValue(field) {
        if (['variable', 'record'].includes(field.selectionType)) return field.value?.pathValue
        return field.value
    }

    validateForm() {
        const {
            activity_type,
            activity_summary,
            activity_deadline,
            activity_user,
            activity_record,
            label
        } = this.fieldState;
        // Validation rules
        const errors = {};
        const date = this.getValidationValue(activity_deadline)
        const user = this.getValidationValue(activity_user)
        // Validate label: must be a non-empty
        !label ? errors.label = "Label field must be a non-empty." : false
        //  Validate activity_record: must be a non-empty string
        !activity_record ? errors.activity_record = "Record must be a non-empty." : false
        // Validate activity_type: must not be a non-empty
        !activity_type ? errors.activity_type = "Activity Type must be a non-empty." : false
        // Validate activity_summary: must not be a non-empty
        !activity_summary ? errors.activity_summary = "Activity Summary must be a non-empty." : false
        // Validate activity_deadline: must not be a non-empty
        !date ? errors.activity_deadline = "Activity Deadline must be a non-empty." : false
        // Validate activity_user: must not be a non-empty
        !user ? errors.activity_user = "Activity User must be a non-empty." : false
        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }
        // If no errors, form is valid
        return { isValid: true };
    }
}

ActivityNode.template = "ActivityNode"
ActivityNode.components = { ...ConfigurationBase.components, CustomDropdown, FieldTypeDropdown, Many2XAutocomplete }
