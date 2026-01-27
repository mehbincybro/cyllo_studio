/** @odoo-module **/
// Import necessary modules and utilities from Odoo
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
const { onMounted } = owl;
// Patch the FormController prototype to add custom functionality
patch(FormController.prototype, {
    setup() {
        super.setup();
        // Execute the custom function when the component is mounted
        onMounted(() => {
            this.AddClassStyle();
        });
    },
    AddClassStyle() {
        /* Method to add class 'document-modal-content' for the parent element with class 'document_lock_wizard' to apply styles */
        const targetElement = this.__owl__.bdom.parentEl.parentElement.querySelector('.document_lock_wizard');
        if (targetElement) {
            // Add the 'document-modal-content' class to the closest '.modal-content' element
            targetElement.closest('.modal-content').classList.add("document-modal-content");
        }
    }
});
// Extend the components of FormController if needed (empty in this example)
FormController.components = {
    ...FormController.components,
};