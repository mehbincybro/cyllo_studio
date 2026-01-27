/** @odoo-module **/
import { PivotDataSource } from "@spreadsheet/pivot/pivot_data_source";
import {SpreadsheetControlPanel} from "./spreadsheet_controlpanel";
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import {SpreadsheetRenderer} from "./spreadsheet_renderer";
import {registry} from "@web/core/registry";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";
import { ListDataSource } from "@spreadsheet/list/list_data_source";
import { buildViewLink } from "@spreadsheet/ir_ui_menu/odoo_menu_link_cell";
const { markdownLink } = spreadsheet.links;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();
const actionRegistry = registry.category("actions");
const {Component, onMounted, onWillStart, useSubEnv, useState, useRef} = owl;
/**
 * Component used for passing data to the spreadsheet
 */
export class ActionSpreadsheet extends Component {
    setup() {
        this.router = useService("router");
        this.orm = useService("orm");
        this.actionService = useService("action");
        const params = this.props.action.params || this.props.action.context.params;
        this.spreadsheetId = params.spreadsheet_id;
        this.model = params.model || "spreadsheet.spreadsheet";
        this.import_data = params.import_data || {};
        this.breadcrumbs = useState(this.env.config.breadcrumbs);
        this.spreadsheetContainer = useRef('spreadsheet-container')
        onMounted(async() => {
            this.router.pushState({
                spreadsheet_id: this.spreadsheetId,
                model: this.model,
            });
            setTimeout(async () => {
                var spreadsheetID = this.spreadsheetId
                const canvas = await html2canvas(this.spreadsheetContainer.el?.querySelector('.o-group-grid'));
                let imgData = canvas.toDataURL('image/png');
                if (spreadsheetID) {
                    this.orm.write("spreadsheet.spreadsheet", [spreadsheetID], {
                        image_1920: imgData.split(',')[1]
                    });
                }
            }, 50);
        });
        onWillStart(async () => {
            this.record =
                (await this.orm.call(
                    this.model,
                    "get_spreadsheet_data",
                    [[this.spreadsheetId]],
                    {context: {bin_size: false}}
                )) || {};
        });
        useSubEnv({
            saveRecord: this.saveRecord.bind(this),
            importData: this.importData.bind(this),
        });
    }
    async saveRecord(data) {
    // Save the changes in the spreadsheet
        if (this.record.mode === "readonly") {
            return;
        }
        if (this.spreadsheetId) {
            this.orm.call(this.model, "write", [this.spreadsheetId, data]);
        } else {
            this.spreadsheetId = await this.orm.call(this.model, "create", [data]);
            this.router.pushState({spreadsheet_id: this.spreadsheetId});
        }
        if (this.record.mode != "readonly") {
        }
    }
    importCreateOrReuseSheet(spreadsheet_model) {
    // Function that creates sheets
        var sheetId = spreadsheet_model.getters.getActiveSheetId();
        var row = 0;
        if (this.import_data.new === undefined && this.import_data.new_sheet) {
            sheetId = uuidGenerator.uuidv4();
            spreadsheet_model.dispatch("CREATE_SHEET", {
                sheetId,
                position: spreadsheet_model.getters.getSheetIds().length,
            });
            // We want to open the new sheet
            const sheetIdFrom = spreadsheet_model.getters.getActiveSheetId();
            spreadsheet_model.dispatch("ACTIVATE_SHEET", {
                sheetIdFrom,
                sheetIdTo: sheetId,
            });
        } else if (this.import_data.new === undefined) {
            row = spreadsheet_model.getters.getNumberRows(sheetId);
            var maxcols = spreadsheet_model.getters.getNumberCols(sheetId);
            var filled = false;
            while (row >= 0) {
                for (var col = maxcols; col >= 0; col--) {
                    if (
                        spreadsheet_model.getters.getCell(sheetId, col, row) !==
                            undefined &&
                        !spreadsheet_model.getters.getCell(sheetId, col, row).isEmpty()
                    ) {
                        filled = true;
                        break;
                    }
                }
                if (filled) {
                    break;
                }
                row -= 1;
            }
            row += 1;
        }
        return {sheetId, row};
    }
    async importGraphData(spreadsheet_model) {
    // Function to import graph data to spreadsheet
      var {sheetId, row} = this.importCreateOrReuseSheet(spreadsheet_model);
        const dataSourceId = uuidGenerator.uuidv4();
        const definition = {
            title: this.import_data.metaData.title,
            type: "odoo_" + this.import_data.metaData.mode,
            background: "#FFFFFF",
            stacked: this.import_data.metaData.stacked,
            metaData: this.import_data.metaData,
            searchParams: this.import_data.searchParams,
            dataSourceId: dataSourceId,
            legendPosition: "top",
            verticalAxisPosition: "left",
        };
        spreadsheet_model.dispatch("CREATE_CHART", {
            sheetId,
            id: dataSourceId,
            position: {
                x: 0,
                y: row,
            },
            definition,
        });
    }
    async importPivotData(spreadsheet_model) {
    //Function to import pivot data to spreadsheet
        var {sheetId, row} = this.importCreateOrReuseSheet(spreadsheet_model);
        const dataSourceId = uuidGenerator.uuidv4();
        const pivot_info = {
            metaData: {
                colGroupBys: this.import_data.metaData.colGroupBys,
                rowGroupBys: this.import_data.metaData.rowGroupBys,
                activeMeasures: this.import_data.metaData.activeMeasures,
                resModel: this.import_data.metaData.resModel,
                expandedColGroupBys: this.import_data.metaData.expandedColGroupBys,
                expandedRowGroupBys: this.import_data.metaData.expandedRowGroupBys,
            },
            searchParams: this.import_data.searchParams,
        };
        const dataSource = spreadsheet_model.config.custom.dataSources.add(
            dataSourceId,
            PivotDataSource,
            pivot_info
        );
        await dataSource.load();
        const {cols, rows, measures} = dataSource.getTableStructure().export();
        const table = {
            cols,
            rows,
            measures,
        };
        spreadsheet_model.dispatch("INSERT_PIVOT", {
            sheetId,
            col: 0,
            row: row,
            id: spreadsheet_model.getters.getNextPivotId(),
            table,
            dataSourceId,
            definition: pivot_info,
        });
    }
     async importListData(spreadsheet_model) {
     // Function to import tree view data to spreadsheet
        var {sheetId, row} = this.importCreateOrReuseSheet(spreadsheet_model);
        const dataSourceId = uuidGenerator.uuidv4();
        var list_info = {
            metaData: {
                resModel: this.import_data.metaData.model,
                columns: this.import_data.metaData.columns.map((column) => column.name),
                fields: this.import_data.metaData.fields,
            },
            searchParams: {
                domain: this.import_data.metaData.domain,
                context: this.import_data.metaData.context,
                orderBy: this.import_data.metaData.orderBy,
            },
            name: this.import_data.metaData.name,
        };
        const dataSource = spreadsheet_model.config.custom.dataSources.add(
            dataSourceId,
            ListDataSource,
            list_info
        );
        await dataSource.load();
        spreadsheet_model.dispatch("INSERT_ODOO_LIST", {
            sheetId,
            col: 0,
            row: row,
            id: spreadsheet_model.getters.getNextListId(),
            dataSourceId,
            definition: list_info,
            linesNumber: this.import_data.metaData.threshold,
            columns: this.import_data.metaData.columns,
        });
        const columns = [];
        for (let col = 0; col < this.import_data.metaData.columns.length; col++) {
            columns.push(col);
        }
        spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {sheetId, cols: columns});
    }
    async linkMenuSpreadsheet(spreadsheet_model){
    // Function to link menu to spreadsheet
        if (this.import_data.new === undefined) {
            const sheetId = spreadsheet_model.uuidGenerator.uuidv4();
            const sheetIdFrom = spreadsheet_model.getters.getActiveSheetId();
            spreadsheet_model.dispatch("CREATE_SHEET", {
                sheetId,
                position: spreadsheet_model.getters.getSheetIds().length,
            });
            spreadsheet_model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        }
        const viewLink = buildViewLink(this.import_data);
        spreadsheet_model.dispatch("UPDATE_CELL", {
            sheetId: spreadsheet_model.getters.getActiveSheetId(),
            content: markdownLink(this.import_data.name, viewLink),
            col: 0,
            row: 0,
        });
    };
    async importData(spreadsheet_model) {
    //Function to import data.Determine the import mode and calls the function
        if (this.import_data.mode === "pivot") {
            await this.importPivotData(spreadsheet_model);
        }
        if (this.import_data.mode === "graph") {
            await this.importGraphData(spreadsheet_model);
        }
        if (this.import_data.mode === "list") {
            await this.importListData(spreadsheet_model);
        }
        if (this.import_data.action){
        await this.linkMenuSpreadsheet(spreadsheet_model)
        }
    }
}
ActionSpreadsheet.template = "cyllo_spreadsheet.ActionSpreadsheet";
ActionSpreadsheet.components = {
    SpreadsheetRenderer,
    SpreadsheetControlPanel,
};
actionRegistry.add("action_load_spreadsheet", ActionSpreadsheet, {force: true});
