/** @odoo-module **/
/**
 * Patch the Odoo Form StatusBarButtons to enable Studio button editing features.
 *
 * This module allows:
 * - Adding, moving, and editing custom buttons in Studio.
 * - Handling drag-and-drop reordering of buttons.
 * - Tracking editing states for normal buttons, smart buttons, and new buttons.
 * - Communicating changes via the Odoo event bus.
 *
 * Uses Owl hooks: useState, useRef, onMounted, and Odoo services for notifications and RPC.
 */
import {
    StatusBarButtons
} from '@web/views/form/status_bar_buttons/status_bar_buttons';
import {
    patch
} from '@web/core/utils/patch';
const {
    useRef,
    useState,
    onMounted
} = owl;
import {
    useService
} from "@web/core/utils/hooks";
import {
    useBus
} from "@web/core/utils/hooks";
import {
    validateEdit
} from "@cyllo_studio/js/root/studio_wrapper";


patch(StatusBarButtons.prototype, {
    setup() {
        super.setup();
        this.notification = useService("effect");
        this.state = useState({
            isVisible: true,
            hasSheet: true,
            isEditingButton: false,
            isEditingSmartButton: false,
            isStudioEdit: false,
            isEditingNewButton:false,
        });
        this.buttonRef = useRef('cy-Button');
        onMounted(() => this.onMounted());
        useBus(this.env.bus, 'REMOVE_BUTTON_PROPERTIES', ({ detail }) => {
            this.state.hasSheet = true
            this.state.isVisible = true
        });
        this.env.bus.addEventListener("SMART_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingSmartButton = detail.isEditingSmartButton
        })
        this.env.bus.addEventListener("STUDIO_EDIT_STARTED", ({ detail }) => {
            this.state.isStudioEdit = detail.isStudioEdit
        })
        this.env.bus.addEventListener("NEW_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingNewButton = detail.isEditingNewButton
        })
    },

    onMounted() {
        const sheet = document.querySelector('.o_form_sheet')?.getAttribute('sheet')
        if (sheet) {
            this.state.hasSheet = false
        }
        const self = this
        const button = this.buttonRef.el
        var drake = dragula([this.buttonRef.el], {
                revertOnSpill: true,
                moves: (el, container, handle) => {
                    return !el.classList.contains('cy-add-button');
                },
                accepts: (el, target, source, sibling) => {
                    return sibling
                }
            })
            .on('drop', async function(el, target, source, sibling) {
                const buttonPath = el.getAttribute('cy-xpath');
                const siblingPath = sibling.getAttribute('cy-xpath')
                const path = siblingPath || '/form/header';
                const position = siblingPath ? 'before' : 'inside';
                self.env.services.ui.block();
                try {
                    const response = await self.env.model.rpc("cyllo_studio/move/button", {
                        method: 'move_button',
                        kwargs: {
                            path,
                            position,
                            buttonPath,
                            model: self.env.model.action.currentController.action.res_model,
                            view_id: self.env.config.viewId,
                            view_type: self.env.config.viewType,
                        }
                    })
                    if (response) {
                        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                        let cleanedStr = response.replace(/\s+/g, ' ').trim();
                        storedArray.push(cleanedStr)
                        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                        sessionStorage.setItem('ReDO', JSON.stringify([]));
                    }
                } finally {
                    self.env.services.ui.unblock();
                }
                self.env.model.action.doAction('studio_reload')
            });
    },

    async addNewButton() {
        const notification = this.notification || useService("notification");

        if (
            !validateEdit(this.state, notification, "isEditingButton", "ButtonNew")||
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button") ||
            !validateEdit(this.state, notification, "isEditingNewButton", "EditingNewButton") ||
            !validateEdit(this.state, notification, "isStudioEdit", "EditingButton")
        ) {
            return;
        }
        const header = this.buttonRef.el.closest('.o_form_statusbar');
        const newHeader = header?.getAttribute('studio-header');
        const cyXpath = header?.getAttribute('cy-xpath');

        if (!header) return;
        this.state.isEditingButton = true;
        this.env.bus.trigger('BUTTON_EDIT_STARTED',{
             isEditingButton : this.state.isEditingButton
        });

        // Hide menu or toolbar if needed
        this.state.isVisible = false;

        this.env.bus.trigger('BUTTON_DETAILS', {
            type: "ButtonProperties",
            path: cyXpath || "",
            position: "inside",
            create: false,
            newButton: true,
            newHeader,
        });
    },
});
StatusBarButtons.template = 'cyllo_studio.Button'