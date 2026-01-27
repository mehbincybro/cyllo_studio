/** @odoo-module **/
import { useService} from "@web/core/utils/hooks";
import {SpreadsheetRenderer} from "@cyllo_spreadsheet/spreadsheet/bundle/spreadsheet_renderer";
import { patch } from "@web/core/utils/patch";
/**
*    Patching this components to save the spreadsheet content to the ir_attachment while editing the spreadsheet
*/
patch(
    SpreadsheetRenderer.prototype,
    {
        setup() {
             super.setup();
            this.actionService = useService("action");
        },
      onSpreadsheetSaved() {
      //Helps to add content of the spreadsheet to ir attachment while editing the spreadsheet
      let save_sheet = super.onSpreadsheetSaved()
        this.actionService.doAction({
        type: "ir.actions.client",
        tag: "action_share_spreadsheet",
        params: {
            name: this.props.record.name,
            xlsxData: this.spreadsheet_model.exportXLSX(),
            id: this.spreadsheetId
            },
        });
        return save_sheet
      },
    }
);
