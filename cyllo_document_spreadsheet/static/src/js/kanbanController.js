/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { DocumentKanbanRecord } from "@cyllo_documents/js/kanban_record"
import { patch } from "@web/core/utils/patch";
/**
 * Patching this components open a wizard add spreadsheet
 */
patch(
    KanbanController.prototype,
    {
        setup() {
            super.setup();
            this.actionService = useService("action");
            this.orm = useService("orm");
        },
        _onClickSpreadsheet() {
         // Open wizard for creating spreadsheet
              this.actionService.doAction("cyllo_document_spreadsheet.action_view_create_spreadsheet"
            );
        },
        Select_Doc() {
        //Freeze the create spreadsheet button while clicking the select button
        let select_docs = super.Select_Doc()
        const elements = this.rootRef.el.querySelectorAll('.on_click_spreadsheet');
        elements.forEach((element) => {
            element.classList.add('disabled');
        });
        return select_docs
        },
        CancelSelect() {
        //Restore the functionality of create spreadsheet button while cancel the selection
        let cancel_select = super.CancelSelect()
        this.rootRef.el.querySelectorAll('.on_click_spreadsheet').forEach(element => {
            element.classList.remove('disabled');
            });
        return cancel_select
        }
    }
);
/**
 * Patching this components super function for opening a document added code for open an excel document.
 */
patch(
    DocumentKanbanRecord.prototype,
    {
        setup() {
            super.setup();
            this.actionService = useService("action");
            this.orm = useService("orm");
        },
        FileOpen(file, files = [file]) {
        // Open spreadsheet while clicking an excel document
        let file_open = super.FileOpen(file, files = [file])
        if (file.extension == "xlsx"){
            this.orm.call('document.file', "open_spreadsheet",[file]).then((result) =>{
                if (result){
                // Loading client action to open spreadsheet
                      this.actionService.doAction({
                            type: "ir.actions.client",
                            tag: "action_load_spreadsheet",
                            params: {
                                spreadsheet_id: result,
                                model: 'spreadsheet.spreadsheet',
                            },
                      });
                }
            });
        }
        return file_open
    }
});