/** @odoo-module **/
import {
    Component,
    onMounted,
    useState,
    useEffect,
    useRef,
    onWillStart,
    onWillUpdateProps,
    useExternalListener,
} from "@odoo/owl";
import {
    useService,
    useOwnedDialogs
} from "@web/core/utils/hooks";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    registry
} from "@web/core/registry";
import {
    handleUndoRedo
} from "@cyllo_studio/js/utils/undo_redo_utils";
import {
    ExpressionEditorDialog
} from "@web/core/expression_editor_dialog/expression_editor_dialog";
import {
    _t
} from "@web/core/l10n/translation";
import {
    getWidgetTypes,
    getWidgetSupport
} from "@cyllo_studio/js/view_editor/widget";
import {MultiSelectDropDown} from "@cyllo_studio/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown";
import {
    DomainSelectorDialog
} from "@web/core/domain_selector_dialog/domain_selector_dialog";

import {
SelectionFieldValue
} from "@cyllo_studio/js/view_editor/components/selection_field_widget_values/selection_field_value_widget";

export class FieldProperties extends Component {
    static template = "cyllo_studio.FieldProperties";
    static props = {
        attr: {
            type: Object,
            optional: true
        },
        allFields: {
            type: Object,
            optional: true
        },
        type: {
            type: String,
            optional: true
        },
        name: {
            type: String,
            optional: true
        },
        string: {
            type: String,
            optional: true
        },
        label: {
            type: String,
            optional: true
        },
        widget: {
            type: String,
            optional: true
        },
        fieldType: {
            type: String,
            optional: true
        },
        context: {
            type: String,
            optional: true
        },
        viewType: {
            type: String,
            optional: true
        },
        model: {
            type: String,
            optional: true
        },
        viewId: {
            type: [Number,Boolean],
            optional: true
        },
        type: {
            type: String,
            optional: true
        },
        create: {
            type: Boolean,
            optional: true
        },
        placeholder: {
            type: String,
            optional: true
        },
        help: {
            type: String,
            optional: true
        },
        edit: {
            type: Boolean,
            optional: true
        },
        readonly: {
            type: String,
            optional: true
        },
        column_invisible: {
            type: String,
            optional: true
        },
        invisible: {
            type: String,
            optional: true
        },
        required: {
            type: String,
            optional: true
        },
        related_model: {
            type: String,
            optional: true
        },
        relational_model: {
            type: [Object, String],
            optional: true
        },
        domain: {
            type: String,
            optional: true
        },
        field_path: {
            type: String,
            optional: true
        },
        label_path: {
            type: String,
            optional: true
        },
        path: {
            type: String,
            optional: true
        },
        widget_types: {
            type: Object,
            optional: true
        },
        options: {
            type: Object,
            optional: true
        },
        label_path: {
            type: String,
            optional: true
        },
        position: {
            type: String,
            optional: true
        },
        item_type: {
            type: String,
            optional: true
        },
        field_info: {
            type: Object,
            optional: true
        },
        sibling: {
            type: Boolean,
            optional: true
        },
        sibling_edit: {
            type: Boolean,
            optional: true
        },
         mode: {
        type: [String, Object, Number],
        optional: true
    },
    activeFields: {
        type: Object,
        optional: true
    },
    measure: {
        type: [String, Object, Array],
        optional: true
    },
    isMenu: {
        type: Boolean,
        optional: true
    },
    hasColorPicker: {
        type: Boolean,
        optional: true
    },
    progressAttributes: {
        type: Object,
        optional: true
    },
    envModel: {
        type: [String, Object],
        optional: true
    },
    ribbonElement: {
        type: Object,
        optional: true
    },
    MetaData: {
        type: Object,
        optional: true
    },
    calendar_info: {
        type: Object,
        optional: true
    },
    isFieldTag: {
        type: Boolean,
        optional: true
    },
    colorPickerPath: {
        type: String,
        optional: true
    },
    optional: {
        type: String,
        optional: true
    },
    fieldNodes: {
        type: Object,
        optional: true
      }
    };
    setup() {
        this.actionService = useService("action");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("effect");
        this.addDialog = useOwnedDialogs();
        this.ref = useRef('cy-Properties')
        this.prevState = useState({
            ...this.props
        })
        this.StatusBarValues = useState({
            clickable: false,
            foldField: '',
            statusbarVisible: '',
            group_ids: [],
            invisible: 'False',
            defaultValue: 'True',
        })
        this.state = useState({
            xStudio: 0,
            create: this.props.create || false,
            field_names: [],
            item_name: null,
            name: this.props.name,
            string: this.props.string,
            related_model: this.props.related_model || this.getRelatedModelFromField(),
            widget: this.props.widget,
            help: this.props.help,
            placeholder: this.props.placeholder,
            optional: this.props?.attr?.optional || '',
            column_invisible: this.props.column_invisible || 'false',
            invisible: this.props.invisible || 'false',
            readonly: this.props.readonly || 'false',
            required: this.props.required || 'false',
            relatedModel: this.props.related_model || '',
            relatedModelField:"",
            field_path: this.props.field_path,
            label_path: this.props.label_path,
            edited: false,
            existedField: false,
            fieldType: [
                "Char",
                "Text",
                "Html",
                "Integer",
                "Float",
                "Date",
                "Datetime",
                "Binary",
                "Selection",
                "Boolean",
                "Many2one",
                "One2many",
                "Many2many",
            ],
             field: 'existing',
            values: [],
            selectionValues: [],
            SelectedOptions: [],
            models: [],
            domain: this.props.domain || '',
            inverseFields: [],
            selectedFieldType: this.props.fieldType || 'char',
            widget_types: [],
            context: '{}',
            sibling : this.props.sibling,
            isStatusBar: false,
            related_model_field: [],
        });
        this.selectedWidget = this.props.widget === 'False' ? '' : this.props.widget || ''
        onWillUpdateProps((nextProps) => {
            this.state.name = nextProps.name
            this.state.string = nextProps.string

            let relatedModel = nextProps.related_model;
            if (!relatedModel && nextProps.name && nextProps.allFields) {
                const fieldInfo = nextProps.allFields[nextProps.name];
                if (fieldInfo?.relation) {
                    relatedModel = fieldInfo.relation;
                }
            }
            this.state.related_model = relatedModel;

            this.state.widget = nextProps.widget
            this.state.selectedFieldType = nextProps.fieldType
            this.state.help = nextProps.help
            this.state.placeholder = nextProps.placeholder
            this.state.optional = nextProps.optional
            this.state.column_invisible = nextProps.column_invisible || 'false'
            this.state.invisible = nextProps.invisible || 'false'
            this.state.readonly = nextProps.readonly || 'false'
            this.state.required = nextProps.required || 'false'
            this.state.sibling = nextProps.sibling
            this.state.widget_types = getWidgetTypes(nextProps.fieldType);
            this.state.domain = nextProps.domain || '';
        });
        useEffect(() => {
            if (this.props.edit === true && this.state.widget === 'statusbar') {
                this.loadStatusbarValues();
            }
            else {
                const CurrWidget = this.props.widget
                this.widgetOptionalFields(CurrWidget, this.props.options)
            }
        }, () => [this.props.edit, this.state.widget])

        onMounted(async () => {
            this.state.widget_types = getWidgetTypes(this.props.fieldType)
            this.action_area = document.querySelector(".o_action_manager")
            const fieldsData = await this.orm.searchRead(
                "ir.model.fields",
                [
                    ["model_id", "=", this.props.model]
                ],
                ["name"]
            );
            const studioFields = fieldsData.filter((field) =>
                field.name?.startsWith("x_studio")
            );
            this.state.xStudio = studioFields.length;
            this.state.models = await this.rpc('/cyllo_studio/get_non_abstract_non_transient_models');
        });

        var arrExistingFields = []
        Object.entries(this.props.allFields).forEach(([key, value]) => {
            arrExistingFields.push({
                name: key,
                string: value.string,
                type: value.type
            })
        });
        this.existedField = arrExistingFields
    }
    //start
    onOptionalClick({target}){
    this.state.optional = target.checked ? 'hide' : 'show'
    }
  get statusbarVisibleOptions() {
    // Use props.options if exists
    let visible = '';
    if (this.props.options && this.props.options.statusbar_visible) {
        visible = this.props.options.statusbar_visible;
    } else if (this.StatusBarValues.statusbarVisible) {
        visible = this.StatusBarValues.statusbarVisible;
    }

    const visibleArray = visible
        ? visible.split(',').map(v => v.trim()).filter(Boolean)
        : [];

    return visibleArray;
}
async loadStatusbarValues() {
    try {
        // Load selection values for the field
        if (this.props.field_info && this.props.field_info.selection) {
            this.state.values = this.props.field_info.selection;
        } else if (this.props.allFields && this.props.name) {
            const fieldInfo = this.props.allFields[this.props.name];
            if (fieldInfo && fieldInfo.selection) {
                this.state.values = fieldInfo.selection;
            }
        }

        // Load currently visible options from widget options
        if (this.props.options && this.props.options.statusbar_visible) {
            const visibleStr = this.props.options.statusbar_visible;
            // statusbar_visible contains keys (technical names), not labels
            this.state.SelectedOptions = visibleStr
                .split(',')
                .map(v => v.trim())
                .filter(Boolean);
            this.StatusBarValues.statusbarVisible = visibleStr;
        } else {
            // If no statusbar_visible is set, show all values
            this.state.SelectedOptions = this.state.values.map(v => v[0]);
        }
    } catch (error) {
        console.error('Error loading statusbar values:', error);
    }
}

    generateRandomFieldName() {
        const timestamp = Date.now();
        const randomNum = Math.floor(Math.random() * 1000);
        return `x_studio_${timestamp}_${randomNum}`;
    }

    onCellKeydown(value) {
        this.state.edited = true
        const labelValue = this.ref.el.querySelector("#label").value.trim();
        this.state.name = 'x_studio_' + labelValue.toLowerCase().split(' ').join('_');
    }
    get fieldType() {
        const result = this.state.fieldType.map((item) => ({
            value: item,
            label: item
        }));
        return result;
    }
    RelatedModel(array) {
        const result = array.map((item) => ({
            value: item.model,
            label: item.name,
        }));
        return result;
    }
   async handleFieldTypeChange(value) {
    this.state.edited = true
    this.selectedWidget = ''
    const container = document.getElementById('dynamic-container');
    while (container && container.firstChild) {
        container.removeChild(container.firstChild);
    }
    this.state.selectedFieldType = value.toLowerCase()
    this.state.widget_types = getWidgetTypes(this.state.selectedFieldType)
    if (['many2one', 'many2many'].includes(this.state.selectedFieldType)) {
        this.state.models = await this.rpc('/cyllo_studio/get_non_abstract_non_transient_models');
    }else if (this.state.selectedFieldType === 'one2many' || this.props.fieldType === 'one2many') {
        const relatedFields = await this.orm.searchRead('ir.model.fields',[
            ['ttype', '=', 'many2one'],
            ['relation', '=', this.action.currentController.action.res_model]
            ], ['name', 'field_description', 'model_id'])
        this.state.related_model_field = relatedFields;
    } else {
        this.state.related_model_field = [];
    }
}
getRelatedModelFromField() {
    if (this.props.name && this.props.allFields) {
        const fieldInfo = this.props.allFields[this.props.name];
        if (fieldInfo?.relation) {
            return fieldInfo.relation;
        }
    }
    return '';
}

    fieldsDomain() {
        const ModelName = this.state.related_model || this.props.model || this.props.related_model
        this.dialogService.add(DomainSelectorDialog, {
            resModel: ModelName,
            domain: this.state.domain,
            onConfirm: (domain) => this.domainConfirm(domain),
            title: ("Domain"),
        });
    }
    domainConfirm(domain) {
        this.state.domain = domain
    }
    cancelField() {
        if (this.props.create) {
            this.action.doAction('studio_reload')
            this.env.bus.trigger('CLEAR-MENU');
        }
    }

    async deleteField(el) {
        const view_id = this.props.viewId
        const view_type = this.props.viewType
        const currentNotebook = document.querySelector('.o_notebook .nav-link.active');
        if (currentNotebook) {
            const notebookContainer = currentNotebook.closest('.o_notebook');
            const notebookId = notebookContainer?.getAttribute('data-notebook-id') || 'default';
            const pageIndex = Array.from(currentNotebook.parentElement.parentElement.children)
                .indexOf(currentNotebook.parentElement);

            const storedPages = JSON.parse(sessionStorage.getItem("cy_studio_active_notebook") || "{}");
            storedPages[notebookId] = pageIndex;
            sessionStorage.setItem("cy_studio_active_notebook", JSON.stringify(storedPages));
        }
        const response = await this.rpc("cyllo_studio/delete/existing_fields", {
            method: 'delete_existing_fields',
            model: this.props.model,
            view_id: this.props.viewId,
            view_type: this.props.viewType,
            args: [{
                fieldName: this.props.string,
                model: this.props.model,
                path: this.props.path,
                label_path: this.props.label_path
            }],

            kwargs: {
                view_id: view_id ? view_id : null,
                view_type: view_type,
            }
        })
        if (response) {
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr);
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }
        this.action.doAction('studio_reload')
    }
    async createField() {
    // Validate field name
    if (!this.state.name) {
        this.notification.add({
            title: _t("Validation Error"),
            message: "Unable to save the field.",
            description: "Please provide a field name to save",
            type: "notification_panel",
            notificationType: "warning",
        });
        return;
    }

    let optionalFields = {};

    // Collect widget options from DOM
    const container = document.getElementById('dynamic-container');
    if (container) {
        container.querySelectorAll('input, select').forEach(field => {
            const fieldName = field.id;
            let fieldValue = field.type === "checkbox" ? field.checked : field.value;

            if (field.name === "fold_field") {
                this.orm.searchRead("ir.model.fields", [
                    ['model', '=', this.state.relatedModel]
                ])
                .then((fields) => {
                    const foldFieldExists = fields.some(f => f.name === 'fold');
                    if (!foldFieldExists) {
                        this.action.doAction({
                            type: 'ir.actions.client',
                            tag: 'display_notification',
                            params: {
                                message: 'Related model must contain fold field',
                                type: 'danger',
                                sticky: false,
                            },
                        });
                    }
                });
            }

            if (fieldValue !== undefined && fieldValue !== null && fieldValue !== "") {
                optionalFields[fieldName] = fieldValue;
            }

            if (typeof fieldValue === 'string' && fieldValue.startsWith('[') && fieldValue.endsWith(']')) {
                try {
                    fieldValue = fieldValue.replace(/'/g, '"');
                    fieldValue = JSON.parse(fieldValue);
                    optionalFields[fieldName] = fieldValue;
                } catch (e) {
                    console.error('Error parsing field value:', e);
                }
            }
        });
    }
    // Build the arguments object
    const attrs = {
        widget: this.state.widget || '',
        help: this.state.help || '',
        placeholder: this.state.placeholder || '',
        invisible: this.state.invisible || '',
        readonly: this.state.readonly || '',
        required: this.state.required || '',
        domain: this.state.domain || '',
        context: this.state.context || '',
    };

    let args = {};

    if (this.props.edit) {
        // EDIT MODE: Send changed values with field_info containing selection
        const changedValues = this.getCurrentChanges(this.prevState, this.state);

        // Ensure field_info is included for selection fields
        if (this.state.selectedFieldType === 'selection') {
            changedValues.field_info = {
                selection: this.state.SelectedOptions
                    .filter(val => val && val.trim() !== '')
                    .map(val => [val.toLowerCase().replace(/\s+/g, '_'), val])
            };
        }

        // IMPORTANT: Add statusbar_visible to optional_fields if this is a statusbar widget
        if (this.state.widget === 'statusbar' && this.state.SelectedOptions.length > 0) {
            optionalFields['statusbar_visible'] = this.state.SelectedOptions.join(', ');
        }

        args = {
            edit: true,
            value: changedValues,
            optional_fields: optionalFields || {},
            field_path: this.props.field_path || this.props.path,
            label_path: this.props.label_path || '',
            field_name: this.props.name || '',
            active_fields:this.props.activeFields,
            model:this.state.related_model || this.props.model,
        };
    } else {
        var related_model_field = null;
        if (this.state.selectedFieldType === 'one2many') {
            const related_field_id = this.state.relatedModelField ? this.state.relatedModelField : '';
            if (related_field_id) {
                related_model_field = this.state.related_model_field.find(field => field.id == related_field_id);
            }
        }

        // For statusbar widget in new field mode
        if (this.state.widget === 'statusbar' && this.state.selectionValues.length > 0) {
            optionalFields['statusbar_visible'] = this.state.selectionValues.join(', ');
        }
        args = {
            edit: false,
            field_type: this.state.selectedFieldType || 'char',
            optional_fields: optionalFields || {},
            technical_name: this.state.name,
            label: this.state.string || '',
            position: this.props.position || 'inside',
            cy_path: this.props.path || '',
            sibling: this.state.sibling || false,
            item_type: this.props.item_type || "",
            field_info: this.props.field_info || {},
            field_path: this.props.path,
            label_path: this.props.label_path,
            elementType: "",
            related_model: this.state.related_model,
            attrs,
            model: this.props.model,
            view_id: this.props.viewId,
            view_type: this.props.viewType,
            selectionValues: this.state.selectionValues,
            related_model_field: related_model_field,
            active_fields:this.props.activeFields,
        };
    }
    this.env.services.ui.block();
        let hasError = false;
    try {
        const modelName = sessionStorage.getItem("RelationalModel")
            ? (Flatted.parse(sessionStorage.getItem("RelationalModel"))?.[0]?.relation || this.props.model)
            : this.props.model;
        if (['many2one', 'many2many'].includes(this.state.selectedFieldType) && !this.state.related_model){
            this.notification.add({
                title: _t("Validation Error"),
                message: "Unable to save the field.",
                description: "Please select a related model field for One2many or Many2many.",
                type: "notification_panel",
                notificationType: "warning",
            });
            hasError=true;
            return;
        }

        const currentNotebook = document.querySelector('.o_notebook .nav-link.active');
        if (currentNotebook) {
            const notebookContainer = currentNotebook.closest('.o_notebook');
            const notebookId = notebookContainer?.getAttribute('data-notebook-id') || 'default';
            const pageIndex = Array.from(currentNotebook.parentElement.parentElement.children)
                .indexOf(currentNotebook.parentElement);

            const storedPages = JSON.parse(sessionStorage.getItem("cy_studio_active_notebook") || "{}");
            storedPages[notebookId] = pageIndex;
            sessionStorage.setItem("cy_studio_active_notebook", JSON.stringify(storedPages));
        }

        const response = await this.rpc("/cyllo_studio/create/new_fields", {
            method: 'create_new_fields',
            model: modelName || this.props.model,
            view_id: this.props.viewId,
            view_type: this.props.viewType,
            args: [args],
        });

        if (response) {
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr);
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }
    } catch (error) {
        hasError = true;
        console.error('Error creating field:', error);
        this.notification.add({
            title: _t("Error"),
            message: "Failed to save the field",
            description: error.message || "An unexpected error occurred",
            type: "notification_panel",
            notificationType: "danger",
        });
    } finally {
        this.env.services.ui.unblock();
        if(!hasError){
          this.action.doAction('studio_reload')
        }
    }
}
    getCurrentChanges(prev, current) {
        const changed = {};
        const excludedKeys = ['fieldType', 'widget_types'];
        for (const key in current) {
            if (prev[key] !== undefined && !excludedKeys.includes(key) && prev[key] !== current[key]) {
                changed[key] = current[key];
            }
        }
        return changed;
    }
    handleColumnInvisibleChange(event){
    this.state.edited = true
    this.state.column_invisible = ["false", "undefined"].includes(this.state.column_invisible) ? "true" : "false";
    }
    handleInvisibleChange(event) {
        this.state.edited = true
        this.state.invisible = ["false", "undefined"].includes(this.state.invisible) ? "true" : "false";
    }
    handleReadonlyChange(event) {
        this.state.edited = true
        this.state.readonly = ["false", "undefined"].includes(this.state.readonly) ? "true" : "false";
    }
    handleRequiredChange(event) {
        this.state.required = ["false", "undefined"].includes(this.state.required) ? "true" : "false";
    }
    handleRelatedModelChange(value) {
        this.state.edited = true
        this.props.related_model = value;
        this.state.related_model = value;
    }

    RelatedModelField(array) {
        const result = array.map(item => ({
        value: item.id,
        label: item.field_description + '(' + item.model_id[1] + ')'
        }));
        return [{value: false, label: ''},...result]
    }

    async handleRelatedModelFieldChange(value) {
        this.state.relatedModelField = value;
        const One2ManyRelated = this.state.related_model_field.find(field => field.id == this.state.relatedModelField)
        const One2ManyRelatedModel = await this.orm.read("ir.model", [One2ManyRelated.model_id[0]], [])
        this.state.relatedModel = One2ManyRelatedModel[0].model
    }

    get defaultRelatedModelField() {
        return this.state.relatedModelField
    }

    async attrDomain(ev) {
        this.state.edited = true
        const parent = event.target.closest('.cy-basedOn')
        var attribute = parent.getAttribute('data-attribute')
        var domain = '';
        if (attribute === 'readonly' && this.props.readonly) {
            domain = this.state.readonly ? this.state.readonly : this.props.readonly
        } else if (attribute === 'invisible' && this.props.invisible) {
            domain = this.state.invisible ? this.state.invisible : this.props.invisible
        } else if (attribute === 'required' && this.props.required) {
            domain = this.state.required ? this.state.required : this.props.required
        } else {
            domain = false
        }
        var resModel = this.action.currentController.props.resModel
         var fields_detail = await this.orm.call(resModel, 'fields_get', [], {
        attributes: ['string', 'help', 'type', 'relation', 'selection', 'domain']
    });
    var resModel = this.action.currentController.props.resModel
    domain = domain ? domain : "False";

    // Use the fields that are already available from props
    const fields_info = this.props.allFields || {};
        this.addDialog(ExpressionEditorDialog, {
            resModel,
            fields: fields_info,
            expression: domain,
            onConfirm: (expression) => this.modifier(expression, attribute),
        });
    }
    modifier(expression, attribute) {
        this.attribute = attribute
        if (attribute == 'invisible') {
            this.state.invisible = expression
        }
        if (attribute == 'readonly') {
            this.state.readonly = expression
        }
        if (attribute == 'required') {
            this.state.required = expression
        }
    }
    get newFieldWidgets() {
        return this.state.widget_types.length ? [{
            value: false,
            label: ''
        }, ...this.state.widget_types] : this.state.widget_types
    }

    FieldTypeChange(value) {
        if (value === 'button') {
            this.createButton();
        } else if (value === 'new') {
            this.createNewField();
        } else if (value === 'existing') {
            this.env.bus.trigger("LIST_EXISTING_FIELDS", {
                name: "ExistingName",
                type: "ExistingProperties",
            });
            this.env.bus.trigger('CLEAR-MENU');
        }
    }
    async createButton() {
        this.env.bus.trigger("BUTTON_DETAILS", {
            type: "ButtonProperties",
            path: "/tree",
            position: "inside",
        });
    }

    handleFieldWidgetChange(value) {
        this.state.widget = value;
        this.widgetOptionalFields(this.state.widget)
    }

    //    Widget Options Start
    widgetOptionalFields(widget_name, widget_options = null) {
        if (document.getElementById('dynamic-container')) {
            document.getElementById('dynamic-container').innerHTML = '';
        }
        if (widget_name) {

            if (widget_name == "statusbar") {
                this.state.isStatusBar = true
                this.loadStatusbarValues();
            } else {
                this.state.isStatusBar = false
            }
            const supportedOptions = getWidgetSupport(widget_name);
            const widgetOption = getWidgetTypes(widget_name)
            if (supportedOptions) {
                const container = document.getElementById('dynamic-container');
                if (container) {
                    container.innerHTML = '';
                    supportedOptions.forEach(async field => {
                        const fieldName = field.options.name;
                        const widgetOptionsType = widgetOption?.component?.props[fieldName]?.type
                        let widgetOptionsType_value = "";

                        if (widgetOptionsType && widgetOptionsType.name) {
                            widgetOptionsType_value = widgetOptionsType.name.toString();
                        }
                        var fieldValue = this.props.options?.[fieldName] || ''
                        if (field.options.availableTypes && field.options.availableTypes.length > 0) {
                            const optionFields = this.state.field_type === 'many2many' ? this.state.related_model : this.existedField
                            if (optionFields) {
                                this.state.charFields = Object.keys(optionFields)
                                    .filter(key => optionFields[key].type === field.options.availableTypes[0])
                                    .reduce((obj, key) => {
                                        obj[key] = optionFields[key];
                                        return obj;
                                    }, {});
                            }
                            if (widget_name === 'monetary' && this.state.charFields) {
                                const options = Object.keys(this.state.charFields)
                                    .filter(item => this.state.charFields[item].relation === 'res.currency')
                                    .reduce((acc, key) => {
                                        acc[key] = this.state.charFields[key];
                                        return acc;
                                    }, {});

                                // Update charFields with the filtered options (for 'monetary' widget)
                                this.state.charFields = options;
                            }
                        }
                        var obj = field.options.label
                        let string = "";
                        for (const key in obj) {
                            if (obj.hasOwnProperty(key)) {
                                string += obj[key];
                            }
                        }
                        if (field.options.type === 'field') {
                            if (fieldName === "fold_field") {
                                const div = document.createElement('div');
                                div.id = fieldName + '_div'; // Use field name as ID
                                div.innerHTML = `
                                    <label class="cy-radio_label" for="${fieldName}">
                                        <input class="form-check-input " type="checkbox" id="${fieldName}" name="${fieldName}" ${fieldValue ? 'checked' : ''} >
                                        ${obj}
                                    </label>`;
                                container.appendChild(div);
                            } else {
                                const div = document.createElement('div');
                                div.id = fieldName + '_div'; // Use field name as ID
                                div.innerHTML = `
                                <label class="cy-navbar_label" for="${fieldName}">${obj}:</label>`;
                                container.appendChild(div);
                                const div2 = document.createElement('div');
                                div2.setAttribute('id', fieldName);
                                div2.classList.add('cy-studio-custom-dropdown-image-widget', 'cy-studio-custom-dropdown');
                                container.appendChild(div2);;
                                await owl.mount(CylloStudioDropdown, div2, {
                                    props: {
                                        options: this.ImageWidget,
                                        defaultValue: fieldValue,
                                        onChange: (value) => this.AddModelWidget({
                                            [fieldName]: value
                                        })

                                    },
                                })
                            }
                        } else if (field.options.type === 'string') {
                            const div = document.createElement('div');
                            div.id = fieldName + '_div';

                            // Create label element
                            const label = document.createElement('label');
                            label.className = 'cy-navbar_label';
                            label.htmlFor = fieldName; // Links the label to the input by ID
                            label.textContent = `${obj}:`;

                            // Create input element
                            const input = document.createElement('input');
                            input.className = 'cy-input';
                            input.type = 'text';
                            input.autocomplete = 'off';
                            input.id = fieldName;
                            input.name = fieldName;
                            input.value = fieldValue;
                            if (widgetOptionsType) {
                                input.placeholder = `Expected Input  As :- ${widgetOptionsType_value}`;
                            }

                            // Bind events
                            input.addEventListener('change', (ev) => this.fieldValidation(ev, widgetOptionsType_value)); // Event for the input
                            // Append elements
                            div.appendChild(label);
                            div.appendChild(input);

                            // Append the div to the container
                            container.appendChild(div);
                        } else if (field.options.type == 'boolean') {
                            const div = document.createElement('div');
                            div.id = fieldName + '_div';
                            div.innerHTML = `
                                <label class="cy-radio_label" for="${fieldName}">
                                    <input class="form-check-input" type="checkbox" id="${fieldName}" name="${fieldName}" ${fieldValue ? 'checked' : ''} onClick="(ev)=>onClickColorChangeLabel(ev)">
                                    ${obj}
                                </label>
                            `;
                            div.addEventListener('click', function(ev) {
                                const label = document.getElementsByClassName('cy-radio_label')
                                const checkbox = ev.target;
                                if (checkbox.checked) {
                                    ev.srcElement.parentElement.style.color = '#d3d2ba';
                                } else {
                                    ev.srcElement.parentElement.style.color = "#BCBBA7";
                                }
                            })
                            container.appendChild(div);
                        }
                    })
                }

            }
        } else if (document.getElementById('dynamic-container')) {
            const container = document.getElementById('dynamic-container');
            container.innerHTML = '';
        }
    }

    get ImageWidget() {
        const arr = [{
            value: false,
            label: ''
        }]
        for (let value in this.state.charFields) {
            const obj = {
                value: this.state.charFields[value].name,
                label: this.state.charFields[value].string || this.state.charFields[value].display_name
            }
            arr.push(obj)
        }
        return arr
    }
    AddModelWidget(value) {
        this.state.previewImage = {...this.state.previewImage, ...value}
    }

get multiSelectDropDown() {
    const values = this.state.field === 'existing' ? this.state.values : this.state.selectionValues;

    // Build allValues object from selection values
    let allValues = {};
    if (this.state.field === 'existing') {
        // For existing fields, values are in [key, label] format
        // We use key (technical name) as the value to store
        values.forEach(item => {
            if (Array.isArray(item) && item.length >= 2) {
                const key = item[0];   // technical name (e.g., 'draft', 'sent')
                const label = item[1]; // display name (e.g., 'Draft', 'Sent')
                allValues[key] = label; // key -> label mapping for display
            }
        });
    } else {
        // For new fields, values are simple strings
        values.forEach(item => {
            if (item) {
                allValues[item] = item;
            }
        });
    }

    return {
        selectedValues: [...new Set(this.state.SelectedOptions)],
        allValues,
        onUpdate: (value) => {
            this.state.SelectedOptions = value;
            // Store as comma-separated keys
            this.StatusBarValues.statusbarVisible = value.join(',');
            this.state.edited = true;
        },
    };
}

    //Selection value functions start -->
   checkSelectionValues() {
        const lowerCaseArray = this.state.selectionValues.map(element => element.toLowerCase());
        let setValues = new Set(lowerCaseArray);
        const isSameElement = setValues.size != lowerCaseArray.length
        const isEmpty = lowerCaseArray.some(str => str === null || str.match(/^ *$/) !== null);
        if (isSameElement || isEmpty) {
        let message = isSameElement ? 'Containing same values!' : 'Containing empty values!'
        this.env.services.action.doAction({
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
        'message': message,
        'type': 'warning',
        'sticky': false,
        }
        })
        return false
        }
        return true
        }
addSelectionValue() {
    return this.checkSelectionValues() ? this.state.selectionValues.push('') : false
}
changeSelectionValue(index, value) {
    this.state.selectionValues[index] = value
}
deleteSelectionValue(index) {
    this.state.selectionValues.splice(index, 1)
}
}

FieldProperties.components = {
    CylloStudioDropdown,
    MultiSelectDropDown,
    SelectionFieldValue
};