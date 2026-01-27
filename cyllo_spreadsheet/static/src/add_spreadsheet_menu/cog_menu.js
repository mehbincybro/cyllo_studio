/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { AddMenuSpreadsheet } from "../add_spreadsheet_menu/add_menu_spreadsheet";
import { AddListSpreadsheet } from "../add_spreadsheet_menu/add_list_spreadsheet";
import { Component } from "@odoo/owl";
const cogMenuRegistry = registry.category("cogMenu");
/**
 * Component for adding cog menu items for spreadsheet
 */
export class SpreadsheetCogMenu extends Component {
    static template = "cyllo_spreadsheet.SpreadsheetCogMenu";
    static components = { Dropdown, AddMenuSpreadsheet, AddListSpreadsheet};
}
cogMenuRegistry.add(
    "spreadsheet-cog-menu",
    {
        Component: SpreadsheetCogMenu,
        groupNumber: 30,
        isDisplayed: ({ config, isSmall }) =>
            !isSmall && config.actionType === "ir.actions.act_window" && config.viewType !== "form",
    },
    { sequence: 1 }
);
export class SpreadsheetItem extends Component {
    static template = "cyllo_spreadsheet.SpreadsheetItem";
    static components = { Dropdown};
}
