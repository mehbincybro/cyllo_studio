/** @odoo-module **/

import {useRef, Component, useState, onWillStart, markup} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {UserMenu} from "@web/webclient/user_menu/user_menu";
import {useService} from "@web/core/utils/hooks";
import {browser} from "@web/core/browser/browser";
import {isMacOS} from "@web/core/browser/feature_detection";
import {session} from "@web/session";
import {_t} from "@web/core/l10n/translation";
import {escape} from "@web/core/utils/strings";
import {registry} from "@web/core/registry";

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
        this.orm = useService('orm');
        this.userId = session.uid

        this.state = useState({
            autoEdit: true,
        })
        onWillStart(async () => {
            await this.orm.call('res.users', 'get_auto_edit_value').then((result) => {
                this.state.autoEdit = result;
            });
        })
    },

    logOut() {
        localStorage.setItem('mainMenuVisibility', 'true')
        localStorage.setItem("cy_selected_app", false)
        localStorage.setItem("isSidebarOn", true)
        browser.location.href = "/web/session/logout";
    },

    shortCut() {
        this.env.services.command.openMainPalette({FooterComponent: ShortcutsFooterComponent});
    },

    handleClick(event) {
        event.stopPropagation()
    },

    async profile() {
        const actionDescription = await this.env.services.orm.call("res.users", "action_systray_view_account");
        actionDescription.res_id = this.env.services.user.userId
        this.env.services.action.doAction(actionDescription, {clearBreadcrumbs: true,});
    },

    get command() {
        return isMacOS() ? "Cmd + K" : "Ctrl + K"
    },

    async handleEdit(ev) {
        this.state.autoEdit = !this.state.autoEdit
        await this.orm.call('res.users', 'toggle_auto_edit', [this.state.autoEdit]).then(() => {
            this.env.services['action'].doAction('reload_context');
        });
    },
})

function documentationItem(env) {
    const documentationURL = "https://www.odoo.com/documentation/17.0";
    return {
        type: "item",
        id: "documentation",
        description: _t("Documentation"),
        href: documentationURL,
        callback: () => {
            browser.open(documentationURL, "_blank");
        },
        sequence: 10,
    };
}

function supportItem(env) {
    const url = session.support_url;
    return {
        type: "item",
        id: "support",
        description: _t("Support"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

function shortCutsItem(env) {
    const translatedText = _t("Shortcuts");
    return {
        type: "item",
        id: "shortcuts",
        hide: env.isSmall,
        description: markup(
            `<span>${escape(translatedText)}
                    <span class="badge badge-secondary ms-4">${isMacOS() ? "CMD" : "CTRL"}+K</span>
                    </span>
                    `
        ),
        callback: () => {
            env.services.command.openMainPalette({FooterComponent: ShortcutsFooterComponent});
        },
        sequence: 30,
    };
}

function separator() {
    return {
        type: "separator",
        sequence: 40,
    };
}

export function preferencesItem(env) {
    return {
        type: "item",
        id: "settings",
        description: _t("Preferences"),
        callback: async function () {
            const actionDescription = await env.services.orm.call("res.users", "action_get");
            actionDescription.res_id = env.services.user.userId;
            env.services.action.doAction(actionDescription);
        },
        sequence: 50,
    };
}

function odooAccountItem(env) {
    return {
        type: "item",
        id: "account",
        description: _t("My Odoo.com account"),
        callback: () => {
            env.services
                .rpc("/web/session/account")
                .then((url) => {
                    browser.open(url, "_blank");
                })
                .catch(() => {
                    browser.open("https://accounts.odoo.com/account", "_blank");
                });
        },
        sequence: 60,
    };
}

function logOutItem(env) {
    const route = "/web/session/logout";
    return {
        type: "item",
        id: "logout",
        description: markup(`<span><i class="ri-logout-box-r-line me-1"></i>Logout</span>`),
        href: `${browser.location.origin}${route}`,
        callback: () => {
            browser.location.href = route;
        },
        sequence: 70,
    };
}

registry
    .category("user_menuitems")
    .add("shortcuts", shortCutsItem, {force: true })
    .add("separator", separator, {force: true})
    .add("log_out", logOutItem, {force: true});
