/** @odoo-module */

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PayrollDashboard extends Component {

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        // ---------------- STATE ----------------
        this.state = useState({
            employees: 0,
            contracts: 0,
            generated: 0,
            paid: 0,
            warnings: [],
            batches: [],
            payroll_dist_labels: [],
            payroll_dist_data: [],
            employee_cost_year_labels: [],
            employee_cost_year_data: [],
            employee_cost_month_labels: [],
            employee_cost_month_data: [],
            employee_cost_period: "year",   // default
            payroll_dist_type_ids: [],
        });

        this.employeeCostChart = null;
        this.payrollPieChart = null;

        // ---------------- LOAD DATA ----------------
        onWillStart(async () => {
            const data = await this.orm.call(
                "employee.payslip",
                "get_payroll_dashboard_data",
                []
            );
            Object.assign(this.state, data);
        });

        // ---------------- MOUNT ----------------
        onMounted(() => {
            this.renderEmployeeCostChart();
            this.renderPayrollPieChart();
        });

        // ---------------- DROPDOWN HANDLER ----------------
        this.onEmployeeCostFilterChange = (ev) => {
            const selected = ev.target.value; // 'month' or 'year'
            this.state.employee_cost_period = selected;
            this.renderEmployeeCostChart();
        };
    }

    // ================= EMPLOYEE COST BAR =================
    renderEmployeeCostChart() {
        const labels =
            this.state.employee_cost_period === "year"
                ? this.state.employee_cost_year_labels
                : this.state.employee_cost_month_labels;

        const data =
            this.state.employee_cost_period === "year"
                ? this.state.employee_cost_year_data
                : this.state.employee_cost_month_data;
        if (this.employeeCostChart) {
            this.employeeCostChart.destroy();
        }
        const ctx = document.getElementById("employeeCostChart");
        this.employeeCostChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Net Salary",
                    data: data,
                    backgroundColor: "rgba(155, 89, 182, 0.6)",
                    borderRadius: 8,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return "Net Salary: " +
                                    context.raw.toLocaleString();
                            }
                        }
                    }
                },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    openBatchList() {
    this.action.doAction({
        type: "ir.actions.act_window",
        name: "Payslip Batches",
        res_model: "employee.payslip.batch",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        target: "current",
    });
}
    openEmployees() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Employees",
            res_model: "hr.employee",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
    openContracts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Contracts",
            res_model: "hr.contract",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
    openPayslips() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Payslips",
            res_model: "employee.payslip",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
    openPaidPayslips() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paid Payslips",
            res_model: "employee.payslip",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [["state", "=", "paid"]],
        });
    }
    openBatch(ev) {
            const batchId = parseInt(ev.currentTarget.dataset.id);
            if (!batchId) {
                console.warn("Invalid batch ID:", batchId);
                return;
            }
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Payslip Batch",
                res_model: "employee.payslip.batch",
                res_id: batchId,
                views: [[false, "form"]],
                view_mode: "form",
                target: "current",
            });
        }

    onWarningClick(ev) {
        const label = ev.currentTarget.dataset.id;
        if (!label) {
            return;
        }
        if (label === "Draft Payslips") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Draft Payslips",
                res_model: "employee.payslip",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["state", "=", "draft"]],
                target: "current",
            });
        }
        if (label === "Employees Without Running Contracts") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees Without Running Contracts",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["contract_id", "=", false]],
                target: "current",
            });
        }
        if (label === "Employees With Both New And Running Contracts") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees With Both New And Running Contracts",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [
                    ["contract_ids.state", "=", "open"],
                    ["contract_ids.state", "=", "draft"],
                ],
                target: "current",
            });
        }
        if (label === "Employees Without Bank Accounts") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees Without Bank Accounts",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["bank_account_id", "=", false]],
                target: "current",
            });
        }
        if (label === "Nearly Expired Contracts (Next 30 Days)") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Nearly Expired Contracts",
                res_model: "hr.contract",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [
                    ["state", "=", "open"],
                    ["date_end", "!=", false],
                    ["date_end", ">=", moment().format("YYYY-MM-DD")],
                    ["date_end", "<=", moment().add(30, "days").format("YYYY-MM-DD")],
                ],
                target: "current",
            });
        }
        if (label === "Employees Without Identification Number") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees Without Identification Number",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["identification_id", "=", false]],
                target: "current",
            });
        }

}



    // ================= PAYROLL PIE =================
    renderPayrollPieChart() {

        if (this.payrollPieChart) {
            this.payrollPieChart.destroy();
        }

        const chartEl = document.getElementById("payrollPieChart");

        this.payrollPieChart = new Chart(chartEl, {
            type: "pie",
            data: {
                labels: this.state.payroll_dist_labels,
                datasets: [{
                    data: this.state.payroll_dist_data,
                    backgroundColor: [
                        "#3498db",
                        "#2ecc71",
                        "#e74c3c",
                        "#f1c40f",
                        "#9b59b6"
                    ]
                }]
            },

        options: {
            responsive: true,

            // ✅ CLICK ACTION (same pattern as your reference)
            onClick: (evt, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const typeId =
                        this.state.payroll_dist_type_ids[index];
                    this.openStructureType(typeId);
                }
            },
            plugins: {
                legend: {
                    position: "bottom",
                },
                tooltip: {
                    enabled: true,
                }
            }
        }
    });
}

    openStructureType(typeId) {
        if (!typeId) return;

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Salary Structures",
            res_model: "hr.payroll.structure",
            domain: [['struct_type_id', '=', typeId]],
            views: [[false, "tree"], [false, "form"]],
            view_mode: "tree,form",
            target: "current",
        });
    }
    }

// ================= TEMPLATE =================

PayrollDashboard.template = "cyllo_payroll_management.PayrollDashboard"
registry.category("actions").add(
    "hr_payroll_dashboard",
    PayrollDashboard
);
