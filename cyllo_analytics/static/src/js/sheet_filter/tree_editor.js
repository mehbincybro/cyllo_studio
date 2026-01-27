/* @odoo-module */
import {TreeEditor} from "@web/core/tree_editor/tree_editor";

export class SheetTreeEditor extends TreeEditor {
    static template = "cyllo_analytics.TreeEditor"
}
SheetTreeEditor.props = {
    ...SheetTreeEditor.props,
    modelName: {type: String, optional: true},
}
SheetTreeEditor.defaultProps = {
    ...SheetTreeEditor.defaultProps,
    modelName: "",
}