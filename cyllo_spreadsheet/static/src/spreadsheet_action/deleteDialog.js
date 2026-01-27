/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";


export class DeleteDialog extends Component {
    // This is a class for delete dialog box that is shown when trying to delete a sheet
    setup(){
        // Initialize necessary services and references
        this.orm = useService("orm")
        this.action = useService("action")
    }

    /**
     * Handles the confirmation action, which typically involves deletion of one or more records.
     * If multiple record IDs are provided in props, unlinks each record from the database.
     * Otherwise, unlinks the single record identified by 'id' in props.
     * Executes the removeManually callback, if provided.
     * Closes the dialog and executes the onConfirm callback.
     *
     * @returns {void}
     */
    async _onConfirm(){
        if (this.props.ids){
            for (const id of this.props.ids) {
                await this.orm.unlink(this.props.model, [id]);
            }
        }
        else{
            await this.orm.unlink(this.props.model, [this.props.id]);
        }
        this.props.removeManually && this.props.removeManually()
        this.props.close()
        this.props.onConfirm()
    }
    /**
     * Handle the close action.
     */
    async _onClose() {
        this.props.cancelSelect && this.props.cancelSelect()
        this.props.close();
    }

}
// Define the template for the DeleteDialog component
DeleteDialog.template = "cyllo_spreadsheet.DeleteDialog"
// Define the components used in the DeleteDialog
DeleteDialog.components = { Dialog }
// Define default properties for the DeleteDialog component
DeleteDialog.defaultProps = {
    confirmLabel: _t("Confirm"),
    cancelLabel: _t("Cancel"),
    confirmClass: "btn-primary",
    title: _t("Delete"),
    body: _t("Are you sure you want to delete this sheet ?"),
    onConfirm: () => {}
};
