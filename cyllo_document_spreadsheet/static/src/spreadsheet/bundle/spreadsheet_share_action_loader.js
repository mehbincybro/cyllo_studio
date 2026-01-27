/** @odoo-module */
import { registry } from "@web/core/registry";
const actionRegistry = registry.category("actions");
import { jsonrpc } from "@web/core/network/rpc_service";
/**
 * Function that pass spreadsheet data to the controller for add attachment
 */
async function downloadSpreadsheetXlsx(env, action) {
    let { name, xlsxData,id } = action.params;
     jsonrpc("/spreadsheet/create/xlsx", {
                name: `${name}.xlsx`,
                files: JSON.stringify(xlsxData.files),
                id:id,
                }).then(function (result){
                    });
     }
actionRegistry.add("action_share_spreadsheet", downloadSpreadsheetXlsx, { force: true });
