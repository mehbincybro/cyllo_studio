/** @odoo-module **/
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
/**
 * Component for link menu to the spreadsheet
 */
export class AddMenuSpreadsheet extends Component {
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.dialogManager = useService("dialog");
        this.orm = useService("orm");
    }
     // Opening wizard for importing spreadsheet data
    linkToSpreadsheet() {
        const actionToLink = this.getViewDescription();
        this.actionService.doAction(
            "cyllo_spreadsheet.action_view_spreadsheet_spreadsheet_import",
            {
                additionalContext: {
                    default_name: this.env.config.getDisplayName(),
                    default_import_data: actionToLink,
                },
            }
        );
    }
     // Function that returns some meta data of current view
    getViewDescription() {
        const { resModel } = this.env.searchModel;
        const { views = [] } = this.env.config;
        const { context } = this.env.searchModel.getIrFilterValues();
        const action = {
            domain: this.env.searchModel.domain,
            context,
            modelName: resModel,
            views: views.map(([, type]) => [false, type]),
        };
        return {
            viewType: this.env.config.viewType,
            action,
        };
    }
}
AddMenuSpreadsheet.props = {};
AddMenuSpreadsheet.template = "cyllo_spreadsheet.AddMenuSpreadsheet";
AddMenuSpreadsheet.components = { DropdownItem };
