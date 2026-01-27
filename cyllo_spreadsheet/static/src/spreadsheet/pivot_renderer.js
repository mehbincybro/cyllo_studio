/** @odoo-module **/
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { patch } from "@web/core/utils/patch";
/**
 * Patching this components open a wizard and set data to add spreadsheet
 */
patch(
    PivotRenderer.prototype,
    {
        onSpreadsheetButtonClicked() {
            // Open wizard for adding spreadsheet and pass meta data
            this.actionService.doAction(
                "cyllo_spreadsheet.action_view_spreadsheet_spreadsheet_import",
                {
                    additionalContext: {
                        default_name: this.model.metaData.title,
                        default_import_data: {
                            mode: "pivot",
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
