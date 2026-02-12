/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";

export const debugNotificationService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        if (session.debug_denied) {
            notification.add(_t("Debug mode is restricted by your administrator."), {
                type: "warning",
                sticky: false,
            });
        }
    },
};

registry.category("services").add("debug_notification", debugNotificationService);
