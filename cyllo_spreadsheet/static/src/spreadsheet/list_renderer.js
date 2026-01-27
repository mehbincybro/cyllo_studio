/** @odoo-module **/
import {useBus, useService} from "@web/core/utils/hooks";
import {ListRenderer} from "@web/views/list/list_renderer";
import {omit} from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
/**
 * Patching this components open a wizard and set data to add spreadsheet
 */
patch(
    ListRenderer.prototype,
    {
        setup() {
               super.setup();
                this.userService = useService("user");
                this.actionService = useService("action");
                useBus(
                    this.env.bus,
                    "addListOnSpreadsheet",
                    this.onAddListOnSpreadsheet.bind(this)
                );
        },
        onAddListOnSpreadsheet() {
            // Open wizard for adding spreadsheet and pass meta data
            const model = this.env.model.root;
            this.actionService.doAction(
                "cyllo_spreadsheet.action_view_spreadsheet_spreadsheet_import",
                {
                    additionalContext: {
                        default_name: this.env.config.getDisplayName(),
                        default_import_data: {
                            mode: "list",
                            metaData: {
                                model: model.resModel,
                                domain: model.domain,
                                orderBy: model.orderBy,
                                context: omit(
                                    model.context,
                                    ...Object.keys(this.userService.context)
                                ),
                                columns: this.getSpreadsheetColumns(),
                                fields: model.fields,
                                name: this.env.config.getDisplayName(),
                                threshold: Math.min(model.count, model.limit),
                            },
                        },
                    },
                }
            );
        },
        getSpreadsheetColumns() {
          // Return spreadsheet column details.ie., Total field details from tree view
            const fields = this.env.model.root.fields;
            return this.state.columns
                .filter(
                    (col) => col.type === "field" && fields[col.name].type !== "binary"
                    // We want to avoid binary fields
                )
                .map((col) => ({name: col.name, type: fields[col.name].type}));
        },
    }
);
