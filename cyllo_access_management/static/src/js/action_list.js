/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller"
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        const model = this.model.config.resModel;
        this.orm = useService('orm');
        onWillStart(async () => {
            this.profileFlags = await this.orm.call(
                "profile.management",
                "get_profile_flags",
                [], { model }
            )
            if (this.profileFlags.actions && this.profileFlags.actions.includes("export")) {
                this.env.config.hideExportAll = true;
            }
        });
    },

    get actionMenuItems() {
        const items = super.actionMenuItems;
        if (this.profileFlags.actions) {
            const actions = items.action.filter((item) => !this.profileFlags.actions.includes(item.key))
            items.action = actions
        }
        if (this.profileFlags.hide_actions) {
            delete items.action;
        }
        if (this.profileFlags.hide_print) {
            delete items.print;
        }
        return items;
    },

});

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        const model = this.model.config.resModel;
        onWillStart(async () => {
            this.profileFlags = await this.orm.call(
                "profile.management",
                "get_profile_flags",
                [], { model }
            )
        });
    },

    get actionMenuItems() {
        const items = super.actionMenuItems;
        if (this.profileFlags.actions) {
            const actions = items.action.filter((item) => !this.profileFlags.actions.includes(item.key))
            items.action = actions
        }
        if (this.profileFlags.hide_actions) {
            delete items.action;
        }
        if (this.profileFlags.hide_print) {
            delete items.print;
        }
        return items;
    },
});

const cogMenuRegistry = registry.category("cogMenu");
const exportAllItem = cogMenuRegistry.get("export-all-menu");
if (exportAllItem) {
    const originalIsDisplayed = exportAllItem.isDisplayed;
    exportAllItem.isDisplayed = async (env) => {
        if (env.config.hideExportAll) {
            return false;
        }
        return originalIsDisplayed ? await originalIsDisplayed(env) : true;
    };
}
