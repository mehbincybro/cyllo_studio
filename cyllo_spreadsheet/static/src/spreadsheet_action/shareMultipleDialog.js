/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";


export class ShareMultipleDialog extends Component {
    setup(){
        // Initialize necessary services and references
        this.orm = useService("orm")
        this.action = useService("action")
        this.notification = useService("notification");
        this.state = useState({
            contributors: [],
            readers: []
        })
    }

    /**
     * Handles the removal of a reader from the list of readers selected in share dialog.
     *
     * @param {Object} rec - The reader object to be removed.
     * @returns {void}
     */
    onRemoveReader(rec) {
        const indexToRemove = this.state.readers.findIndex(reader => reader.id === rec.id);
        if (indexToRemove !== -1) {
            this.state.readers.splice(indexToRemove, 1);
        }
    }
    /**
     * Handles the removal of a contributor from the list of contributors selected in share dialog.
     *
     * @param {Object} rec - The contributor object to be removed.
     * @returns {void}
     */
    onRemoveContributor(rec) {
        const indexToRemove = this.state.contributors.findIndex(contributor => contributor.id === rec.id);
        if (indexToRemove !== -1) {
            this.state.contributors.splice(indexToRemove, 1);
        }
    }

    /**
     * Handles the selection of a contributor and adds it to the list of contributors.
     *
     * @param {Object} ev - The event object containing the selected contributor.
     * @returns {void}
     */
    onContributorSelect(ev){
        if(!this.state.contributors.some(contributor => contributor.id === ev[0].id)){
            this.state.contributors.push(ev[0])
        }
    }

    /**
     * Handles the selection of a reader and adds it to the list of readers.
     *
     * @param {Object} ev - The event object containing the selected reader.
     * @returns {void}
     */
    onReaderSelect(ev){
        if(!this.state.readers.some(reader => reader.id === ev[0].id)){
            this.state.readers.push(ev[0])
        }
    }

    /**
     * Handles the confirmation of sharing action.
     * Collects contributor and reader IDs and calls the share_sheet_multiple function for each sheet.
     * Triggers notification of successful sharing, executes onCancelSelect, close, and onConfirm props.
     *
     * @returns {void}
     */
    async _onConfirm(){
        const contributorIds = this.state.contributors.map(contributor => contributor.id);
        const readerIds = this.state.readers.map(reader => reader.id);
        for (const sheetId of this.props.ids) {
            this.orm.call('spreadsheet.spreadsheet', 'share_sheet_multiple', [this.props.ids, contributorIds, readerIds])
        }
        this.props.onCancelSelect && this.props.onCancelSelect()
        this.notification.add(_t("Successfully Shared"), {
                        type: "success",
                    });
        this.props.close()
        this.props.onConfirm()
    }
    // Function to handle close action
    async onClose() {
        this.props.onCancelSelect && this.props.onCancelSelect()
        this.props.close();
    }
}
ShareMultipleDialog.template = "cyllo_spreadsheet.ShareMultipleDialog"
ShareMultipleDialog.components = { Dialog, Many2XAutocomplete }
ShareMultipleDialog.defaultProps = {
    confirmLabel: _t("Confirm"),
    cancelLabel: _t("Cancel"),
    confirmClass: "btn-primary",
    onConfirm: () => {}
};
