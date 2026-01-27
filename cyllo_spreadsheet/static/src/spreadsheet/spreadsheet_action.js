/** @odoo-module **/
import {loadSpreadsheetAction} from "@spreadsheet/assets_backend/spreadsheet_action_loader";
import {registry} from "@web/core/registry";
const actionRegistry = registry.category("actions");
/**
*    Add client action to the action registry
*/
const loadSpreadsheetActionLoad = async (env, context) => {
    // Load spreadsheet client action to the loadSpreadsheetAction function
    await loadSpreadsheetAction(
        env,
        "action_load_spreadsheet",
        loadSpreadsheetActionLoad
    );
    return {
        ...context,
        target: "current",
        tag: "action_load_spreadsheet",
        type: "ir.actions.client",
    };
};
actionRegistry.add("action_load_spreadsheet", loadSpreadsheetActionLoad);
