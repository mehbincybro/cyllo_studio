/** @odoo-module **/
import { ChartMaker } from "./chart_maker"
const { Component, useRef, onMounted, useState } = owl;
import { browser } from "@web/core/browser/browser";
import { KpiSheetChart } from "./kpi_sheet_chart";
import { Table } from "./table/table";


export class StackItem {
    /**
     * Class for creating a stack item in a Cyllo dashboard.
     * @param {Element} element - The DOM element where the stack item is created.
     * @param {object} props - Properties for the stack item.
     * @param {GridStack} stack - The GridStack instance.
     * @param {object} theme - The theme for the stack item.
     * @param {object} params - Additional parameters.
     */
    constructor(element, props, stack, theme, params= {} ){
        this.setup(element, props, stack, theme, params);
    }
    async setup(element, props, stack, theme, params) {
        // Create a ChartMaker instance
        this.maker = new ChartMaker(props.data, props.dimension, props.measures,
         props.name, props.type, props.dimension_axis, params)
         // Generate graph options using the ChartMaker
        this.options = await this.maker.makeGraphOptions()
        this.stack = stack // GridStack instance
        this.theme = theme
        this.params = params
        this.parent = element
        this.addElement()
    }
    /**
     * Add the ECharts graph element to the stack item.
     */
    addElement(){
        this.el = document.createElement('div')
        this.el.classList.add("edit-border", "background-color-class")
        const { unit, graph_height, graph_width } = this.params
        var width = graph_width ? (unit -1) * graph_width : this.parent.clientWidth
        var height = ((unit - 1) * (graph_height || 3)) - 5
        width -= 10
        this.el.style.width = width + 'px'
        this.el.style.height = height + 'px'
        this.el.style.border = `1.5px ridge #000000;`
        const themeName = this.params.isDarkMode ? `${this.theme}_dark` : this.theme
        this.eChart = echarts.init(this.el, themeName)
        this.eChart.setOption(this.options)
        this.parent.appendChild(this.el)
        this.addChartProps()
    }
    addChartProps() {
        if (this.params.off){
            this.eChart.off() // Todo: Turns off the click functionality in the graph
        }
    }
    /**
     * Re-render the stack item with the specified theme.
     * @param {object} theme - The theme for the stack item.
     */
    reRender(theme, height, width){
        this.parent.removeChild(this.el)
        this.theme = theme ? theme : this.theme
        this.params.graph_height = height || this.params.graph_height
        const { unit } = this.params
        width = (((unit -1) * width) + 5)/ (unit - 1)
        this.params.graph_width = width  || this.params.graph_width
        this.addElement()
    }
}

export class StackKpiItem {
/**
     * Class for creating a stack item for Key Performance Indicators (KPIs).
     * @param {Element} element - The DOM element where the stack item is created.
     * @param {object} props - Properties for the stack item.
     * @param {GridStack} stack - The GridStack instance.
     */
    constructor(element, props, stack, env, params= {}){
        this.params = params
        this.element = element
        this.setup(element, props, stack, env, params)
    }
    async setup(element, props, stack, env) {
        this.stack = stack
        var width = element.clientWidth - 10
        var height = element.clientHeight - 10
        element.classList.add("edit-border")
        element.classList.add("kpi_class")
        element.style.width = width + 'px'
        element.style.height = height + 'px'
        await owl.mount(KpiSheetChart, element, {
            props: {
                query: props,
                kpi: props.kpi,
                editSheet: true,
                name: props.name
            },
            env
        })
    }
    reRender(theme, height, width){
        height = height ? height : 1
        width = width ? width : 3
        var { unit } = this.params
        var w = ( width * unit ) - 10
        var h = ( height * unit ) - 10
        this.element.style.width = w + 'px'
        this.element.style.height = h + 'px'
    }
}

export class StackTableItem {
/**
     * Class for creating a stack item for Key Performance Indicators (KPIs).
     * @param {Element} element - The DOM element where the stack item is created.
     * @param {object} props - Properties for the stack item.
     * @param {GridStack} stack - The GridStack instance.
     */
    constructor(element, props, stack, env, params= {}){
        this.element = element
        this.env = env
        this.props = props
        this.params = params
        this.setup(element, props, stack, env, params)
    }
    async setup(element, props, stack, env) {
        props.dimension = [props.dimension]
        var { style: { w, h }, unit } = this.params
        element.classList.add("cyllo_table")
        h = (unit * h) - 8
        w = (unit * w) - 12
        this.mountChild(w, h)
    }
    async reRender(theme, height, width){
        var { unit } = this.params
        height = (unit * height) - 8
        width = (unit * width) - 12
        var childElement = this.element.querySelector(".cy_sheet_scrollable_table")
        if (childElement){
            this.element.removeChild(childElement)
            this.element.style.width = width + 'px'
            this.element.style.height = height + 'px'
            this.mountChild(width, height)
        }
    }
    async mountChild(width, height) {
        await owl.mount(Table, this.element, {
            props: {
                data: this.props,
                name: this.props.name,
                toggleClass: "edit-border",
                theme: this.params.theme,
                style: {
                    width: `${width}px;`,
                    height: `${height}px;`
                }
            },
            env: this.env
        })
    }
}