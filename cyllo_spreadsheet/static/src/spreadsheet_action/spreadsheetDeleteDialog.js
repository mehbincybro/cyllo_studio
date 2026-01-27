/** @odoo-module **/
import { DeleteDialog } from "@cyllo_spreadsheet/spreadsheet_action/deleteDialog";


export class SpreadsheetDeleteDialog extends DeleteDialog {
    // Function to handle confirmation of deletion
    async _confirm() {
        await this.orm.unlink(this.props.model, [this.props.id]);
        this.props.removeManually && this.props.removeManually()
        this.props.close()
        this.props.onConfirm()
    }
    static defaultProps = {
        ...DeleteDialog.defaultProps,
        callBackAction: false
    }
}
