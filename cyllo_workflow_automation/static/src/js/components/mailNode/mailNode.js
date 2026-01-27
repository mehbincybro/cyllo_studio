/** @odoo-module */
const {useState, onWillStart, useEffect} = owl;
import {_t} from "@web/core/l10n/translation";
import {Record} from "@web/model/record";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {Select, Input} from "@web/core/tree_editor/tree_editor_components";
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {VariableSelector} from "../Assists/variableSelector/variableSelector";
import {getValueEditorInfo} from "@web/core/tree_editor/tree_editor_value_editors";
import {RecordPathSelector} from "../Assists/recordPathSelector/recordPathSelector";
import {TypeToggler} from "../Assists/typeToggler/TypeToggler";
import {FieldTypeDropdown} from "../Assists/fieldTypeDropdown/fieldTypeDropDown";
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";
import {MailRecordPathSelector} from "./subcomponents/mailRecordPathSelector";
import {MultiDataSelector} from "../FollowerNode/subComponents/multiDataSelector";

export class MailNode extends ConfigurationBase {
    static props = ['*'];
    setup() {
        super.setup();
        this.emailState = useState({
            mailTemp: ""
        })
        this.state = useState({
            templateId: false,
            applyModel: false,
            isTemplate: true
        })
    }

    get getTogglerOptions() {
        return [
            {label: "custom", value: false},
            {label: "Template", value: true},
        ]
    }

    get getType() {
        return this.fieldState.mail_isTemplate || false
    }

    updateType(value) {
        this.fieldState.mail_isTemplate = value.value
    }

    get getSubject() {
        return this.fieldState.mail_subject || {}
    }

    setSubject(ev) {
        const mail_sub = this.fieldState.mail_subject || {}
        mail_sub.value = ev
        this.fieldState.mail_subject = mail_sub
    }

    setLabel(label) {
        this.fieldState.label = label
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    get getLabel() {
        return this.fieldState.label || ""
    }

    get getMessage() {
        return this.fieldState.mail_body || ""
    }

    setMessageValue(ev) {
        this.fieldState.mail_body = ev
    }

    getDomain() {
        return [["model_id", "=", this.getModelId]]
    }

    get getModelId() {
        const modelId = this.variables.find(variable => variable.id === this.fieldState.mail_record.value)
        return modelId?.modelId || false
    }

    get getModel() {
        return this.fieldState.mail_record?.value || ""
    }

    get getTemplate() {
        return this.fieldState.mail_template.name || ''
    }

    getRecipient() {
        !this.fieldState.mail_to ? this.fieldState.mail_to = [{value: []}] : false
        return this.fieldState.mail_to
    }

    get getRecipientField() {
        return {type: "many2many",}
    }

    get getRecords() {
        let variables = []
        this.variables.forEach(variable => {
            variable.variable_type === 'record' && variable.modelId ? variables.push({
                value: variable.id,
                label: variable.variable_name
            }) : null
        })
        return variables
    }

    setData(value, index, field) {
        if (field === 'recipient') {
            const actualIndex = index ? index : 0
            this.fieldState.mail_to[actualIndex] = this.fieldState.mail_to[actualIndex] ? this.fieldState.mail_to[actualIndex] : {}
            this.fieldState.mail_to[actualIndex].value = value
        }
    }

    insertData(index, field) {
        if (field === 'recipient') {
            index !== false ? this.fieldState.mail_to.splice(index + 1, 0, {value: []}) : this.fieldState.mail_to.push({value: []})
        }
    }

    removeData(indexToRemove, field) {
        if (field === 'recipient') {
            const filteredData = this.fieldState.mail_to.filter((_, index) => index !== indexToRemove)
            this.fieldState.mail_to = filteredData
        }
    }

    onUpdateRecipients(ev) {
        let mail_to = this.fieldState.mail_to || {}
        mail_to.value = ev
        this.fieldState.mail_to = mail_to
    }

    getResDomain() {
        return []
    }

    updateObject(record) {
        this.fieldState.mail_record = this.getRecords.find((item) => item.value === record)
        if (!this.fieldState.mail_template) {
            this.fieldState.mail_template = {}
        }
        this.fieldState.mail_template.name = ""
        this.fieldState.mail_template.id = false
        this.getDomain()
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }

    getComponentProps(info) {
        const {value, update} = info.type === 'recipient'
            ? {value: this.getRecipient.value, update: (value) => this.onUpdateRecipients(value)}
            : info.type === 'subject'
                ? {value: this.getSubject.value || '', update: (value) => this.setSubject(value)}
                : false
        return info.extractProps({value, update})
    }

    getFieldData(type) {
        return type === 'recipient'
            ? {fieldDef: {type: "many2one", relation: 'res.partner',}, operator: 'in'}
            : type === 'subject'
                ? {fieldDef: {type: "char"}, operator: '='}
                : false
    }

    getVariablesField(type, selectionType) {
        let flVariables;
        let fieldInfo;
        if (type === 'recipient') {
            return selectionType === 'variable'
                ? {flVariables: this.props.variables.filter(variable => ['record', 'recordset'].includes(variable.variable_type) && ["res.partner", "res.users", "hr.employee"].includes(variable.modelName))}
                : selectionType === 'record'
                    ? {
                        flVariables: this.props.variables.filter(variable => variable.variable_type === "record"),
                        fieldInfo: {
                            resModel: this.modelState.model['model'],
                            fieldDef: {type: 'many2one', relation: ['res.partner', 'res.users']},
                        }
                    }
                    : false
        }
        if (type === 'subject') {
            return selectionType === 'variable'
                ? {flVariables: this.props.variables.filter(variable => variable.variable_type === "string")}
                : selectionType === 'record'
                    ? {
                        flVariables: this.props.variables.filter(variable => variable.variable_type === "record"),
                        fieldInfo: {resModel: this.modelState.model['model'], fieldDef: {type: 'char'},}
                    }
                    : false
        }

    }

    getValueEditorInfo(field, type) {
        const selectionType = field.selectionType ? field.selectionType : ''
        const {fieldDef, operator} = this.getFieldData(type)
        const {flVariables, fieldInfo} = this.getVariablesField(type, selectionType)
        let editorValue = getValueEditorInfo(fieldDef, operator);
        editorValue.type = type;
        if (selectionType === "variable") {
            return {
                component: VariableSelector,
                type,
                extractProps: ({value, update}) => {
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
                component: MailRecordPathSelector,
                type,
                extractProps: ({value, update}) => {
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
    toggleIncludeVariable(value, field, index) {
        if (field === 'recipient') {
            if (![value, undefined].includes(this.fieldState.mail_to[index].selectionType)) {
                this.fieldState.mail_to[index] = {value: [], selectionType: value}
            }else this.fieldState.mail_to[index].selectionType = value
        } else if (field === 'subject') {
            if (![value, undefined].includes(this.fieldState.mail_subject.selectionType)) {
                this.fieldState.mail_subject = {value: '', selectionType: value}
            }else this.fieldState.mail_subject.selectionType = value
        }
    }

    onSelectMail(ev) {
        if (!this.fieldState.mail_template) {
            this.fieldState.mail_template = {}
        }
        this.fieldState.mail_template.name = ev[0]?.display_name
        this.fieldState.mail_template.id = ev[0]?.id
    }

    getRecipientCode(mail_to) {
        let email_to = []
        let mail_rec;
        mail_to ? mail_to.forEach(field => {
            if (field.selectionType === 'variable') {
                mail_rec = this.props.variables.filter((variable) => variable.id === field.value.selectedVariable)[0]
                if (mail_rec.modelName === 'res.users') {
                    if (mail_rec.variable_type === 'recordset') {
                        // const records = mail_rec
                        email_to.push(`*[rec.partner_id.id for rec in ${mail_rec.variable_name}]`)
                    } else {
                        email_to.push(`${mail_rec.variable_name}.partner_id.id`)
                    }
                } else if (mail_rec.modelName === "res.partner") {
                    email_to.push('*' + mail_rec.variable_name + '.ids')
                } else if (mail_rec.modelName === "hr.employee") {
                    if (mail_rec.variable_type === 'recordset') {
                        email_to.push(`*[rec.work_contact_id.id for rec in ${mail_rec.variable_name}]`)
                    } else {
                        email_to.push(`${mail_rec.variable_name}.work_contact_id.id`)
                    }
                }
            } else if (field.selectionType === 'record') {
                mail_rec = this.props.variables.filter((variable) => variable.id === field.value.record)[0]
                email_to.push(mail_rec.variable_name + '.' + field.value.pathValue)
            } else {
                email_to.push(field.value)
            }
        }) : false
        return email_to
    }

    generateCode() {
        const {mail_record, mail_template, mail_isTemplate, mail_to, mail_body, mail_subject} = this.fieldState
        // const mail_selectionType = mail_to.selectionType || false
        const Record = this.variables.find(variable => variable.id === mail_record.value)
        let email_to = mail_to ? this.getRecipientCode(mail_to) : []
        let email_subject;
        let subject_rec;
        const subject_selectionType = mail_subject.selectionType
        if (subject_selectionType === 'variable') {
            subject_rec = this.props.variables.filter((variable) => variable.id === mail_subject.value.selectedVariable)
            email_subject = subject_rec[0].variable_name
        } else if (subject_selectionType === 'record') {
            subject_rec = this.props.variables.filter((variable) => variable.id === mail_subject.value.record)
            email_subject = subject_rec[0].variable_name + '.' + mail_subject.value.pathValue
        } else {
            email_subject = `"${mail_subject.value}"`
        }
        let code = ``
        if (mail_isTemplate) {
            code = `template = env["mail.template"].browse(${mail_template.id})\ntemplate.send_mail(${Record?.variable_name}.id,force_send=True)`
        } else {
            code = `to = env["res.partner"].browse([${email_to}]).mapped('email')\nemail = env['ir.mail_server'].build_email(email_from=env.user.email,email_to=list(set(to)),subject=${email_subject}, body="""${mail_body}""")\nenv['ir.mail_server'].send_email(email)`
        }
        return code || "";
    }

    getValidateRecipient(fields, single) {
        let isField = true
        if (single) {
            if (['variable', 'record'].includes(fields.selectionType)) {
                if (!fields.value?.pathValue) {
                    isField = false
                }
            } else isField = fields.value?.length
        } else {
            fields.forEach(field => {
                if (['variable', 'record'].includes(field.selectionType)) {
                    if (!field.value?.pathValue) isField = false
                } else isField = field.value?.length
            })
        }
        return isField
    }

    validateForm() {
        const {mail_record, mail_template, mail_isTemplate, mail_to, mail_body, mail_subject, label} = this.fieldState;
        // Validation rules
        const errors = {};
        const recipients = this.getValidateRecipient(mail_to, false)
        const subject = this.getValidateRecipient(mail_subject, true)
        // Validate label: must be a non-empty
        !label ? errors.label = "Label field must be a non-empty." : false
        // Validate mail_record: must be a non-empty string
        if (mail_isTemplate && !mail_record) {
            errors.mail_record = "Record must be a non-empty.";
        }
        // Validate mail_template: must not be a non empty
        if (mail_isTemplate && !mail_template.id) {
            errors.mail_template = "Template must be a non-empty.";
        }
        // Validate mail_template: must not be a non empty
        !mail_isTemplate && !recipients ? errors.mail_to = "Mail to  must be a non-empty." : false

        // Validate mail_subject: must not be a non-empty
        !mail_isTemplate && !subject ? errors.mail_subject = "Mail subject  must be a non-empty." : false

        // Validate mail_body: must not be a non-empty
        !mail_isTemplate && !mail_body.length ? errors.mail_body = "Mail Message  must be a non-empty." : false
        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }
        // If no errors, form is valid
        return {isValid: true};
    }
}

MailNode.template = "MailNode";
MailNode.components = {
    ...ConfigurationBase.components,
    Many2OneField,
    Record,
    Select,
    Input,
    Many2XAutocomplete,
    Dropdown,
    DropdownItem,
    TypeToggler,
    FieldTypeDropdown,
    CustomDropdown,
    MultiDataSelector,
};
