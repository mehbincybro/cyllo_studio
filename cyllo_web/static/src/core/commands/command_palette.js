/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { CommandPalette } from "@web/core/commands/command_palette";

patch(CommandPalette.prototype, {
    setup() {
        super.setup();
        this.menuService = useService("menu");
    },

    async executeCommand(command) {
        if (command.href) {
            const params = new URLSearchParams(command.href.split("#")[1]);
            let menu = params?.get("menu_id")
                        ? this.menuService.getMenuAsTree(params.get("menu_id"))
                        : false;
            if (menu?.id && menu?.appID) {
                this.env.bus.trigger("OPEN-MENU", menu)
            }
        }
        super.executeCommand(command)
    }
})
