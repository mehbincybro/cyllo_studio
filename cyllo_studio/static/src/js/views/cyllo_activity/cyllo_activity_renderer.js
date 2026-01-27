/** @odoo-module **/
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";
import { CylloActivityRecord } from "./cyllo_activity_record";
import { Component, onMounted, useState, onWillUnmount,onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ActivityPopover } from "@cyllo_studio/js/views/cyllo_activity/cyllo_activity_popover_dailog";
import { getFormattedRecord, getImageSrcFromRecordInfo, isHtmlEmpty } from "@web/views/kanban/kanban_record";

/**
 * CylloActivityRenderer
 *
 * Extends the base ActivityRenderer to trigger custom activity dialogs
 * and provide a temporary highlight message when the edit button is shown.
 */
export class CylloActivityRenderer extends ActivityRenderer {
	setup() {
		super.setup();
		this.rpc = useService('rpc');
		this.action = useService("action");
		this.dialog = useService("dialog");
        this._openDialog = this._openDialog.bind(this);

		onMounted(async() => {
		    this.env.bus.trigger("ACTIVITY_DETAILS", {
				archInfo: this.props.archInfo,
				model: this.props.resModel,
				viewId: this.env.config.viewId,
				viewType: this.env.config.viewType,
				type:'dialog_box',
				fields: this.props.fields,
				activityResIds: this.props.activityResIds,
				records: this.props.records,
			});
			const recordId = sessionStorage.getItem('ActivityRecordId')
            if (recordId && parseInt(recordId) === this.props.records[0].resId) {
                sessionStorage.removeItem('ActivityRecordId')
                this._openDialog();
            }
            this.env.bus.addEventListener('showActivityEdits', this._openDialog)
		});
		onWillUnmount(() => {
                this.env.bus.removeEventListener('showActivityEdits', this._openDialog)
            });
        onWillDestroy(()=>{
            this.env.bus.trigger("ACTIVITY_REMOVED", {
                activity:false
            })
          })
	}
	_openDialog() {
    this.dialog.add(ActivityPopover, {
            archInfo: this.props.archInfo,
            model: this.props.resModel,
            viewId: this.env.config.viewId,
            viewType: this.env.config.viewType,
            fields: this.props.fields,
            activityResIds: this.props.activityResIds,
            records: this.props.records,
        });
}

	/**
     * Show a temporary highlight message for the edit button
     */
	showEditButton(ev) {
		const editButton = document.querySelector('.cy-viewEdits').parentElement
		const editHighlight = editButton.querySelector('div')

		if (editButton && !editHighlight) {
			editButton.classList.add('edit-highlight')
			const messageDiv = document.createElement('div')
			messageDiv.className = 'cy-activity-edit-message';
			const spanElement = document.createElement('span');
			spanElement.textContent = 'Customise Activity Record';
			messageDiv.append(spanElement);
			editButton.append(messageDiv);

			setTimeout(() => {
				editButton.classList.remove('edit-highlight');
				if (editButton.contains(messageDiv)) {
					editButton.removeChild(messageDiv);
				}
			}, 3000);
		}
	}
}
CylloActivityRenderer.components = {
	...ActivityRenderer.components,
	CylloActivityRecord,
}
CylloActivityRenderer.template = "cyllo_studio.CylloActivityRenderer"