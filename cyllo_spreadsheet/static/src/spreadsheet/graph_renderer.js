/** @odoo-module **/
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { patch } from "@web/core/utils/patch";
/**
 * Patching this components open a wizard and set data to add spreadsheet
 */
patch(
    GraphRenderer.prototype,
    {
        onSpreadsheetButtonClicked() {
            // Open wizard for adding spreadsheet and pass meta data
            this.actionService.doAction(
                "cyllo_spreadsheet.action_view_spreadsheet_spreadsheet_import",
                {
                    additionalContext: {
                        default_name: this.model.metaData.title,
                        default_import_data: {
                            mode: "graph",
                            metaData: JSON.parse(JSON.stringify(this.model.metaData)),
                            searchParams: JSON.parse(
                                JSON.stringify(this.model.searchParams)
                            ),
                        },
                    },
                }
            );
        },
    }
);
