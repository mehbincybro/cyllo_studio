/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";

export class ReportCreationDialog extends owl.Component {
    static template = "cyllo_studio.ReportCreationDialog";
    static components = { Dialog, AutoComplete };
    static props = {
        close: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            name: "",
            modelId: "",
            modelLabel: "",
            models: [],
        });

        onWillStart(async () => {
            // Fetch models that can have reports
            this.state.models = await this.orm.searchRead(
                "ir.model",
                [['transient', '=', false], ['model', 'not like', 'ir.%']],
                ["id", "name", "model"]
            );
            // Sort models by name
            this.state.models.sort((a, b) => a.name.localeCompare(b.name));
        });
    }

    get autoCompleteSources() {
        return [
            {
                placeholder: _t("Search a model..."),
                options: (request) => {
                    const filtered = this.state.models.filter(m =>
                        m.name.toLowerCase().includes(request.toLowerCase()) ||
                        m.model.toLowerCase().includes(request.toLowerCase())
                    );
                    return filtered.map(m => ({
                        value: m.id,
                        label: `${m.name} (${m.model})`,
                    }));
                },
            },
        ];
    }

    onModelSelected({ value, label }) {
        this.state.modelId = value;
        this.state.modelLabel = label;
    }

    async _onCreate() {
        if (!this.state.name || !this.state.modelId) {
            this.notification.add("Please fill in all fields", { type: "danger" });
            return;
        }

        try {
            const action = await this.orm.call(
                "ir.actions.report",
                "action_create_blank_report",
                [this.state.name, this.state.modelId]
            );

            if (action && action.type === "ir.actions.client") {
                this.action.doAction(action);
                this.props.close();
            } else if (action && action.success === false) {
                this.notification.add(action.error || "Execution failed", { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || "An error occurred", { type: "danger" });
        }
    }
}
