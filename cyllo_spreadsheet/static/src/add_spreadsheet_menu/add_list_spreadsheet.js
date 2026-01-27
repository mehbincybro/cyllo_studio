/** @odoo-module **/
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";
/**
 * Component for adding list on the spreadsheet from list view
 */
export class AddListSpreadsheet extends Component {
    linkToSpreadsheet() {
        this.env.bus.trigger("addListOnSpreadsheet");
    }
}
AddListSpreadsheet.props = {};
AddListSpreadsheet.template = "cyllo_spreadsheet.AddListSpreadsheet";
AddListSpreadsheet.components = { DropdownItem };
