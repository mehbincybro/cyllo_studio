/** @odoo-module **/
import {loadSpreadsheetAction} from "@spreadsheet/assets_backend/spreadsheet_action_loader";
import {registry} from "@web/core/registry";
const actionRegistry = registry.category("actions");
/**
*    Add share client action to the action registry
*/
const loadSpreadsheetActionXlsx = async (env, context) => {
    await loadSpreadsheetAction(
        env,
        "action_share_spreadsheet",
        loadSpreadsheetActionOcaXlsx
    );
    return {
        ...context,
        target: "current",
        tag: "action_share_spreadsheet",
        type: "ir.actions.client",
    };
};
actionRegistry.add("action_share_spreadsheet", loadSpreadsheetActionXlsx);
