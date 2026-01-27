/** @odoo-module **/
import {useBus, useService} from "@web/core/utils/hooks";
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {omit} from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
/**
 * Patching this components open a wizard and set data to add spreadsheet
 */
patch(
    KanbanRenderer.prototype,
    {
        setup() {
            super.setup();
            this.userService = useService("user");
            this.actionService = useService("action");
            useBus(
                this.env.bus,
                "addKanbanOnSpreadsheet",
                this.onAddKanbanOnSpreadsheet.bind(this)
            );
        },
        onAddKanbanOnSpreadsheet() {
            // Open wizard for adding spreadsheet and pass meta data
            const model = this.env.searchModel;
            this.actionService.doAction(
                "cyllo_spreadsheet.action_view_spreadsheet_spreadsheet_import",
                {
                    additionalContext: {
                        default_name: this.env.config.getDisplayName(),
                        default_import_data: {
                            mode: "kanban",
                            metaData: {
                                model: model.resModel,
                                domain: model.domain,
                                orderBy: model.orderBy,
                                context: omit(
                                    model.context,
                                    ...Object.keys(this.userService.context)
                                ),
                                fields: model.fields,
                                name: this.env.config.getDisplayName(),
                                threshold: Math.min(model.count, model.limit),
                            },
                        },
                    },
                }
            );
        },
    }
);
