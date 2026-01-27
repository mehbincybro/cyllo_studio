/* @odoo-module */
import {DomainSelector} from "@web/core/domain_selector/domain_selector";
import {SheetTreeEditor} from "./tree_editor";
import {getOperatorEditorInfo} from "@web/core/tree_editor/tree_editor_operator_editor";
import {getDomainDisplayedOperators} from "./getDomainDisplayedOperators";
import {condition} from "@web/core/tree_editor/condition_tree";

export const ALLOWED_FIELD_TYPES = [
    'many2one',
    'boolean',
    'selection',
    'char',
    'text',
    'html',
    'date',
    'datetime',
    'integer',
    'float',
    'monetary',
]

export class SheetDomainSelector extends DomainSelector {
    static template = "SheetDomainSelector"

    setup() {
        super.setup();
        this.domainDefaultCondition = condition("id", "in", [])
    }

    getPathEditorInfo() {
        const {resModel, isDebugMode} = this.props;
        const res = super.getPathEditorInfo(...arguments);
        return {
            ...res,
            extractProps: ({update, value: path}) => {
                return {
                    path,
                    update,
                    resModel,
                    isDebugMode,
                    readonly: false,
                    followRelations: false,
                    filter: (fieldDef) => {
                        return ALLOWED_FIELD_TYPES.includes(fieldDef.type) && fieldDef.store
                    }
                };
            },
        };
    }

    getOperatorEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const operators = getDomainDisplayedOperators(fieldDef);
        return getOperatorEditorInfo(operators);
    }
}

SheetDomainSelector.components = {
    ...SheetDomainSelector.components,
    SheetTreeEditor,
}

SheetDomainSelector.props = {
    ...SheetDomainSelector.props,
    modelName: {type: String, optional: true},
    handleDeleteDomain: {type: Function, optional: true},
}
SheetDomainSelector.defaultProps = {
    ...SheetDomainSelector.defaultProps,
    modelName: "",
    handleDeleteDomain: () => {
    },
}