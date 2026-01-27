/** @odoo-module **/
import {registry} from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const actionRegistry = registry.category("actions");
const {Component, onMounted, onWillStart, useSubEnv, useState, useRef} = owl;
import {ActionSpreadsheet} from "@cyllo_spreadsheet/spreadsheet/bundle/spreadsheet_action";
import { patch } from "@web/core/utils/patch";

patch(ActionSpreadsheet.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        onMounted(async() => {
            setTimeout(async () => {
                var spreadsheetID = this.spreadsheetId
                const canvas = await html2canvas(this.spreadsheetContainer.el?.querySelector('.o-group-grid'));
                let imgData = canvas.toDataURL('image/png');
                if (spreadsheetID) {
                    this.orm.write("spreadsheet.spreadsheet", [spreadsheetID], {
                        image_1920: imgData.split(',')[1]
                    });
                    var docFileId = await this.orm.read("spreadsheet.spreadsheet", [spreadsheetID], ['document_file_id']);
                    if (docFileId && docFileId[0].document_file_id[0]) {
                        this.orm.write("document.file", [docFileId[0].document_file_id[0]], {
                            excel_thumbnail: imgData.split(',')[1]
                        });
                    }
                }
            }, 50);
        });
    }
});