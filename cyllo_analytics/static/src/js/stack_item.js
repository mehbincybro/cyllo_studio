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
        this.wrapper = document.createElement('div')
        this.wrapper.classList.add("edit-border", "background-color-class", "cy_tile", "cy_dashboard_chart", "card")
        
        // Ensure the component fills available space flexibly
        this.wrapper.style.width = '100%';
        this.wrapper.style.height = '100%';
        this.wrapper.style.boxSizing = 'border-box';
        this.wrapper.style.border = `1.5px ridge #000000;`
        this.wrapper.style.display = 'flex'
        this.wrapper.style.flexDirection = 'column'
        this.wrapper.style.overflow = 'hidden'

        // Add header
        this.header = document.createElement('div')
        this.header.className = "sheet-header d-flex justify-content-between align-items-center"
        this.title = document.createElement('div')
        this.title.className = "sheet-title"
        this.title.innerText = this.maker.name
        this.header.appendChild(this.title)
        this.wrapper.appendChild(this.header)

        this.el = document.createElement('div')
        this.el.style.width = '100%'
        this.el.style.flex = '1'
        this.el.style.minHeight = '0'
        this.el.style.boxSizing = 'border-box'
        this.wrapper.appendChild(this.el)

        this.parent.appendChild(this.wrapper)

        const themeName = this.params.isDarkMode ? `${this.theme}_dark` : this.theme
        this.eChart = echarts.init(this.el, themeName)
        this.eChart.setOption(this.options)

        // Add ResizeObserver to handle asynchronous layout changes and grid resizing
        this.resizeObserver = new ResizeObserver(() => {
            if (this.eChart) {
                this.eChart.resize();
            }
        });
        this.resizeObserver.observe(this.el);

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
        if (this.wrapper && this.parent.contains(this.wrapper)) {
            this.parent.removeChild(this.wrapper)
        }
        this.theme = theme ? theme : this.theme
        this.params.graph_height = height || this.params.graph_height
        const unit = Math.max(this.params.unit || 1, 1.0001)
        if (unit > 1) {
            width = (((unit - 1) * width) + 5) / (unit - 1)
        }
        this.params.graph_width = width || this.params.graph_width
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
        element.classList.add("edit-border")
        element.classList.add("kpi_class")
        element.style.width = '100%'
        element.style.height = '100%'
        element.style.boxSizing = 'border-box'
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
        this.element.style.width = '100%'
        this.element.style.height = '100%'
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
        element.classList.add("cyllo_table")
        element.style.width = '100%'
        element.style.height = '100%'
        this.mountChild('100%', '100%')
    }
    async reRender(theme, height, width){
        var childElement = this.element.querySelector(".cy_sheet_scrollable_table")
        if (childElement){
            this.element.removeChild(childElement)
            this.element.style.width = '100%'
            this.element.style.height = '100%'
            this.mountChild('100%', '100%')
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
                    width: width.includes('%') ? width : `${width}px;`,
                    height: height.includes('%') ? height : `${height}px;`
                }
            },
            env: this.env
        })
    }
}