/** @odoo-module **/
import {worldMapChart} from "./charts/world_map";
import {loadingChart} from "./charts/loadingChart"

/**
 * Converts a string to title case.
 * @param {string} inputString - The input string to be converted to title case.
 * @param {string} [splitBy="_"] - The character to split the input string.
 * @returns {string} - The input string converted to title case.
 */
export const convertToTitleCase = (inputString, splitBy = "_") => {
    var titleCaseString = inputString
    if (inputString) {
        const words = inputString.split(splitBy);
        titleCaseString = words
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    return titleCaseString;
}

export class ChartMaker {
    /**
     * Constructor for the ChartMaker class.
     * @param {Array} data - The data for the chart.
     * @param {string} dimension - The dimension of the chart.
     * @param {Array} measures - The measures for the chart.
     * @param {string} name - The name of the chart.
     * @param {string} type - The type of chart (e.g., 'bar', 'line', 'pie', 'doughnut').
     * @param {string} dimension_axis - The dimension axis ('x' or 'y').
     * @param {object} params - Additional parameters for the chart (optional).
     */
    constructor(data, dimension, measures, name, type, dimension_axis, params = {}) {
        this.data = data
        this.dimension = dimension
        this.measures = measures
        this.name = name
        this.type = type
        this.dimension_axis = dimension_axis
        this.params = params
        this.chartOptions = {}
    }

    getDefaultZoom() {
        const length = this.data.length
        const getStartValue = () => {
            if (length > 5000) return 99;
            if (length > 4500 && length <= 5000) return 95;
            if (length > 3500 && length <= 4500) return 88;
            if (length > 2500 && length <= 3500) return 83;
            if (length > 1500 && length <= 2500) return 77;
            if (length > 1000 && length <= 1500) return 70;
            if (length > 500 && length <= 1000) return 65;
            if (length > 100 && length <= 500) return 45;
            if (length > 15) return 30;
            if (length <= 15) return 0;
        }
        var dataZoom = [{
            type: 'inside',
            start: getStartValue(),
            end: 100,
            zoomOnMouseWheel: false,
            moveOnMouseMove: true,
            moveOnMouseWheel: true
        }]
        if (this.dimension_axis === "x") {
            dataZoom[0].id = "insideY"
            dataZoom[0].YAxisIndex = 0
        } else {
            dataZoom[0].id = "insideX"
            dataZoom[0].XAxisIndex = 0
        }
        return dataZoom
    }

    /**
     * Generate graph options for the chart.
     * @returns {object} - The graph options for the chart.
     */
    makeGraphOptions() {
        if (!this.data?.length) {
            return loadingChart({
                text: 'No Data Found',
                loop: false,
                title: this.name
            })
        }
        var legends = {
            data: [this.name]
        }
        var formatter = '{a} <br/>{b} : {c}'
        this.chartOptions.formatter = formatter
        if (this.measures.length > 2) {
            legends = {
                data: []
            }
            this.measures.forEach((key) => {
                legends.data.push(convertToTitleCase(key))
            })
        }
        var series = []
        this.measures.forEach((key) => {
            series.push({
                name: convertToTitleCase(key),
                type: this.type,
                data: [],
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 10
                    }
                },
            })
        })
        var xAxis = {
            data: [],
            type: 'category'
        }
        this.data && this.data.forEach((item, mi) => {
            xAxis.data.push(item[this.dimension])
            this.measures.forEach((key, i) => {
                series[i].data.push(item[key])
            })
        })
        var yAxis = {
            type: "value"
        }
        var dataZoom = this.getDefaultZoom()
        let val = {
            title: {
                text: convertToTitleCase(this.name, " "),
                padding: [3, 0, 0, 15],
                textStyle: {
                    fontSize: 17,
                    fontWeight: 'normal',
                }
            },
            legends,
            legend: {
                type: 'scroll',
                orient: 'vertical',
                right: 10,
                top: 20,
                bottom: 20,
            },
            xAxis: this.dimension_axis === "x" ? xAxis : yAxis,
            yAxis: this.dimension_axis === "x" ? yAxis : xAxis,
            series,
            tooltip: {
                trigger: 'item',
                formatter: formatter
            },
            grid: {
                left: '12%', // Adjust as needed
                right: '15%', // Adjust as needed
                top: '15%', // Adjust as needed
                bottom: '20%' // Adjust as needed
            },
            dataZoom,
        }
        return this.additionalOption(val)
    }

    parseMeasures() {
        return this.measures.map(measure => convertToTitleCase(measure))
    }

    additionalOption(val) {
        /*
        Additional options for different chart can be added
        with functions named the type of the chart suffixed by 'Chart'
        */
        if (typeof this[`${this.type}Chart`] === 'function') {
            val.series.forEach(item => item.data = [])
            delete val.dataZoom
            return this[`${this.type}Chart`](val)
        }
        return val
    }

    pieAndDoughnutChart(val) {
        let axis = this.dimension_axis === "x" ? val.xAxis : val.yAxis
        let radius = this.type === 'doughnut' ? ["40%", "70%"] : '50%'
        this.data && this.data.forEach((item, mi) => {
            axis.data.push(item[this.dimension])
            this.measures.forEach((key, i) => {
                val.series[i].data.push({
                    value: item[key],
                    name: axis.data[mi]
                })
                val.series[i].radius = radius
                val.series[i].type = "pie"
            })
        })
        delete val.xAxis
        delete val.yAxis
        val.tooltip.formatter = this.chartOptions.formatter + '({d}%)'
        return val
    }

    maxValue(flag) {
        var val = 0
        var result = this.data
        var key = this.measures[0]
        if (result.length) {
            for (let i = 0; i < result.length; i++) {
                val = val + result[i][key];
            }
            if (flag == false) {
                return val.toFixed(2)
            } else {
                const roundValue = Math.ceil(val / 20) * 20;
                const result = roundValue > 100 ? roundValue : 100;
                return result
            }
        }
    }

    pieChart(val) {
        return this.pieAndDoughnutChart(val)
    }

    doughnutChart(val) {
        return this.pieAndDoughnutChart(val)
    }

    scatterChart(val) {
        var dataZoom = this.getDefaultZoom()
        const axisData = this.data.map(item => item[this.dimension]);
        var series = this.measures.map(measure => {
            const data = this.data.map(item => [axisData.findIndex(axis => axis === item[this.dimension]), item[measure]])
            return {
                data,
                type: "scatter",
                name: convertToTitleCase(measure),
                symbolSize: 20,
            }
        })
        if (this.dimension_axis === "x") {
            val.xAxis.data = axisData
        } else {
            val.yAxis.data = axisData
        }
        val.series = series
        val.dataZoom = dataZoom
        return val
    }

    radarChart(val) {
        val.legends.data = this.parseMeasures();
        const indicator = this.data.map(item => {
            const values = this.measures.map(measure => item[measure])
            const max = Math.max(...values) + (Math.min(...values) / 2) // Fixme: Calculation
            return {
                name: item[this.dimension],
                max
            }
        })
        val.radar = {
            indicator
        }
        val.series = [{
            name: this.name,
            type: 'radar',
            data: this.measures.map(name => {
                return {
                    value: this.data.map(item => item[name]),
                    name: convertToTitleCase(name)
                }
            })
        }];
        delete val.xAxis
        delete val.yAxis
        return val
    }

    async mapChart(val) {
        if (!this.measures.length) {
            return val
        }
        return await worldMapChart(this, val)
    }

    gaugeChart(val) {
        val.tooltip.formatter = this.chartOptions.formatter
        val.series = [{
            name: this.name,
            type: 'gauge',
            min: 0,
            max: this.maxValue(true),
            splitNumber: 20,
            progress: {
                show: true
            },
            detail: {
                valueAnimation: true,
                formatter: '{value}'
            },
            data: this.measures.map(name => {
                return {
                    value: this.maxValue(false)
                }
            })
        }];
        delete val.xAxis
        delete val.yAxis
        return val
    }

    heatmapChart(val) {
        const length = this.data.length
        var AxisIndex = this.dimension_axis === "x" ? {xAxisIndex: 0} : {yAxisIndex: 0}
        var dataZoom = [{
            type: 'inside',
            id: this.dimension_axis === "x" ? "insideX" : "insideY",
            start: 0,
            end: length > 15 ? 30 : 100,
            zoomOnMouseWheel: false,
            moveOnMouseMove: true,
            moveOnMouseWheel: true,
            ...AxisIndex
        }]
        const yAxis = [...new Set(this.data.map(item => item[this.dimension]))]
        if (this.measures.length) {
            const xAxis = this.data.map(item => item[this.measures[0]])
            const data = this.data.map((item, index) => {
                return [yAxis.findIndex(res => res == item[this.dimension]), index, item[this.measures[this.measures.length - 1]]]
            })
                .map(item => {
                    return this.dimension_axis === "x" ? [item[1], item[0], item[2] || '-'] : [item[0], item[1], item[2] || '-']
                });
            var option = {
                dataZoom,
                tooltip: {
                    position: 'top'
                },
                title: val.title,
                grid: val.grid,
                xAxis: {
                    type: 'category',
                    splitArea: {
                        show: true
                    }
                },
                yAxis: {
                    type: 'category',
                    splitArea: {
                        show: true
                    }
                },
                visualMap: {
                    min: 0,
                    max: Math.max(...this.data.map(item => item[this.measures[this.measures.length - 1]])),
                    calculable: true,
                    orient: 'vertical',
                    right: 7,
                    bottom: '35%',
                },
                series: [{
                    name: convertToTitleCase(this.measures[this.measures.length - 1]),
                    type: 'heatmap',
                    data,
                    label: {
                        show: true,
                        position: 'inside',
                        rotate: this.dimension_axis === 'x' ? 90 : 0,
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }]
            };
            if (this.dimension_axis === "x") {
                option.xAxis.data = xAxis
                option.yAxis.data = yAxis
            } else {
                option.xAxis.data = yAxis
                option.yAxis.data = xAxis
            }
        } else {
            option = val
        }
        return option
    }

    regressionLineScatterChart(val) {
        echarts.registerTransform(ecStat.transform.regression);
        const axisData = [...new Set(this.data.map(item => item[this.dimension]))]
        var dataZoom = this.getDefaultZoom()
        var data = this.measures.map(measure => {
            const source = this.data.map(item => {
                return [axisData.findIndex(data => data == item[this.dimension]), item[measure]]
            })
            return {source}
        })
        if (!data.length) {
            data = [{source: [[0, 0]]}]
        }
        var option = {
            dataset: [
                ...data,
                {
                    transform: {
                        type: 'ecStat:regression',
                        config: {
                            method: 'exponential'
                        }
                    }
                }
            ],
            title: val.title,
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                }
            },
            xAxis: {
                splitLine: {
                    lineStyle: {
                        type: 'dashed'
                    }
                }
            },
            yAxis: {
                splitLine: {
                    lineStyle: {
                        type: 'dashed'
                    }
                }
            },
            series: [{
                name: 'scatter',
                type: 'scatter',
                datasetIndex: 0
            },
                {
                    name: 'line',
                    type: 'line',
                    smooth: true,
                    datasetIndex: 1,
                    symbolSize: 0.1,
                    symbol: 'circle',
                    label: {
                        show: true,
                        fontSize: 16
                    },
                    labelLayout: {
                        dx: -20
                    },
                    encode: {
                        label: 2,
                        tooltip: 1
                    }
                }
            ],
            dataZoom,
        };
        if (this.dimension_axis === "x") {
            option.xAxis.data = axisData
        } else {
            option.yAxis.data = axisData
        }
        return option
    }

    funnelChart(val) {
        let data = this.dimension_axis === "x" ? val.xAxis.data : val.yAxis.data;
        data = data.filter(item => item).map(item => typeof item === 'number' ? JSON.stringify(item): item)
        const seriesData = {
            name: convertToTitleCase(this.measures[0]),
            type: 'funnel',
            left: '10%',
            top: 80,
            bottom: 60,
            width: '80%',
            min: 0,
            max: 100,
            minSize: '0%',
            maxSize: '100%',
            sort: 'descending',
            gap: 2,
            label: {
                show: true,
                position: 'inside'
            },
            labelLine: {
                length: 10,
                lineStyle: {
                    width: 1,
                    type: 'solid'
                }
            },
            itemStyle: {
                borderColor: '#fff',
                borderWidth: 1
            },
            emphasis: {
                label: {
                    fontSize: 20
                }
            },
        }
        const series = this.measures.map(measure => {
            return {
                data: this.data.map(item => {
                    return {
                        name: item[this.dimension],
                        value: item[measure]
                    }
                }),
                ...seriesData
            }
        })
        val.legend = {
            top: 25,
            data,
            type: 'scroll',
            orient: 'horizontal',
            right: 10,
            bottom: 20,
        }
        val.series = series
        delete val.xAxis
        delete val.yAxis
        return val
    }

    pictorialBarChart(val) {
        var option = val
        var dataZoom = this.getDefaultZoom()
        if (this.measures.length > 1) {
            var axisCategory = this.data.map(item => item[this.dimension])
            var barSeriesData = this.data.map(item => item[this.measures[0]])
            var lineSeriesData = this.data.map(item => item[this.measures[1]])
            option = {
                dataZoom,
                title: {
                    text: convertToTitleCase(this.name, " "),
                    padding: [3, 0, 0, 15],
                    textStyle: {
                        fontSize: 17,
                        fontWeight: 'normal',

                    }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'shadow'
                    }
                },
                legend: {
                    data: [convertToTitleCase(this.measures[0]), convertToTitleCase(this.measures[1])],
                    textStyle: {
                        color: '#ccc'
                    },
                    top: 25,
                },
                series: [{
                    name: convertToTitleCase(this.measures[1]),
                    type: 'line',
                    smooth: true,
                    showAllSymbol: true,
                    symbol: 'emptyCircle',
                    symbolSize: 15,
                    data: lineSeriesData
                },
                    {
                        name: convertToTitleCase(this.measures[0]),
                        type: 'bar',
                        barWidth: 10,
                        itemStyle: {
                            borderRadius: 5,
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                                offset: 0,
                                color: '#14c8d4'
                            },
                                {
                                    offset: 1,
                                    color: '#43eec6'
                                }
                            ])
                        },
                        data: barSeriesData
                    },
                    {
                        name: convertToTitleCase(this.measures[1]),
                        type: 'bar',
                        barGap: '-100%',
                        barWidth: 10,
                        itemStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                                offset: 0,
                                color: 'rgba(20,200,212,0.5)'
                            },
                                {
                                    offset: 0.2,
                                    color: 'rgba(20,200,212,0.2)'
                                },
                                {
                                    offset: 1,
                                    color: 'rgba(20,200,212,0)'
                                }
                            ])
                        },
                        z: -12,
                        data: lineSeriesData
                    },
                    {
                        name: convertToTitleCase(this.measures[1]),
                        type: 'pictorialBar',
                        symbol: 'rect',
                        itemStyle: {
                            color: '#0f375f'
                        },
                        symbolRepeat: true,
                        symbolSize: [12, 4],
                        symbolMargin: 1,
                        z: -10,
                        data: lineSeriesData
                    }
                ]
            };
            var xAxis = {
                data: axisCategory,
                axisLine: {
                    lineStyle: {
                        color: '#ccc'
                    }
                }
            }
            var yAxis = {
                splitLine: {
                    show: false
                },
                axisLine: {
                    lineStyle: {
                        color: '#ccc'
                    }
                }
            }
            if (this.dimension_axis === "x") {
                option.xAxis = xAxis;
                option.yAxis = yAxis;
            } else {
                option.yAxis = xAxis;
                option.xAxis = yAxis;
            }
        }
        return option;
    }

    regenGraphOptions(params) {
        this.params = {...this.params, ...params};
        return this.makeGraphOptions()
    }
}
