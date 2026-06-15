/** @odoo-module **/

/**
 * RibbonProperties Component
 *
 * Provides the properties sidebar for a Kanban ribbon element in Studio.
 * Allows editing the ribbon's label, color, visibility, and domain conditions.
 * Integrates with ExpressionEditorDialog for domain expressions.
 */
const { Component, useState, onMounted, useExternalListener } = owl;
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { handleUndoRedo } from "@cyllo_studio/js/utils/undo_redo_utils";
import { _t } from "@web/core/l10n/translation";

export class RibbonProperties extends Component {
    static template = 'cyllo_studio.RibbonProperties';

    setup() {
        this.addDialog = useOwnedDialogs();
        this.notification = useService('effect');
        this.action = useService('action');
        this.rpc = useService('rpc');

        this.state = useState({
            showDropdown: false
        });

        this.properties = useState({
            string: '',
            color: 'text-bg-danger',
            invisible: 'False',
        });

        this.saveHandled = false;
        onMounted(() => {
            this.action_area = document.querySelector(".o_action_manager")
        });
    }
    /**
    * Automatically saves the current ribbon properties via RPC.
    * Shows a warning if the label is empty.
    *
    * @param {Event} ev - The triggering event (mousedown or click)
    */
    async handleAutoSave(ev) {
        if (!this.properties.string) {
            return this.notification.add({
                title: _t("Validation Error"),
                message: "Unable to save the ribbon.",
                description: "Please provide a label to save",
                type: "notification_panel",
                notificationType: "warning",
            });
        }
        if (ev.type === 'mousedown') {
            this.saveHandled = true;
        } else if (ev.type === 'click' && this.saveHandled) {
            this.saveHandled = false;
            return;
        }
        this.env.services.ui.block();
        try {
            const viewType = this.props.viewDetails.viewType;
            const endpoint = viewType === "form"
                ? "cyllo_studio/form/add/ribbon"
                : "cyllo_studio/kanban/add/ribbon";

            // Get the ribbon element for form-specific properties
            const ribbonElement = this.props.element;
            let requestData = {
                path: this.props.properties.elementInfo.path,
                position: this.props.properties.elementInfo.position,
                ...this.props.viewDetails,
                properties: { ...this.properties },
                viewType: this.props.viewDetails.viewType,
                viewId: this.props.viewDetails.viewId,
                model: this.props.viewDetails.model,
            };

            // For form view updates
            if (viewType === "form") {
                requestData = {
                    viewType: this.props.viewDetails.viewType,
                    viewId: this.props.viewDetails.viewId,
                    model: this.props.viewDetails.model,
                    path: this.props.properties.elementInfo.path,
                    properties: { ...this.properties },
                    position: this.props.properties.elementInfo.position,
                    ...this.props.viewDetails,
                };
            }
            console.log("res", requestData["path"])

            const response = await this.rpc(endpoint, requestData);

            if (response) {
                handleUndoRedo(response);
            }
            this.env.bus.trigger("CLEAR-MENU");
            if (viewType === "form") {
                this.action.doAction("studio_reload");
            }
        } catch (error) {
            console.error("Error saving ribbon:", error);
            this.notification.add({
                title: _t("Error"),
                message: "Failed to save ribbon",
                description: error.message || "An unexpected error occurred",
                type: "notification_panel",
                notificationType: "danger",
            });
        } finally {
            this.env.services.ui.unblock();
        }
        //    this.action.doAction("studio_reload");
    }

    /**
     * Cancels ribbon editing and closes the sidebar.
     *
     * @param {Event} ev - Triggering event
     */
    async cancelribbon(ev) {
        this.env.bus.trigger("CLEAR-MENU");
        this.action.doAction('studio_reload');
    }
    /**
     * Returns the available color options for ribbons.
     */
    get colors() {
        return {
            'text-bg-primary': 'Primary',
            'text-bg-secondary': 'Secondary',
            'text-bg-success': 'Success',
            'text-bg-info': 'Info',
            'text-bg-warning': 'Warning',
            'text-bg-danger': 'Danger'
        };
    }

    /**
     * Handles selecting a color for the ribbon.
     *
     * @param {string} color - CSS class representing the color
     */
    handleSelectColor(color) {
        //        console.log("Selected color:", color);
        //        this.properties.color = color;
        //        this.state.showDropdown = false;
        //        this.props.element.firstChild.className = color;
        let span = this.props.element.querySelector("span");
        if (!span) {
            span = document.createElement("span");
            this.props.element.appendChild(span);
        }
        span.className = color;

        this.properties.color = color;
        this.state.showDropdown = false;
        this.props.element.firstChild.className = color;
    }

    /**
     * Updates the ribbon's label text.
     *
     * @param {Event} event - Input change event
     */
    handleLabelChange({ target }) {
        //        this.props.element.firstChild.textContent = target.value;
        //        this.properties.string = target.value;
        let span = this.props.element.querySelector("span");

        if (!span) {
            span = document.createElement("span");
            span.className = this.properties.color || "text-bg-danger";
            this.props.element.appendChild(span);
        }
        span.textContent = target.value;
        this.properties.string = target.value;
    }

    /**
     * Adds or removes click/mousedown listeners for auto-saving.
     *
     * @param {boolean} isAdd - True to add listeners, false to remove
     */
    handleListener(isAdd = true) {
        if (isAdd) {
            document.addEventListener("click", this.AutoSave, { capture: true });
            document.addEventListener("mousedown", this.AutoSave, { capture: true });
        } else {
            document.removeEventListener("click", this.AutoSave, { capture: true });
            document.removeEventListener("mousedown", this.AutoSave, { capture: true });
        }
    }

    /**
     * Updates the ribbon's visibility based on domain radio selection.
     *
     * @param {Event} target - Radio input event
     */
    onDomainRadioClick({ target }) {
        this.properties.invisible = target.checked ? 'True' : 'False'
    }
    /**
     * Opens the ExpressionEditorDialog for editing the ribbon's domain expression.
     *
     * @param {Event} target - Click event
     */
    async onDomainClick({ target }) {
        this.handleListener(false)
        this.addDialog(ExpressionEditorDialog, {
            resModel: this.props.viewDetails.model,
            fields: this.props.viewDetails.allFields,
            expression: this.properties.invisible,
            onConfirm: (expression) => this.handleDomain(expression),
            onClose: () => this.handleListener(),
        });
    }
    /**
     * Handles updating the domain expression after editing.
     *
     * @param {string} expression - The new domain expression
     */
    handleDomain(expression) {
        this.handleListener()
        this.properties.invisible = expression
    }

}
