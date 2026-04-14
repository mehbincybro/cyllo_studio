/** @odoo-module */

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {Component, useState, onWillStart} from "@odoo/owl";
import {RepairCard} from "../repair_card/repair_card";

export class RepairFloorDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");

        this.state = useState({
            currentFilter: 'confirmed',
            employees: [],
            selectedEmployee: null,
            repairs: {draft: [], confirmed: [], under_repair: [], done: [], cancel: []},
            isManager: false
        });

        onWillStart(async () => {
            this.state.isManager = await this.user.hasGroup("stock.group_stock_manager");
            await this.loadEmployees();
            await this.fetchRepairOrders();
        });
    }

    async loadEmployees() {
        this.state.employees = await this.orm.searchRead("hr.employee", [], ["id", "name"]);
        const currentUserEmp = await this.orm.searchRead(
            "hr.employee",
            [["user_id", "=", this.user.userId]],
            ["id", "name"],
            {limit: 1}
        );
        if (currentUserEmp.length > 0) {
            this.state.selectedEmployee = currentUserEmp[0];
        } else if (this.state.employees.length > 0) {
            this.state.selectedEmployee = this.state.employees[0];
        }
    }

    selectEmployee(employee) {
        this.state.selectedEmployee = employee;
    }

    // Simple tab navigation
    setView(viewName) {
        this.state.currentFilter = viewName;
    }

    async fetchRepairOrders() {
        const records = await this.orm.searchRead(
            "repair.order",
            [["state", "in", ["draft", "confirmed", "under_repair", "done", "cancel"]]],
            [
                "name", "state", "product_id", "partner_id", "user_id",
                "under_warranty", "operator_ids",
                "current_start_time", "is_timer_running", "total_accumulated_time", "sale_order_id",
            ]
        );

        this.state.repairs = {draft: [], confirmed: [], under_repair: [], done: [], cancel: []};
        records.forEach(record => {
            if (this.state.repairs[record.state]) {
                this.state.repairs[record.state].push(record);
            }
        });
    }
}

RepairFloorDashboard.template = "repair_floor.Dashboard";
RepairFloorDashboard.components = {RepairCard};

registry.category("actions").add("repair_floor.dashboard", RepairFloorDashboard);