/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class CompanyDetailsDialog extends Component {
    setup(){
        this.orm = useService("orm")
        this.action = useService("action")
    }

    async _onConfirm(){
        this.props.close()
        this.props.onConfirm()
    }
    /**
     * Handle the cancel action.
     */
    async _cancel() {
        this.props.close();
    }

}
// Define the template for the DeleteDialog component
CompanyDetailsDialog.template = "cyllo_dashboard.CompanyDetailsDialog"
// Define the components used in the DeleteDialog
CompanyDetailsDialog.components = { Dialog }
// Define default properties for the DeleteDialog component
CompanyDetailsDialog.defaultProps = {
    confirmLabel: _t("Confirm"),
    cancelLabel: _t("Cancel"),
    confirmClass: "btn-primary",
    onConfirm: () => {}
};
