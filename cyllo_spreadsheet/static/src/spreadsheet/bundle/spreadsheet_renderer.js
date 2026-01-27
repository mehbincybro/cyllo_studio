/** @odoo-module **/
import {Component} from "@odoo/owl";
import {DataSources} from "@spreadsheet/data_sources/data_sources";
import { Dialog } from "@web/core/dialog/dialog";
import {Field} from "@web/views/fields/field";
import { loadSpreadsheetDependencies } from "@spreadsheet/assets_backend/helpers";
import {migrate} from "@spreadsheet/o_spreadsheet/migration";
import * as spreadsheet from "@odoo/o-spreadsheet";
import {useService} from "@web/core/utils/hooks";
import {useSetupAction} from "@web/webclient/actions/action_hook";
import { registry } from "@web/core/registry";
const {Spreadsheet, Model} = spreadsheet;
const {useSubEnv, useState, onWillStart} = owl;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();
import {_lt } from "@web/core/l10n/translation";

export class SpreadsheetTransportService {
    constructor(orm, bus_service, model, res_id) {
        this.orm = orm;
        this.bus_service = bus_service;
        this.model = model;
        this.res_id = res_id;
        this.channel = "cyllo_spreadsheet;" + this.model + ";" + this.res_id;
        this.bus_service.addChannel(this.channel);
        this.bus_service.addEventListener(
            "notification",
            this.onNotification.bind(this)
        );
        this.listeners = [];
    }
    onNotification({detail: notifications}) {
        for (const {payload, type} of notifications) {
            if (
                type === "cyllo_spreadsheet" &&
                payload.res_model === this.model &&
                payload.res_id === this.res_id
            ) {
                // What shall we do if no callback is defined (empty until onNewMessage...) :/
                for (const {callback} of this.listeners) {
                    callback(payload);
                }
            }
        }
    }
    sendMessage(message) {
        this.orm.call(this.model, "send_spreadsheet_message", [[this.res_id], message]);
    }
    onNewMessage(id, callback) {
        this.listeners.push({id, callback});
    }
    leave(id) {
        this.listeners = this.listeners.filter((listener) => listener.id !== id);
    }
}

export const spreadsheetService = {
    dependencies: ["bus_service"],
    async start(env, { bus_service }) {
        return {
            bus_service: bus_service,
        };
    },
};
registry.category("services").add("spreadsheet_service", spreadsheetService);
/**
 * Component used for rendering the spreadsheet data
 */
export class SpreadsheetRenderer extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.bus_service = useService("spreadsheet_service").bus_service;
        this.user = useService("user");
        this.spreadsheetId = this.props.res_id
        const dataSources = new DataSources(this.env);
        this.state = useState({
            dialogDisplayed: false,
            dialogTitle: "Spreadsheet",
            dialogContent: undefined,
        });
        this.confirmDialog = this.closeDialog;
        this.spreadsheet_model = new Model(
            migrate(this.props.record.spreadsheet_raw),
            {
                evalContext: {env: this.env, orm: this.orm},
                transportService: new SpreadsheetTransportService(
                    this.orm,
                    this.bus_service,
                    this.props.model,
                    this.props.res_id
                ),

                client: {
                    id: uuidGenerator.uuidv4(),
                    name: this.user.name,
                },
                mode: this.props.record.mode,
                custom: {dataSources},
            },
            this.props.record.revisions
        );
        useSubEnv({
            saveSpreadsheet: this.onSpreadsheetSaved.bind(this),
            editText: this.editText.bind(this),
            askConfirmation: this.askConfirmation.bind(this),
            download_sheet: this.download_sheet.bind(this),
            raiseError : this.raiseError.bind(this)
        });
        onWillStart(async () => {
            await loadSpreadsheetDependencies();
            await dataSources.waitForAllLoaded();
            await this.env.importData(this.spreadsheet_model);
        });
        useSetupAction({
            beforeLeave: () => this.onSpreadsheetSaved(),
        });
        dataSources.addEventListener("data-source-updated", () => {
            const sheetId = this.spreadsheet_model.getters.getActiveSheetId();
            this.spreadsheet_model.dispatch("EVALUATE_CELLS", {sheetId});
        });
    }
    closeDialog() {
        this.state.dialogDisplayed = false;
        this.state.dialogTitle = "Spreadsheet";
        this.state.dialogContent = undefined;
    }
    onSpreadsheetSaved() {
    //Used to save the spreadsheet content
        const data = this.spreadsheet_model.exportData();
        this.env.saveRecord({spreadsheet_raw: data});
        this.spreadsheet_model.leaveSession();
    }
    editText(title, callback, options) {
        this.state.dialogContent = options.placeholder;
        this.state.dialogTitle = title;
        this.state.dialogDisplayed = true;
        this.confirmDialog = () => {
            callback(this.state.dialogContent);
            this.closeDialog();
        };
    }
    askConfirmation(content, confirm) {
    // Function that used to delete a sheet from spreadsheet
    this.spreadsheet_model.dispatch("DELETE_SHEET", { sheetId: this.spreadsheet_model.getters.getActiveSheetId()})
    }
    download_sheet(env){
    //Download sheet from the spreadsheet
       this.actionService.doAction({
            type: "ir.actions.client",
            tag: "action_download_spreadsheet",
            params: {
                name: this.props.record.name,
                xlsxData: this.spreadsheet_model.exportXLSX(),
            },
        });
    }
    raiseError(env){
    // Displays error sticky note while saving a sheet with empty name
    this.actionService.doAction({
            type: "ir.actions.client",
            tag: "display_notification",
            'params': {
                    type: 'danger',
                    sticky: false,
                    message : _lt(env),
            },
        });
    }
}
SpreadsheetRenderer.template = "cyllo_spreadsheet.SpreadsheetRenderer";
SpreadsheetRenderer.components = {
    Spreadsheet,
    Field,
    Dialog,
};
SpreadsheetRenderer.props = {
    record: Object,
    res_id: {type: Number, optional: true},
    model: String,
    importData: {type: Function, optional: true},
};
