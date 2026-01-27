/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
const { useRef, Component } = owl
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { browser } from "@web/core/browser/browser";
import { isMacOS } from "@web/core/browser/feature_detection";

class ShortcutsFooterComponent extends Component {
    setup() {
        this.runShortcutKey = isMacOS() ? "CONTROL" : "ALT";
    }
}

ShortcutsFooterComponent.template = "web.UserMenu.ShortcutsFooterComponent";

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        this.dropdown = useRef("dropdown")
    },
    logOut() {
        localStorage.setItem('mainMenuVisibility', 'true')
        localStorage.setItem("cy_selected_app", false)
        browser.location.href = "/web/session/logout";
    },
    shortCut() {
        this.env.services.command.openMainPalette({FooterComponent: ShortcutsFooterComponent});
    },
    handleClick(event) {
        event.stopPropagation()
    },
    async profile() {
        const actionDescription = await this.env.services.orm.call("res.users", "action_get");
        actionDescription.res_id = this.env.services.user.userId;
        this.env.services.action.doAction(actionDescription);
    },
    get command() {
        return isMacOS() ? "Cmd + K" : "Ctrl + K"
    },
})