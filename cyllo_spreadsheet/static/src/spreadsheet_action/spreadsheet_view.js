/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, useRef } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DeleteDialog } from "@cyllo_spreadsheet/spreadsheet_action/deleteDialog";
import { ShareDialog } from "@cyllo_spreadsheet/spreadsheet_action/shareDialog";
import { ShareMultipleDialog } from "@cyllo_spreadsheet/spreadsheet_action/shareMultipleDialog";
import { AddMenuSpreadsheet } from "@cyllo_spreadsheet/add_spreadsheet_menu/add_menu_spreadsheet";
import { _t } from "@web/core/l10n/translation";


export class SpreadSheetView extends Component {
    setup(){
        super.setup(...arguments);
        this.spreadsheetRoot = useRef('spreadsheet_root')
        this.orm = useService('orm');
        this.action = useService("action");
        this.dialogService = useService("dialog")
        this.notification = useService("notification");
        this.state = useState({
            sheets: [],
            searchText: false,
            isSelectActive: false,
            selectedSheets: [],
            viewType: 'list',
            sheetData: []
        })
        onWillStart(async () => {
            if (browser.localStorage.getItem('viewType')){
                this.state.viewType = browser.localStorage.getItem('viewType')
            }
            this.state.sheets = await this.orm.searchRead("spreadsheet.spreadsheet", [],['id', 'name', 'owner_id', 'create_date', 'write_uid', 'image_1920']
            );
        });
    }
    openDialog() {
        this.spreadsheetRoot.el.querySelector('#fileid').click();
    }

    /**
     * Handles the file upload process.
     * Reads the selected file, converts it to base64, and creates a new record in the 'spreadsheet.spreadsheet' model.
     */
    async uploadFile() {
        var self = this;
        var selectedFile = $(this.__owl__.bdom.el).find(".fileInput").prop('files')[0]
        var reader = new FileReader();
        reader.onload = async function (event) {
            var fileContents = event.target.result;
            var base64String = btoa(fileContents);
            var file_name = selectedFile['name']
            if (!file_name.endsWith('.xlsx')) {
                self.notification.add(_t("Please upload a .xlsx file"), {
                        type: "danger",
                        title: _t("Invalid file format")
                    });
                return;
            }
            const newRecordData = {
                name: file_name,
                owner_id: session.uid,
                spreadsheet_data: base64String,
            };
            const newSheet = await self.orm.create("spreadsheet.spreadsheet", [newRecordData]);
            self.action.doAction({
                type: "ir.actions.client",
                tag: "action_load_spreadsheet",
                params: { spreadsheet_id: newSheet[0], model: 'spreadsheet.spreadsheet' },
            });
        }
        reader.readAsBinaryString(selectedFile);
    }

    /**
     * Handles the click event on a spreadsheet sheet.
     * If selection mode is active, toggles the selection state of the sheet.
     * If selection mode is inactive, loads the spreadsheet associated with the clicked sheet.
     *
     * @param {Event} event - The click event triggered by the user.
     * @param {Object} sheet - The sheet object representing the clicked spreadsheet sheet.
     * @returns {void}
     */
    onClickSheet(event, sheet) {
        const { selectedSheets, isSelectActive } = this.state;
        const sheetId = sheet.id;
        const isSelected = selectedSheets.includes(sheetId);
        if (!isSelectActive) {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "action_load_spreadsheet",
                params: { spreadsheet_id: sheetId, model: 'spreadsheet.spreadsheet' },
            });
        } else {
            const row = event.currentTarget;
            if (isSelected) {
                // Remove the class and sheet ID from the list
                row.classList.remove('cy-sheet-row-selected');
                this.state.selectedSheets = selectedSheets.filter(id => id !== sheetId);
                 if (this.state.viewType === 'grid') {
                    row.querySelector('.cyllo-sheet--file').classList.remove('cy-sheet-row-selected');
                    row.classList.remove('cy-sheet-grid-selected');
                }
            } else {
                // Add the class and sheet ID to the list
                row.classList.add('cy-sheet-row-selected');
                this.state.selectedSheets.push(sheetId);
                if (this.state.viewType === 'grid') {
                    row.classList.add('cy-sheet-grid-selected');
                    row.querySelector('.cyllo-sheet--file').classList.add('cy-sheet-row-selected');
                }
            }
        }
    }

    async createNewSheet() {
        const newRecordData = {
                name: 'Untitled Spreadsheet',
                owner_id: session.uid,
            };
        const newSheet = await this.orm.create("spreadsheet.spreadsheet", [newRecordData]);
        this.action.doAction({
            type: "ir.actions.client",
            tag: "action_load_spreadsheet",
            params: { spreadsheet_id: newSheet[0], model: 'spreadsheet.spreadsheet' },
        });
    }

    /**
     * Handles the deletion of a spreadsheet sheet or multiple selected sheets.
     * If one sheet is selected, prompts the user for confirmation before deleting it.
     * If multiple sheets are selected, prompts the user for confirmation and deletes them in bulk.
     *
     * @param {Object} sheet - The sheet object representing the sheet to be deleted (if only one is selected).
     * @returns {void}
     */
    onDeleteSheet(sheet) {
        const { selectedSheets } = this.state;
        if (this.state.selectedSheets.length > 0) {
            this.dialogService.add(DeleteDialog, {
                ids: selectedSheets,
                model: "spreadsheet.spreadsheet",
                title: 'Delete Sheets',
                body: `Are you sure you want to Delete the selected sheets?`,
                removeManually: () => {
                    this.state.sheets = this.state.sheets.filter(item => !this.state.selectedSheets.includes(item.id));
                    this.onCancelSelect()
                    this.notification.add(_t("Successfully Deleted"), {
                        type: "success",
                    });
                },
                cancelSelect: () => {
                    this.onCancelSelect()
                }
            });
        }
        else{
            this.dialogService.add(DeleteDialog, {
                id: sheet.id,
                model: "spreadsheet.spreadsheet",
                title: 'Delete Sheet',
                body: `Are you sure you want to Delete ${sheet.name} ?`,
                removeManually: () => {
                    this.state.sheets = this.state.sheets.filter(item => item.id !== sheet.id);
                    this.notification.add(_t("Successfully Deleted"), {
                        type: "success",
                    });
                }
            })
        }
    }
    /**
     * Handles the duplication of a spreadsheet sheet or multiple selected sheets.
     * If one sheet is selected, duplicates it.
     * If multiple sheets are selected, duplicates them in bulk.
     *
     * @param {Object} sheet - The sheet object representing the sheet to be duplicated (if only one is selected).
     * @returns {void}
     */
    async onDuplicateSheet(sheet){
        if (this.state.selectedSheets.length > 0){
            for (const sheetId of this.state.selectedSheets) {
                await this.orm.call('spreadsheet.spreadsheet', 'copy', [sheetId]);
            }
            this.onCancelSelect()
        }
        else{
            await this.orm.call('spreadsheet.spreadsheet', 'copy', [sheet.id])
        }
        this.notification.add(_t("Successfully Duplicated"), {
                        type: "success",
                    });
        this.state.sheets = await this.orm.searchRead("spreadsheet.spreadsheet", [],['id', 'name', 'owner_id', 'create_date', 'write_uid', 'image_1920'])
    }

    /**
     * Activates the selection mode for spreadsheet sheets.
     * Disables various elements related to sheet manipulation and displays cancel button.
     * Adds 'disabled' class to certain elements to prevent interaction during selection mode.
     *
     * @returns {void}
     */
    selectSheet(){
        this.state.isSelectActive = true
        this.spreadsheetRoot.el.querySelector('.btn_cancel').style.display = 'block';
        this.spreadsheetRoot.el.querySelector('.select_document').style.display = 'none';
        const elements = this.spreadsheetRoot.el.querySelectorAll(
            '.upload_sheet, .cy-sheet__search-input');
        elements.forEach((element) => {
            element.classList.add('disabled');
        });
    }

    /**
     * Deactivates the selection mode for spreadsheet sheets.
     * Clears selected sheets, removes selection classes, and hides cancel button.
     *
     * @returns {void}
     */
    onCancelSelect() {
        this.state.isSelectActive = false;
        const selectedRows = this.spreadsheetRoot.el.querySelectorAll('.cy-sheet-row-selected');
        selectedRows.forEach(row => row.classList.remove('cy-sheet-row-selected'));
        const selectedGrids = this.spreadsheetRoot.el.querySelectorAll('.cy-sheet-grid-selected');
        selectedGrids.forEach(row => row.classList.remove('cy-sheet-grid-selected'));

        this.state.selectedSheets = [];

        // Hide the cancel button and show the select button
        this.spreadsheetRoot.el.querySelector('.btn_cancel').style.display = 'none';
        this.spreadsheetRoot.el.querySelector('.select_document').style.display = 'block';
    }

    /**
     * Opens a dialog to share a single spreadsheet sheet.
     *
     * @param {Object} sheet - The sheet object representing the sheet to be shared.
     * @returns {void}
     */
    shareSheet(sheet) {
        this.dialogService.add(ShareDialog, {
            id: sheet.id,
            name: sheet.name,
        })
    }

    /**
     * Opens a dialog to share multiple spreadsheet sheets.
     *
     * @returns {void}
     */
    onShareMultipleSheet(){
        this.dialogService.add(ShareMultipleDialog, {
            ids: this.state.selectedSheets,
            onCancelSelect: () => {
                this.onCancelSelect()
            }
        })
    }

    /**
     * Toggles the view type of the spreadsheet.
     *
     * @param {string} type - The type of view to toggle to ('grid' or 'list').
     * @returns {void}
     */
    onToggleView(type) {
        this.state.viewType = type
        browser.localStorage.setItem("viewType", type);
        this.onCancelSelect()
    }

    /**
     * Handles the search operation for spreadsheet sheets.
     * Updates the search text in the component state.
     * Performs a search query with the provided search text and updates the list of sheets accordingly.
     *
     * @param {Event} ev - The event object representing the search operation triggered by the user.
     * @returns {void}
     */
    async onSearchSheet(ev) {
        this.state.searchText = ev.toLowerCase();
        const domain = [['name', 'ilike', '%' + this.state.searchText + '%']];
        this.state.sheets = await this.orm.searchRead("spreadsheet.spreadsheet", domain, ['id', 'name', 'owner_id', 'create_date','write_uid', 'image_1920'])
    }
}

SpreadSheetView.template = "SpreadSheetView";
SpreadSheetView.components = { Dropdown, DropdownItem, AddMenuSpreadsheet }
registry.category("actions").add("spreadsheet_view", SpreadSheetView);