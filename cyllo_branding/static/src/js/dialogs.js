/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
/*Patch the dialog box and changing the tittle*/
patch(Dialog.prototype,{
    setup() {
        super.setup(...arguments);
        if (this.props.title === "Odoo"){
            this.props.title = "Cyllo"
        }
    }
});