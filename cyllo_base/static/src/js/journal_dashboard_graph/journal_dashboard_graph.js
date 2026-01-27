/** @odoo-module **/
import {JournalDashboardGraphField} from '@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field';
import {patch} from "@web/core/utils/patch";
import { hexToRGBA } from "@web/core/colors/colors";

patch(JournalDashboardGraphField.prototype, {
    setup() {
        super.setup(...arguments);
    },

    getLineChartConfig() {
        const labels = this.data[0].values.map(function (pt) {
            return pt.x;
        });
        const color10 = '#9EA700'
        const borderColor = this.data[0].is_sample_data ? hexToRGBA(color10, 0.1) : color10;
        const backgroundColor = this.data[0].is_sample_data
            ? hexToRGBA(color10, 0.05)
            : hexToRGBA(color10, 0.2);
        return {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        borderColor,
                        data: this.data[0].values,
                        fill: "start",
                        label: this.data[0].key,
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        intersect: false,
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: {
                        display: false,
                    },
                    x: {
                        display: false,
                    },
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
            },
        };
    },

    getBarChartConfig() {
        const data = [];
        const labels = [];
        const backgroundColor = [];
        const color13 = '#C1E1C1'
        const color19 = '#ADD8E6';
        this.data[0].values.forEach((pt) => {
            data.push(pt.value);
            labels.push(pt.label);
            if (pt.type === "past") {
                backgroundColor.push(color13);
            } else if (pt.type === "future") {
                backgroundColor.push(color19);
            } else {
                backgroundColor.push("#ebebeb");
            }
        });
        return {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        data,
                        fill: "start",
                        label: this.data[0].key,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        intersect: false,
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: {
                        display: false,
                    },
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
            },
        };
    }
});