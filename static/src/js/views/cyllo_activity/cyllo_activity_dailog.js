/** @odoo-module **/

/**
 * ActivityDialog Component
 *
 * Opens a dialog to display activity records for a specific model.
 * If there are no activity records, shows a warning notification.
 */
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted, useState } from "@odoo/owl";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import { CylloActivityRecord } from "./cyllo_activity_record";
import { DisplayNotification } from "@cyllo_studio/js/utils/display_notification";
import { ActivityPopover } from "./cyllo_activity_popover_dailog";


export class ActivityDialog extends Component {
	setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.addDialog = useOwnedDialogs();

        onMounted(() => {
            if (this.props.records?.length) {
                this.dialogService.add(ActivityPopover, {
                    archInfo: this.props.archInfo,
                    fields: this.props.fields,
                    activityResIds: this.props.activityResIds,
                    records: this.props.records,
                    model: this.props.model,
                    viewId: this.props.viewId,
                    viewType: this.props.viewType,
                    updateState : this.props.updateState
                });
            }
            else {
                return DisplayNotification(this, {
                    message: 'No Activity Records !!',
                    type: 'warning',
                    sticky: false,
                });
            }
        });
    }
}

ActivityDialog.components = {
	Dialog,
	Record,
	CylloActivityRecord,
	ActivityPopover
};
ActivityDialog.template = "cyllo_studio.CylloActivityDialog";