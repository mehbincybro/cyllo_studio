/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl";

class ShopfloorScreen extends Component {
    setup() {
        this.orm = useService("orm");
        this.busService = this.env.services.bus_service;

        this.state = useState({
            workcenters: [],
            selectedWorkcenter: null,
            selectedMO: null,
            groupedWorkOrders: []
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
                for (const wo of group.workOrders) {
                    // Freeze visual timer if the parent workcenter is blocked
                    if (wo.is_user_working && this.state.selectedWorkcenter?.working_state !== 'blocked') {
                        wo.display_duration = wo.base_duration + minutesSinceSync;
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
        for (const { payload, type } of notifications) {
            if (type === "workorder_updated") {
                this.fetchWorkcenters(); // Keep workcenter block status synced
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

        // Keep the selected workcenter's state completely in sync
        if (this.state.selectedWorkcenter) {
            const updatedWC = this.state.workcenters.find(wc => wc.id === this.state.selectedWorkcenter.id);
            if (updatedWC) {
                this.state.selectedWorkcenter = updatedWC;
            }
        }
    }

    async selectWorkcenter(workcenter) {
        this.state.selectedWorkcenter = workcenter;
        this.state.selectedMO = null;
        await this.loadWorkOrders();
    }

    async loadWorkOrders() {
        if (!this.state.selectedWorkcenter) return;

        const rawWorkOrders = await this.orm.searchRead(
            "mrp.workorder",
            [["workcenter_id", "=", this.state.selectedWorkcenter.id], ["state", "!=", "cancel"]],
            ["id", "name", "production_id", "state", "duration", "is_user_working", "working_state",
             "product_id", "qty_production", "production_state"]
        );

        this.lastSyncTime = Date.now();

        const grouped = {};
        for (const wo of rawWorkOrders) {
            const moId = wo.production_id ? wo.production_id[0] : 0;
            const moName = wo.production_id ? wo.production_id[1] : "Unknown MO";

            wo.base_duration = wo.duration || 0;
            wo.display_duration = wo.base_duration;

            if (!grouped[moId]) {
                grouped[moId] = {
                    mo_id: moId,
                    mo_name: moName,
                    product_name: wo.product_id ? wo.product_id[1] : "Unknown Product",
                    qty: wo.qty_production || 0,
                    mo_state: wo.production_state || 'draft',
                    workOrders: []
                };
            }
            grouped[moId].workOrders.push(wo);
        }

        this.state.groupedWorkOrders = Object.values(grouped);
    }

    selectMO(moId) { this.state.selectedMO = moId; }
    clearMOSelection() { this.state.selectedMO = null; }
    clearSelection() {
        this.state.selectedWorkcenter = null;
        this.state.selectedMO = null;
        this.state.groupedWorkOrders = [];
    }

    // --- WORKCENTER BLOCKING ---
    async blockWorkcenter(wcId, ev) {
        if (ev) ev.stopPropagation(); // Prevents click from accidentally opening the workcenter
        await this.orm.call("mrp.workcenter", "button_block_custom", [wcId]);
        await this.fetchWorkcenters();
    }

    async unblockWorkcenter(wcId, ev) {
        if (ev) ev.stopPropagation();
        await this.orm.call("mrp.workcenter", "unblock_custom", [wcId]);
        await this.fetchWorkcenters();
    }

    // --- WORK ORDER ACTIONS ---
    async startWorkOrder(woId) { await this.orm.call("mrp.workorder", "button_start", [woId]); }
    async pauseWorkOrder(woId) { await this.orm.call("mrp.workorder", "button_pending", [woId]); }
    async finishWorkOrder(woId) { await this.orm.call("mrp.workorder", "button_finish", [woId]); }

    formatDuration(minutes) {
        if (!minutes || minutes < 0) return "00:00:00";
        const totalSeconds = Math.floor(minutes * 60);
        const h = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
        const m = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
        const s = (totalSeconds % 60).toString().padStart(2, '0');
        return `${h}:${m}:${s}`;
    }
}

ShopfloorScreen.template = "cyllo_shopfloor.ShopfloorTemplate";

registry.category("actions").add("shopfloor_screen", ShopfloorScreen);