/** @odoo-module **/

/**
 * ActivityPopover Component
 *
 * Handles displaying and editing fields in a Kanban activity record.
 * Supports drag & drop reordering, adding, editing, saving, and deleting fields.
 */
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Field } from "@web/views/fields/field";
import { Record } from "@web/model/record";
import { Component, useExternalListener, onMounted, onWillStart, useState ,onWillDestroy} from "@odoo/owl";
import { useViewCompiler } from "@web/views/view_compiler";
import { CylloActivityCompiler } from "./cyllo_activity_compiler";
import { Select } from "@web/core/tree_editor/tree_editor_components";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { CylloActivityRecord } from "./cyllo_activity_record";
import { handleUndoRedo } from "@cyllo_studio/js/utils/undo_redo_utils";

export class ActivityPopover extends Component {
	setup() {
		this.rpc = useService("rpc");
		this.action = useService("action");
		this.actionService = useService("action");
		this.addDialog = useOwnedDialogs();
		this.state = useState({
			string: "",
			selectedField: "",
			attribute: {},
			selectedFieldAttribute: "",
			fieldName: "",
			editable: false,
			path: "",
			showInvisible: this.props.invisible,
			item: {},
			widget: false
		})

        onWillDestroy(() => {
            if (this.save) {
            sessionStorage.setItem('ActivityRecordId', this.props.records[0]?.resId);
            }
            if (this.props.updateState) {
                    this.props.updateState("editButton", true);
                    this.props.updateState("edit", false);
            }
            });


		const { templateDocs } = this.props.archInfo;
		const templates = useViewCompiler(CylloActivityCompiler, templateDocs);
		this.recordTemplate = templates["activity-box"];

		onMounted(() => {
			const self = this;
			const container = document.querySelector(".cy-activity")
				.closest('.o_activity_record')
				.querySelector(':scope > * > * > *');
			const dBlockElements = container.querySelectorAll(".d-block");

			dBlockElements.forEach(element => {
				const cyXpath = element.getAttribute("cy-xpath");
			});
			const drake = dragula([container], {
					revertOnSpill: true,
					moves: (el, container, handle) => {
						return true
					},
				})
				.on('drop', async (el, target, source, sibling) => {
					const path = el.getAttribute("cy-xpath");
					const parent = target.getAttribute("cy-xpath");
					const sibling_path = sibling?.getAttribute("cy-xpath") || null;
					sibling_path || el.previousElementSibling?.getAttribute("cy-xpath");
					const position = sibling_path ? "before" : "after";
					self.env.services.ui.block();
					try {
						const response = await self.rpc("cyllo_studio/activity/move/field", {
							method: 'move_activity_field',
							view_id: this.props.viewId,
							model: this.props.model,
							path,
							position,
							sibling_path,
							parent,
						});
						if (response) {
							handleUndoRedo(response)
						}
					} finally {
						self.env.services.ui.unblock();
					}
					this.save=true
                    this.env.bus.trigger("RENDER_LOAD");
				})
		})
		this.env.bus.addEventListener('ActivityFieldDetails', (ev) => {
			this.state.widget = ev.detail.widget
			this.state.editable = true
			this.state.attribute = ev.detail.attributes,
            this.state.fieldName = ev.detail.fieldName,
            this.state.path = ev.detail.path
		});
	}

	get activityProps() {
	    state: this.state
	}

	get allFields() {
		const allFields = Object.entries(this.props.fields).map((field) => {
			return { label: field[1].string + ' (' + field[0] + ')', value: field[0] }
		})
		return allFields;
	}

	updatedField(v) {
		this.state.selectedField = v
	}

	get fieldsDisplay() {
		return [{ label: 'full', value: 'full'}, { label: 'right', value: 'right' }, { label: 'left', value: 'left' }];
	}

	get displayValue() {
		return this.state.attribute?.display || ""
	}

	updatedFieldDisplay(v) {
		this.state.selectedFieldAttribute = v
	}

	handleFieldBold(ev) {
		this.state.attribute.bold = ev.target.checked;
	}

	handleFieldMuted(ev) {
		this.state.attribute.muted = ev.target.checked;
	}

	onDiscard(){
	    this.state.editable = false;
	}

	async onSave() {
		this.env.services.ui.block();
		try {
			const response = await this.rpc("cyllo_studio/activity/save/field", {
				view_id: this.props.viewId,
				model: this.props.model,
				fieldDisplay: this.state.selectedFieldAttribute || this.state.attribute?.display,
				fieldBold: this.state.attribute.bold === "False" ? 'false' : this.state.attribute.bold,
				fieldMuted: this.state.attribute.muted,
				path: this.state.path,
			});
			if (response) {
				handleUndoRedo(response)
			}
		} finally {
			this.env.services.ui.unblock();
		}
        this.action.doAction("studio_reload");
        this.save=true
		this.state.editable = false;
	}

	async onDelete() {
		const fieldNodes = this.props.archInfo.fieldNodes;
		const nameExists = Object.keys(fieldNodes).filter(element => element.startsWith(this.state.fieldName));
		let isPathIncluded = nameExists.some(name => fieldNodes[name].MainPath.includes('/activity/field'));
		let fieldName = isPathIncluded ? "" : this.state.fieldName

		this.env.services.ui.block();
		try {
			const response = await this.rpc("cyllo_studio/activity/remove/field", {
				view_id: this.props.viewId,
				model: this.props.model,
				path: this.state.path,
				field_name: fieldName,
			});
			if (response) {
				handleUndoRedo(response)
			}
		} finally {
			this.env.services.ui.unblock();
		}
        this.action.doAction("studio_reload");
        this.save=true
		this.state.editable = false;
	}

	async addActivityField() {
		if (!this.state.selectedField) {
			return this.action.doAction({
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'message': 'Select a field',
					'type': 'warning',
					'sticky': false,
				}
			})
		}
		const container = document.querySelector(".o_activity_record")
		const path = container.firstElementChild.getAttribute('cy-xpath')

		const response = await this.rpc("cyllo_studio/add/activity/field", {
			method: 'add_activity_field',
			view_id: this.props.viewId,
			view_type: this.props.viewType,
			model: this.props.model,
			path,
			name: this.state.selectedField
		});
		if (response) {
			handleUndoRedo(response)
		}
		this.save = true
        this.env.bus.trigger("RENDER_LOAD");
//        this.action.doAction("studio_reload");
	}
}

ActivityPopover.components = {
	Dialog,
	Field,
	Record,
	Select,
	CylloStudioDropdown,
	CylloActivityRecord
};

ActivityPopover.template = "cyllo_studio.CylloActivityPopover";
