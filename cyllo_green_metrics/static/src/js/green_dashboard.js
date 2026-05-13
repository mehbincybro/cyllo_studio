/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useRef, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class GreenMetricsDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.gasChartRef = useRef("gasChart");
        this.soundChartRef = useRef("soundChart");
        this.waterChartRef = useRef("waterChart");
        
        this.state = useState({ 
            dashboardData: {},
            waterDateFilter: 'yearly',
            waterScopeFilter: ['all'],
            waterStartDate: '',
            waterEndDate: '',
        });
        this.gasChart = null;
        this.soundChart = null;
        this.waterChart = null;

        onWillStart(async () => {
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
            } catch (e) {
                try {
                    await loadJS("https://cdn.jsdelivr.net/npm/chart.js");
                } catch (e2) {
                    console.log("Failed to load Chart.js");
                }
            }
            await this.loadData();
            // Default to 'no_scope' only on load as requested
            this.state.waterScopeFilter = ['no_scope'];
            await this.loadData(); // Reload with the new default filter
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async loadData() {
        // Prepare scope filter for backend (comma separated string)
        const scopeFilterStr = Array.isArray(this.state.waterScopeFilter) ? this.state.waterScopeFilter.join(',') : this.state.waterScopeFilter;
        
        this.state.dashboardData = await this.orm.call(
            "carbon.activity", 
            "get_dashboard_data", 
            [],
            {
                water_date_filter: this.state.waterDateFilter,
                water_scope_filter: scopeFilterStr,
                water_start_date: this.state.waterStartDate,
                water_end_date: this.state.waterEndDate
            }
        );
        if (this.state.dashboardData) {
            this.renderCharts();
        }
    }

    async onWaterDateFilterChange(ev) {
        this.state.waterDateFilter = ev.target.value;
        await this.loadData();
    }

    async onWaterDateRangeChange() {
        if (this.state.waterStartDate && this.state.waterEndDate) {
            await this.loadData();
        }
    }

    createInitiative(projectType = 'green') {
        let projectData = this.state.dashboardData?.projects;
        if (projectType === 'water') projectData = this.state.dashboardData?.water_projects;
        if (projectType === 'sound') projectData = this.state.dashboardData?.sound_projects;

        const projectId = projectData?.project_id;
        if (!projectId) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'project.task',
            views: [[false, 'form']],
            context: { default_project_id: projectId },
        }, {
            onClose: async () => {
                await this.loadData();
            }
        });
    }

    openTasks(projectType = 'green', stageId) {
        let projectData = this.state.dashboardData?.projects;
        if (projectType === 'water') projectData = this.state.dashboardData?.water_projects;
        if (projectType === 'sound') projectData = this.state.dashboardData?.sound_projects;

        const projectId = projectData?.project_id;
        const projectName = projectType.charAt(0).toUpperCase() + projectType.slice(1) + " Initiatives";
        
        if (!projectId) return;
        let domain = [['project_id', '=', projectId]];
        if (stageId) {
            domain.push(['stage_id', '=', stageId]);
        }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: projectName,
            res_model: 'project.task',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: { default_project_id: projectId },
        }, {
            onClose: async () => {
                await this.loadData();
            }
        });
    }

    renderCharts() {
        if (!this.state.dashboardData) return;

        if (this.gasChart) this.gasChart.destroy();
        if (this.soundChart) this.soundChart.destroy();
        if (this.waterChart) this.waterChart.destroy();

        const gasData = this.state.dashboardData.gas;
        if (gasData && gasData.labels.length > 0 && this.gasChartRef.el) {
            this.gasChart = new Chart(this.gasChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: gasData.labels,
                    datasets: [{
                        data: gasData.values,
                        backgroundColor: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });
        }
        
        const soundData = this.state.dashboardData.sound;
        if (soundData && soundData.labels.length > 0 && this.soundChartRef.el) {
            this.soundChart = new Chart(this.soundChartRef.el, {
                type: 'bar',
                data: {
                    labels: soundData.labels,
                    datasets: [{
                        label: 'Sound Emissions',
                        data: soundData.values,
                        backgroundColor: '#ff7f0e',
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });
        }

        const waterData = this.state.dashboardData.water;
        if (waterData && waterData.labels.length > 0 && this.waterChartRef.el) {
            this.waterChart = new Chart(this.waterChartRef.el, {
                type: 'bar',
                data: {
                    labels: waterData.labels,
                    datasets: [{
                        label: 'Water Pollution',
                        data: waterData.values,
                        backgroundColor: '#1f77b4',
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });
        }
    }

    // --- MULTI-SELECT SCOPE HANDLERS ---
    async toggleScopeAll(ev) {
        const checked = ev.target.checked;
        if (checked) {
            const allScopeIds = (this.state.dashboardData.scopes || []).map(s => s.id.toString());
            // Select all individual scopes, but NOT 'no_scope' as requested
            this.state.waterScopeFilter = ['all', ...allScopeIds];
        } else {
            this.state.waterScopeFilter = [];
        }
        await this.loadData();
    }

    async toggleScope(scopeId, ev) {
        const idStr = scopeId.toString();
        let currentFilters = [...this.state.waterScopeFilter];
        
        if (ev.target.checked) {
            if (idStr === 'no_scope') {
                // When 'no_scope' is selected, only 'no_scope' should be selected
                currentFilters = ['no_scope'];
            } else {
                // When an individual scope is selected, remove 'no_scope'
                currentFilters = currentFilters.filter(f => f !== 'no_scope');
                if (!currentFilters.includes(idStr)) {
                    currentFilters.push(idStr);
                }
            }
        } else {
            currentFilters = currentFilters.filter(f => f !== idStr && f !== 'all');
        }
        
        // If all individual scopes are selected (excluding no_scope), add back 'all'
        const allScopeIds = (this.state.dashboardData.scopes || []).map(s => s.id.toString());
        const expectedCount = allScopeIds.length;
        const actualCount = currentFilters.filter(f => f !== 'all' && f !== 'no_scope').length;
        
        if (actualCount === expectedCount && expectedCount > 0) {
            if (!currentFilters.includes('all')) currentFilters.push('all');
        } else {
            currentFilters = currentFilters.filter(f => f !== 'all');
        }
        
        this.state.waterScopeFilter = currentFilters;
        await this.loadData();
    }

    isScopeSelected(id) {
        const idStr = id.toString();
        // Special case: if 'all' is present, it refers to individual scopes, not 'no_scope'
        if (idStr === 'no_scope') {
            return this.state.waterScopeFilter.includes('no_scope');
        }
        return this.state.waterScopeFilter.includes(idStr) || this.state.waterScopeFilter.includes('all');
    }

    isAllSelected() {
        return this.state.waterScopeFilter.includes('all');
    }

    getSelectedScopesText() {
        if (this.isAllSelected()) return "All Scopes";
        if (!this.state.waterScopeFilter || this.state.waterScopeFilter.length === 0) return "No Scopes Selected";
        if (this.state.waterScopeFilter.length === 1 && this.state.waterScopeFilter[0] === 'no_scope') return "No Scope Only";
        
        const count = this.state.waterScopeFilter.filter(f => f !== 'all').length;
        return `${count} Scopes Selected`;
    }
}

GreenMetricsDashboard.template = "cyllo_green_metrics.GreenDashboard";
registry.category("actions").add("green_metrics_dashboard", GreenMetricsDashboard);
