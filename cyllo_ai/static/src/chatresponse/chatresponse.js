/** @odoo-module **/
import { Component, onWillStart, onMounted, useState, useRef, onPatched, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class ChatResponse extends Component {
    static props = {
        id: { type: Number, optional: true },
        text: { type: String, optional: true },
        html: { type: String, optional: true },
        chart_config: {
            validate: (value) => value === null || typeof value === 'object',
            optional: true
        },
        interrupted: { type: Boolean, optional: true },
        onInterruptResponse: { type: Function, optional: true },
        onLoad: { type: Function, optional: true },
    };

    setup() {
        super.setup(...arguments);

        this.chartContainer = useRef("chartContainer");
        this.popupChartContainer = useRef("popupChartContainer");
        this.state = useState({
            hideButtons: false,
            showChartOptions: false,
            chatSelectedType: "bar",
            popupSelectedType: "bar",
            validGraph: false,
            defaultChart: "",
            chartTypes: [
                { name: "default", label: "Default", icon: "/cyllo_ai/static/src/img/default-graph.svg" },
                { name: "bar", label: "Bar", icon: "/cyllo_ai/static/src/img/bar.svg" },
                { name: "line", label: "Line", icon: "/cyllo_ai/static/src/img/line.svg" },
                { name: "pie", label: "Pie", icon: "/cyllo_ai/static/src/img/pie.svg" },
                { name: "donut", label: "Donut", icon: "/cyllo_ai/static/src/img/donut.svg" },
                { name: "scatter", label: "Scatter", icon: "/cyllo_ai/static/src/img/scatter.svg" },
                // Add more types and their icons here
            ],
            chart_config: this.props.chart_config ? JSON.parse(JSON.stringify(this.props.chart_config)) : null,
            showGraphPopup: false,
            hasTable: false,
        })
        this.rpc = useService("rpc");

        this.resizeObserver = null;

        onMounted(() => {
            setTimeout(() => {
                this.initChart();
                this.resizeChart();
            }, 300);

            // Initialize ResizeObserver
            this.resizeObserver = new ResizeObserver(() => {
                this.resizeChart();
            });

            if (this.chartContainer.el) {
                this.resizeObserver.observe(this.chartContainer.el);
            }
            if (this.popupChartContainer.el) {
                this.resizeObserver.observe(this.popupChartContainer.el);
            }

            // Convert String object to primitive string and check for table tags
            const htmlContent = String(this.props.html || '');
            const hasTableTag = htmlContent.includes('<table');

            this.state.hasTable = hasTableTag;
        });

        onWillDestroy(() => {
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
            }
        });
    }

    async onWillStart() {
        this.baseChartConfig = this.props.chart_config ? JSON.parse(JSON.stringify(this.props.chart_config)) : null;
        this.state.chart_config = this.baseChartConfig;
    };

    initChart() {
        try {
            const { chart_config } = this.props;
            const popupRef = this.popupChartContainer?.el;
            const baseRef = this.chartContainer?.el;
            const container = popupRef || baseRef;
            if (!container || typeof echarts === "undefined" || !chart_config) return;

            // Dispose existing chart instance
            if (container.__echarts_instance__) echarts.dispose(container);

            // Deep clone config (avoid mutating props)
            let config = JSON.parse(JSON.stringify(chart_config));
            // ---- Title tweaks ----
            if (config.title) {
                const titles = Array.isArray(config.title) ? config.title : [config.title];
                titles.forEach(title => {
                    title.top ??= 10;
                    title.textStyle ??= {};
                    title.textStyle.fontSize ??= 16;
                    title.textStyle.fontWeight ??= "bold";
                });
                config.title = titles.length === 1 ? titles[0] : titles;
            }

            // ---- Legend tweaks ----
            if (config.legend) {
                const legends = Array.isArray(config.legend) ? config.legend : [config.legend];
                legends.forEach(legend => {
                    legend.top ??= 40;
                    legend.left ??= "center";
                });
                config.legend = legends.length === 1 ? legends[0] : legends;
            }

            // ---- X Axis tweaks ----
            if (config.xAxis) {
                const xAxis = Array.isArray(config.xAxis) ? config.xAxis : [config.xAxis];
                xAxis.forEach(axis => {
                    axis.axisLabel ??= {};
                    axis.axisLabel.hideOverlap ??= true;
                    axis.axisLabel.rotate ??= 45;
                    axis.axisLabel.margin ??= 10;
                    const formatterValue = axis.axisLabel.formatter
                    if (formatterValue) {
                        axis.axisLabel.formatter = function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                    else {
                        axis.axisLabel.formatter ??= function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                });
                config.xAxis = xAxis.length === 1 ? xAxis[0] : xAxis;
            }

            if (config.yAxis) {
                const yAxisArr = Array.isArray(config.yAxis) ? config.yAxis : [config.yAxis];
                yAxisArr.forEach(axis => {
                    axis.axisLabel ??= {};
                    axis.axisLabel.interval = 0;    // Show all y-axis labels
                    axis.axisLabel.hideOverlap = false;
                    const formatterValue = axis.axisLabel.formatter
                    if (formatterValue) {
                        axis.axisLabel.formatter = function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                    else {
                        axis.axisLabel.formatter ??= function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                });
                config.yAxis = yAxisArr.length === 1 ? yAxisArr[0] : yAxisArr;
            }
            // ---- Convert to pie chart if required ----
            if (config.series?.[0]?.type === "pie") {
                config = this.convertToPie(config);
            }

            // ---- Add data zoom ----
            config.dataZoom = [
                { type: "inside", yAxisIndex: 0, start: 0, end: 100 },
                { type: "inside", xAxisIndex: 0, start: 0, end: 100 }
            ];

            // ---- Initialize chart ----
            const chart = echarts.init(container);
            chart.setOption(config, {
                notMerge: true,
                replaceMerge: ["xAxis", "yAxis", "series", "grid", "legend"]
            });

            // ---- Set default graph + resize ----
            this.setDefaultGraph(config);
            requestAnimationFrame(() => chart.resize());

        } catch (err) {
            console.error("ECharts init error:", err);
        }
    }


    setDefaultGraph(chartConfig) {
        this.state.defaultChart = chartConfig;
    }

    resizeChart() {
        let container = this.chartContainer.el;
        if (this.popupChartContainer.el) {
            container = this.popupChartContainer.el;
        }
        if (!container || typeof echarts === "undefined") return;
        const chartInstance = echarts.getInstanceByDom(container);
        if (!chartInstance) return;
        try {
            chartInstance.resize();
        }
        catch (e) {
            console.warn("chart was not resized", e);
        }
    }

    onExpandGraph() {
        this.state.showGraphPopup = !this.state.showGraphPopup;
        this.state.popupSelectedType = "bar";
        setTimeout(() => {
            const container = this.state.showGraphPopup
                ? this.__owl__.refs.popupChartContainer
                : this.__owl__.refs.chartContainer;
            if (container) {
                this.initChart();
            }
        }, 100);
    }

    async handleCancel() {
        this.state.hideButtons = true;
        this.props.onInterruptResponse?.('cancel');

        await this.rpc("/chatbot/set_interrupt", { id: this.props.id });


    }

    handleProceed() {
        this.state.hideButtons = true;
        this.props.onInterruptResponse?.('proceed');
    }

    onGraphIconClick() {
        this.state.showChartOptions = !this.state.showChartOptions;
    }

    onChartTypeSelect = (type, isPopup = false) => {
        if (!isPopup) {
            this.state.chatSelectedType = type;
        }
        else {
            this.state.popupSelectedType = type;
        }
        this.state.showChartOptions = false;

        if (!this.props.chart_config) return;

        // Safely transform chart config based on type
        const updatedConfig = this.props.chart_config ? this.convertChartType(this.state.chart_config, type) : null;

        const container = this.state.showGraphPopup ? this.popupChartContainer.el : this.chartContainer.el;
        if (container && typeof echarts !== "undefined") {
            echarts.dispose(container);
            const chart = echarts.init(container);
            chart.clear();
            chart.setOption(updatedConfig, {
                notMerge: true,
                replaceMerge: ['xAxis', 'yAxis', 'series', 'grid', 'legend']
            });
            setTimeout(() => chart.resize(), 300);
        }
    };

    // Utility function to deep clone config
    cloneConfig(config) {
        return JSON.parse(JSON.stringify(config));
    }

    extractChartData(config) {

        let labels = [];
        let values = [];

        // Try to find any series
        const series = Array.isArray(config.series) ? config.series[0] : config.series;

        if (!series) return { labels, values };

        // 1. Pie-like series → has name/value pairs
        if (Array.isArray(series.data) && series.data.length && series.data[0].name !== undefined) {
            labels = series.data.map(item => item.name);
            values = series.data.map(item => item.value);

            // 2. Axis-based chart → xAxis or yAxis data
        } else if (config.xAxis?.data && config.xAxis.data.length !== 0) {
            labels = config.xAxis.data;
            values = series.data || [];

        } else if (config.yAxis?.data?.length) {
            labels = config.yAxis.data;
            values = series.data || [];

            // 3. Scatter/bubble/other → look for object values
        } else if (Array.isArray(series.data)) {
            if (typeof series.data[0] === "object") {
                labels = series.data.map((_, idx) => `Point ${idx + 1}`);
                values = series.data.map(item => item.value || item[1] || 0);
            } else {
                // fallback simple array
                const configData = this.hasData(config)
                labels = configData;
                values = series.data;
            }
        }

        return { labels, values };
    }

    hasData(obj) {
        if (!obj || typeof obj !== 'object') return false;

        // If this object has a `data` array with length > 0
        if (Array.isArray(obj.data) && obj.data.length > 0) {
            return obj.data;
        }
        // Recursively check all properties
        for (let key in obj) {
            const found = this.hasData(obj[key]);
            if (found) return found;
        }
        return false;
    }

    convertToDefault(config) {
        const newConfig = this.state.defaultChart
        return newConfig
    }

    // Convert any chart to pie chart
    convertToPie(config) {
        const newConfig = this.cloneConfig(config);
        const { labels, values, seriesName } = this.extractChartData(config);
        // Create pie chart data format
        const pieData = labels.map((name, index) => ({
            name: name,
            value: values[index] || 0
        }));
        // Remove incompatible properties
        delete newConfig.xAxis;
        delete newConfig.yAxis;
        delete newConfig.grid;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;


        // Configure pie chart specific properties
        newConfig.tooltip = {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)'
        };

        newConfig.legend = {
            orient: 'vertical',
            left: 'left',
            data: labels,
            top: 30,
        };

        newConfig.series = [{
            name: seriesName,
            type: 'pie',
            radius: '80%',
            center: ['50%', '60%'],
            label: {
                show: true ? this.state.showGraphPopup : false
            },
            labelLine: {
                show: true ? this.state.showGraphPopup : false
            },
            data: pieData,
            avoidLabelOverlap: true,
            left: 100,
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowOffsetX: 0,
                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
            }
        }];

        return newConfig;
    }

    // Convert any chart to horizontal bar chart
    convertToBar(config) {
        if (!config) return null;

        let newConfig = this.cloneConfig(config);
        // ✅ Skip if already a bar chart
        const isBar = Array.isArray(config.series) && config.series.some(s => s.type === "bar");
        if (isBar) {
            newConfig = this.state.defaultChart;
            return newConfig
        }
        // Extract relevant chart data
        const { labels = [], values = [], seriesName = "Series" } = this.extractChartData(config);
        //
        //  Clean up pie/polar-specific properties in one pass
        ["polar", "angleAxis", "radiusAxis", "legend", "tooltip", "toolbox"].forEach(key => delete newConfig[key]);

        // Define new bar chart layout

        if (newConfig.title) {
            const titles = Array.isArray(newConfig.title) ? newConfig.title : [newConfig.title];
            titles.forEach(title => {
                title.top ??= 10;
                title.textStyle ??= {};
                title.textStyle.fontSize ??= 16;
                title.textStyle.fontWeight ??= "bold";
            });
            newConfig.title = titles.length === 1 ? titles[0] : titles;
        }

        // ---- Legend tweaks ----
        if (newConfig.legend) {
            const legends = Array.isArray(newConfig.legend) ? newConfig.legend : [newConfig.legend];
            legends.forEach(legend => {
                legend.top ??= 40;
                legend.left ??= "center";
            });
            newConfig.legend = legends.length === 1 ? legends[0] : legends;
        }

        // ---- X Axis tweaks ----
        if (newConfig.xAxis) {
            const xAxis = Array.isArray(newConfig.xAxis) ? newConfig.xAxis : [newConfig.xAxis];
            xAxis.forEach(axis => {
                axis.axisLabel ??= {};
                axis.axisLabel.hideOverlap ??= true;
                axis.axisLabel.rotate ??= 45;
                axis.axisLabel.margin ??= 10;
                axis.axisLabel.formatter ??= function (value) {
                    if (value >= 1000000) return (value / 1000000) + 'M';
                    if (value >= 1000) return (value / 1000) + 'k';
                    return value
                }
            });
            newConfig.xAxis = xAxis.length === 1 ? xAxis[0] : xAxis;
        }

        if (newConfig.yAxis) {
            const yAxisArr = Array.isArray(newConfig.yAxis) ? newConfig.yAxis : [newConfig.yAxis];
            yAxisArr.forEach(axis => {
                axis.axisLabel ??= {};
                axis.axisLabel.interval = 0;    // Show all y-axis labels
                axis.axisLabel.hideOverlap = false;
                axis.axisLabel.formatter ??= function (value) {
                    if (value >= 1000000) return (value / 1000000) + 'M';
                    if (value >= 1000) return (value / 1000) + 'k';
                    return value
                }
            });
            newConfig.yAxis = yAxisArr.length === 1 ? yAxisArr[0] : yAxisArr;
        }


        // ---- Convert to pie chart if required ----
        if (newConfig.series?.[0]?.type === "pie") {
            newConfig = this.convertToPie(newConfig);
        }

        // ---- Add data zoom ----
        newConfig.dataZoom = [
            { type: "inside", yAxisIndex: 0, start: 0, end: 100 },
            { type: "inside", xAxisIndex: 0, start: 0, end: 100 }
        ];

        return newConfig;
    }

    // Convert any chart to line chart
    convertToLine(config) {
        const newConfig = this.cloneConfig(config);
        const { labels, values, seriesName } = this.extractChartData(config);

        // Remove pie and bar specific properties
        delete newConfig.legend;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;

        newConfig.tooltip = {
            trigger: 'axis'
        };

        newConfig.grid = {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        };

        newConfig.xAxis = {
            type: 'category',
            data: labels,
            boundaryGap: false,
            axisLabel: {
                hideOverlap: true,
                rotate: 45,
                margin: 10
            }
        };

        newConfig.yAxis = {
            type: 'value',
            axisLabel: {
                hideOverlap: true,
                formatter: value => value >= 1000 ? value / 1000 + 'k' : value
            }
        };

        newConfig.series = [{
            name: seriesName,
            type: 'line',
            data: values,
            smooth: true
        }];

        newConfig.dataZoom = [
            {
                type: 'inside',
                yAxisIndex: 0,
                start: 0,
                end: 100
            },
            {
                type: 'inside',
                xAxisIndex: 0,
                start: 0,
                end: 100
            }
        ];
        return newConfig;
    }

    // Convert any chart to scatter plot
    convertToScatter(config) {
        const newConfig = this.cloneConfig(config);
        const { labels, values, seriesName } = this.extractChartData(config);

        // Create scatter plot data format [x, y] pairs
        // For single series data, use index as x-axis and value as y-axis
        const scatterData = values.map((value, index) => [index, value]);

        // Remove pie chart specific properties
        delete newConfig.legend;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;

        // Configure scatter plot properties
        newConfig.tooltip = {
            trigger: 'item',
            formatter: function (params) {
                const label = labels[params.data[0]] || `Point ${params.data[0]}`;
                return `${seriesName}<br/>${label}: ${params.data[1]}`;
            }
        };

        newConfig.grid = {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        };

        newConfig.xAxis = {
            type: 'value',
            scale: true,
            name: 'Category Index'
        };

        newConfig.yAxis = {
            type: 'value',
            scale: true,
            name: seriesName
        };

        newConfig.series = [{
            name: seriesName,
            type: 'scatter',
            data: scatterData,
            symbolSize: 8,
            emphasis: {
                focus: 'series'
            },
            itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(120, 36, 50, 0.5)',
                shadowOffsetY: 5,
                color: {
                    type: 'radial',
                    x: 0.4,
                    y: 0.3,
                    r: 1,
                    colorStops: [{
                        offset: 0,
                        color: 'rgb(251, 118, 123)'
                    }, {
                        offset: 1,
                        color: 'rgb(204, 46, 72)'
                    }]
                }
            }
        }];
        newConfig.dataZoom = [
            {
                type: 'inside',
                yAxisIndex: 0,
                start: 0,
                end: 100
            },
            {
                type: 'inside',
                xAxisIndex: 0,
                start: 0,
                end: 100
            }
        ];
        return newConfig;
    }

    // Convert any chart to donut chart
    convertToDonut(config) {
        const newConfig = this.convertToPie(config);
        delete newConfig.xAxis;
        delete newConfig.yAxis;
        delete newConfig.grid;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;
        // Modify pie config for donut
        newConfig.series[0].radius = ['40%', '80%'];
        return newConfig;
    }
    // Main converter function using strategy pattern
    chartConverters() {
        return {
            default: this.convertToDefault.bind(this),
            pie: this.convertToPie.bind(this),
            bar: this.convertToBar.bind(this),
            line: this.convertToLine.bind(this),
            donut: this.convertToDonut.bind(this),
            scatter: this.convertToScatter.bind(this)
        }
    }

    convertChartType(config, targetType) {
        const converter = this.chartConverters()[targetType];
        if (!converter) {
            return config;
        }
        return converter(config);
    }

    downloadTable() {
        // Get the HTML content
        const htmlContent = String(this.props.html || '');

        // Create a temporary div to parse the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;

        // Find the table element
        const table = tempDiv.querySelector('table');

        if (!table) {
            console.error('No table found in the message');
            return;
        }

        // Convert HTML table to workbook using SheetJS
        const workbook = XLSX.utils.table_to_book(table, {sheet: "Sheet1"});

        // Generate filename with timestamp
        const timestamp = new Date().toISOString().slice(0, 10);
        const filename = `chatbot_table_${timestamp}.xlsx`;

        // Trigger download
        XLSX.writeFile(workbook, filename);

    }
}
ChatResponse.template = "ChatResponse";
