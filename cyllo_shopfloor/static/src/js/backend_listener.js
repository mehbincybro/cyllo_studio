/** @odoo-module **/

import { registry } from "@web/core/registry";

export const shopfloorBackendListener = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        bus_service.addChannel("shopfloor_channel");

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "workorder_updated") {

                    notification.add(
                        "A work order timer was just updated",
                        {
                            title: "Shop Floor Activity",
                            type: "warning",
                            sticky: false,
                        }
                    );

                }
            }
        });
    }
};

registry.category("services").add("shopfloor_backend_listener", shopfloorBackendListener);