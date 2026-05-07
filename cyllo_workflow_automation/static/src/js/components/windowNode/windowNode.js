/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { Record } from "@web/model/record";
import { CharField } from "@web/views/fields/char/char_field";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { ConfigurationBase } from "../configurationBase/configurationBase";

export class WindowNode extends ConfigurationBase {
    get recordProps() {
        const label = { type: "char", string: "Label" };
        const window_action_id = {
            type: "many2one",
            string: "Window Action",
            relation: "ir.actions.act_window",
        };
        const window_view_type = {
            type: "selection",
            string: "View Type",
            selection: [
                ["list", "List"],
                ["form", "Form"],
                ["kanban", "Kanban"],
                ["calendar", "Calendar"],
                ["pivot", "Pivot"],
                ["graph", "Graph"],
                ["activity", "Activity"],
            ],
        };
        const window_target = {
            type: "selection",
            string: "Target",
            selection: [
                ["current", "Current"],
                ["new", "New Tab / Dialog"],
                ["fullscreen", "Fullscreen"],
                ["inline", "Inline"],
            ],
        };
        const window_domain = { type: "char", string: "Domain Filter" };
        const window_context = { type: "char", string: "Context" };

        const fields = {
            label,
            window_action_id,
            window_view_type,
            window_target,
            window_domain,
            window_context,
        };

        return {
            mode: "edit",
            onRecordChanged: (record, changes) => {
                for (const key in changes) {
                    this.fieldState[key] = changes[key];
                }
            },
            resModel: "node.struct",
            resId: this.props.id,
            fieldNames: fields,
            activeFields: fields,
        };
    }

    onChangeLabel(label) {
        this.fieldState.label = label;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId: this.props.id });
    }

    generateCode() {
        const actionId = this.fieldState.window_action_id;
        if (!actionId) {
            return "";
        }

        this.props.updateImports({
            parent: 'import logging\n_logger = logging.getLogger(__name__)',
            child: '',
            nodeId: this.props.id,
        });

        const viewType = this.fieldState.window_view_type || "list";
        const target = this.fieldState.window_target || "current";
        const domain = (this.fieldState.window_domain || "[]").trim() || "[]";
        const context = (this.fieldState.window_context || "{}").trim() || "{}";

        return `
try:
    action_obj = env["ir.actions.act_window"].browse(${actionId}).read()[0]
    action_obj["view_mode"] = "${viewType}"
    action_obj["target"] = "${target}"
    action_obj["domain"] = ${domain}
    action_obj["context"] = ${context}
    channel = "bus_do_action"
    message = {
        "auth": {"user": env.user.id},
        "action": action_obj,
        "channel": channel,
    }
    env["bus.bus"]._sendone(channel, "notification", message)
except Exception as e:
    _logger.error("Check Workflow automation rule(ID:${this.props.id}): %s", e)
`;
    }

    validateForm() {
        const errors = {};
        const { label, window_action_id } = this.fieldState;

        if (!label || !label.trim()) {
            errors.label = _t("Label is required.");
        }
        if (!window_action_id) {
            errors.window_action_id = _t("Please select a Window Action.");
        }

        return {
            isValid: Object.keys(errors).length === 0,
            errors,
        };
    }
}

WindowNode.template = "WindowNode";
WindowNode.components = {
    ...ConfigurationBase.components,
    Record,
    CharField,
    SelectionField,
    Many2OneField,
};
