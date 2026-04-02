/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl";

class ShopFloorScreen extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = this.env.services.bus_service;

        this.state = useState({
            workcenters: [],
            selectedWorkcenter: null,
            selectedProduction: null,
            groupedWorkOrders: [],
            currentFilter: "ready",
        });

        this.lastSyncTime = Date.now();

        onWillStart(async () => {
            await this.fetchWorkcenters();
            this.busService.addChannel("shopfloor_channel");
            this._onBusNotification = this._onBusNotification.bind(this);
            this.busService.addEventListener("notification", this._onBusNotification);
        });

        this.timerInterval = setInterval(() => {
            const now = Date.now();
            const minutesSinceSync = (now - this.lastSyncTime) / 60000;

            for (const group of this.state.groupedWorkOrders) {
                for (const workOrder of group.workOrders) {
                    if (workOrder.is_user_working && this.state.selectedWorkcenter?.working_state !== "blocked") {
                        workOrder.display_duration = workOrder.base_duration + minutesSinceSync;
                    }
                }
            }
        }, 1000);

        onWillDestroy(() => {
            clearInterval(this.timerInterval);
            this.busService.removeEventListener("notification", this._onBusNotification);
        });
    }

    _onBusNotification({ detail: notifications }) {
        for (const { type, payload } of notifications) {
            if (type === "workorder_updated") {
                this.fetchWorkcenters();
                if (this.state.selectedWorkcenter && payload.workcenter_id === this.state.selectedWorkcenter.id) {
                    this.loadWorkOrders();
                }
            }
        }
    }

    async fetchWorkcenters() {
        this.state.workcenters = await this.orm.searchRead(
            "mrp.workcenter",
            [],
            ["id", "name", "code", "working_state"]
        );

        if (this.state.selectedWorkcenter) {
            const updatedWorkcenter = this.state.workcenters.find(
                (wc) => wc.id === this.state.selectedWorkcenter.id
            );
            if (updatedWorkcenter) {
                this.state.selectedWorkcenter = updatedWorkcenter;
            }
        }
    }

    async selectWorkcenter(workcenter) {
        this.state.selectedWorkcenter = workcenter;
        this.state.selectedProduction = null;
        await this.loadWorkOrders();
    }

    async loadWorkOrders() {
        if (!this.state.selectedWorkcenter) return;

        const domain = [
            ["workcenter_id", "=", this.state.selectedWorkcenter.id],
            ["state", "!=", "cancel"],
            ["production_state", "!=", "draft"],
        ];

        if (this.state.currentFilter === "ready") {
            domain.push(["state", "in", ["ready", "progress", "pending", "waiting"]]);
        } else if (this.state.currentFilter === "done") {
            domain.push(["state", "=", "done"]);
        }

        const rawWorkOrders = await this.orm.searchRead(
            "mrp.workorder",
            domain,
            [
                "id", "name", "production_id", "state", "duration", "is_user_working",
                "working_state", "product_id", "qty_production", "production_state"
            ]
        );

        this.lastSyncTime = Date.now();
        const grouped = {};

        for (const workOrder of rawWorkOrders) {
            const productionId = workOrder.production_id ? workOrder.production_id[0] : 0;
            const productionName = workOrder.production_id ? workOrder.production_id[1] : "Unknown MO";

            const rawProductName = workOrder.product_id ? workOrder.product_id[1] : "Unknown Product";
            const cleanProductName = rawProductName.replace(/^\[.*?\]\s*/, "");

            workOrder.base_duration = workOrder.duration || 0;
            workOrder.display_duration = workOrder.base_duration;

            if (!grouped[productionId]) {
                grouped[productionId] = {
                    production_id: productionId,
                    production_name: productionName,
                    product_name: cleanProductName,
                    qty: workOrder.qty_production || 0,
                    production_state: workOrder.production_state || "draft",
                    workOrders: [],
                };
            }
            grouped[productionId].workOrders.push(workOrder);
        }

        this.state.groupedWorkOrders = Object.values(grouped);
    }

    selectProduction(productionId) {
        this.state.selectedProduction = productionId;
    }

    clearProductionSelection() {
        this.state.selectedProduction = null;
    }

    clearSelection() {
        this.state.selectedWorkcenter = null;
        this.state.selectedProduction = null;
        this.state.groupedWorkOrders = [];
    }

    setFilter(filterValue) {
        this.state.currentFilter = filterValue;
        this.loadWorkOrders();
    }

    async blockWorkcenter(workcenterId, ev) {
        if (ev) ev.stopPropagation();
        this.action.doAction("mrp.act_mrp_block_workcenter_wo", {
            additionalContext: { default_workcenter_id: workcenterId },
            onClose: () => {
                this.fetchWorkcenters();
            },
        });
    }

    async unblockWorkcenter(workcenterId, ev) {
        if (ev) ev.stopPropagation();
        await this.orm.call("mrp.workcenter", "unblock", [workcenterId]);
        await this.fetchWorkcenters();
    }

    async startWorkOrder(workOrderId) {
        await this.orm.call("mrp.workorder", "button_start", [[workOrderId]]);
    }

    async pauseWorkOrder(workOrderId) {
        await this.orm.call("mrp.workorder", "button_pending", [[workOrderId]]);
    }

    async finishWorkOrder(workOrderId) {
        const action = await this.orm.call("mrp.workorder", "button_finish", [[workOrderId]]);

        if (action && action.type === "trigger_close_production") {
            await this.closeProduction(action.mo_id);
            return;
        }

        if (action && typeof action === "object" && action.type !== "ir.actions.act_window_close") {
            this.action.doAction(action, {
                onClose: () => {
                    this.loadWorkOrders();
                    this.fetchWorkcenters();
                },
            });
            return;
        }

        this.loadWorkOrders();
        this.fetchWorkcenters();
    }

    formatDuration(minutes) {
        if (!minutes || minutes < 0) return "00:00:00";
        const totalSeconds = Math.floor(minutes * 60);
        const hours = Math.floor(totalSeconds / 3600).toString().padStart(2, "0");
        const mins = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, "0");
        const secs = (totalSeconds % 60).toString().padStart(2, "0");
        return `${hours}:${mins}:${secs}`;
    }

    async actionOpenProduction(productionId) {
        if (!productionId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mrp.production",
            res_id: productionId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async actionOpenProductCatalog(productionId) {
        if (!productionId) return;
        this.action.doAction("cyllo_shopfloor.action_mrp_add_component_wizard", {
            additionalContext: { default_production_id: productionId },
            onClose: () => {
                this.loadWorkOrders();
            },
        });
    }

    async actionScrapComponent(productionId) {
        if (!productionId) return;
        this.action.doAction("cyllo_shopfloor.action_mrp_scrap_component_wizard", {
            additionalContext: { default_production_id: productionId },
            onClose: () => {
                this.loadWorkOrders();
            },
        });
    }

    async closeProduction(productionId) {
        if (!productionId) return;

        const action = await this.orm.call("mrp.production", "action_shopfloor_close_mo", [[productionId]]);

        if (action && typeof action === "object") {
            this.action.doAction(action, {
                onClose: () => {
                    this.loadWorkOrders();
                    this.fetchWorkcenters();
                },
            });
        } else {
            this.clearSelection();
            this.loadWorkOrders();
        }
    }

    async actionAddWorkOrder(productionId) {
        if (!productionId) return;
        this.action.doAction(
            {
                name: "Add Work Order",
                type: "ir.actions.act_window",
                res_model: "mrp.add.workorder.wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_production_id: productionId,
                    default_workcenter_id: this.state.selectedWorkcenter ? this.state.selectedWorkcenter.id : false,
                },
            },
            {
                onClose: () => {
                    this.loadWorkOrders();
                },
            }
        );
    }

    async actionRerouteWorkOrder(productionId) {
        if (!productionId) return;

        const group = this.state.groupedWorkOrders.find((g) => g.production_id === productionId);
        if (!group || group.workOrders.length === 0) return;

        const activeWorkOrder = group.workOrders.find((wo) => !["done", "cancel"].includes(wo.state));

        if (!activeWorkOrder) {
            this.env.services.notification.add("All work orders for this MO are already completed.", {
                type: "warning",
            });
            return;
        }

        this.action.doAction(
            {
                name: "Reroute Work Order",
                type: "ir.actions.act_window",
                res_model: "mrp.reroute.wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_workorder_id: activeWorkOrder.id,
                    default_production_id: productionId,
                },
            },
            {
                onClose: () => {
                    this.fetchWorkcenters();
                    this.loadWorkOrders();
                },
            }
        );
    }

    async viewWorksheet(workOrderId) {
        if (!workOrderId) return;
        const action = await this.orm.call("mrp.workorder", "action_show_shopfloor_worksheet", [[workOrderId]]);
        this.action.doAction(action);
    }
}

ShopFloorScreen.template = "cyllo_shopfloor.ShopfloorTemplate";
registry.category("actions").add("shopfloor_screen", ShopFloorScreen);