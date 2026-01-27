/** @odoo-module **/
import {registry} from "@web/core/registry";
import {StackItem, StackKpiItem, StackTableItem} from "./stack_item";
import {CylloDashboard} from "./cyllo_dashboard";
import {browser} from "@web/core/browser/browser";
const {useState, useRef, onMounted} = owl;


class EditDashboard extends CylloDashboard {
    /** Class for the dashboard editing feature */
    setup() {
        super.setup();
        this.edit = true;
        this.stackItems = {}
        this.ref = useRef('chart-container')
        this.state = useState({
            change: false,
            rearrange: true,
            gridStackData: []
        })
        onMounted(this.fetchData)
        this.rearrangeId = 1
    }

    rearrange() {
        try {
            const newPosition = {x: 0, y: 0, w: 0, h: 0, items: {0: [0]}, type: "kpi"}
            for (const val of this.shuffleArrayItems) {
                const {height: chartHeight, width: chartWidth} = this.getChartSizes(val.type, this.rearrangeId)
                if (val.type !== 'kpi' && newPosition.type === 'kpi') {
                    newPosition.x = 0
                    newPosition.y = Math.max(...newPosition.items[newPosition.y])
                }
                if ((newPosition.x + chartWidth) > 12) {
                    newPosition.x = 0
                    newPosition.y = Math.max(...newPosition.items[newPosition.y])
                }
                newPosition.type = val.type
                if (!newPosition.items[newPosition.y]) {
                    newPosition.items[newPosition.y] = [newPosition.y + chartHeight]
                } else {
                    newPosition.items[newPosition.y].push(newPosition.y + chartHeight)
                }
                const $el = $(this.ref.el).find(`#elem_${val.id}`)
                Object.assign(this.stack.engine.nodes.find(item => val.id === item.id), {
                    x: newPosition.x,
                    y: newPosition.y,
                    w: chartWidth,
                    h: chartHeight,
                });
                $el.attr('gs-x', newPosition.x)
                $el.attr('gs-y', newPosition.y)
                $el.attr('gs-w', chartWidth)
                $el.attr('gs-h', chartHeight)
                const stackItem = this.stackItems[`elem_${val.id}`]
                stackItem.reRender(false, chartHeight, chartWidth)
                newPosition.x += chartWidth
            }
            this.state.change = true
            this.rearrangeId++
        }catch {}
    }

    get shuffleArrayItems() {
        const array = [...this.vals.children];
        array.sort((a, b) => {
            const isNoResizeA = a.noResize === true;
            const isNoResizeB = b.noResize === true;
            if (isNoResizeA && !isNoResizeB) {
                return -1;
            } else if (!isNoResizeA && isNoResizeB) {
                return 1;
            }
            return Math.random() - 0.5;
        });

        return array;
    }

    onSetTemplate() {
    }

    /**
     * Fetch data for the dashboard and set up event listeners.
     */
    fetchData() {
        this.stack = GridStack.init({
            float: true,
            verticalMargin: 100,
            horizontalMargin: 100,
        }, this.ref.el)
        // Iterate through items and create dashboard components
        this.state.sortedItems.forEach((item, i) => {
            var sql = item.query.replace(/\n/g, ' ');
            this.orm.call("dashboard.config", "sql_execute", [sql]).then((res) => {
                let props = {
                    data: res,
                    name: item.name,
                    measures: eval(item.measure),
                    dimension: item.dimension,
                    dimension_axis: item.dimension_axis,
                    type: item.type,
                    id: item.id
                }

                if (item.type == 'kpi') {
                    props.kpi = this.getKpi(item)
                }

                var element = document.createElement('div')
                element.className = "card edit_elem"
                element.id = `elem_${item.id}`
                element.sheetId = item.id
                element.resId = this.id
                let girdOptions = this.gridValues(item)
                const {dashboard_sheet_option_ids: option} = item
                this.stack.addWidget(element, girdOptions)
                const unit = this.state.width
                if (item.type == "kpi") {
                    const kpiStyle = this.computeKpiStyle(option)
                    element.className += " cy-sheet_progress-card"
                    this.stackItems[element.id] = new StackKpiItem(element, props, this.stack, this.env, {
                        kpiStyle,
                        unit
                    })
                } else if (item.type == "table") {
                    const kpiStyle = this.computeKpiStyle(option)
                    var {graph_height, graph_width, x, y} = option[0].attributes
                    this.stackItems[element.id] = new StackTableItem(element, props, this.stack, this.env, {
                        style: {
                            h: graph_height, w: graph_width, x, y
                        }, kpiStyle, unit, theme: this.themeState.currentTheme
                    })
                } else {
                    var {graph_height, graph_width, x, y} = option[0].attributes
                    var params = {
                        themeColor: this.themeState.theme.theme_color_ids,
                        unit: this.state.width,
                        graph_height,
                        isDarkMode: this.state.darkMode
                    }
                    this.stackItems[element.id] = new StackItem(element, props, this.stack, this.themeState.currentTheme, params)
                }
                this.vals = this.stack.save(false, true)
            })
        })
        this.stack.on('change', this.onChange.bind(this))
        this.stack.on('dragstop', this.dragStop.bind(this))
        this.stack.on('resize', (event, el) => {
            var stack_item = this.stackItems[el.id]
            const h = el?.gridstackNode?.h
            const w = el?.gridstackNode?.w
            stack_item.reRender(false, h, w)
        });
    }

    computeKpiStyle(option) {
        const unit = this.state.width
        var {graph_height, graph_width, x, y} = option[0].attributes
        graph_height = (unit * graph_height) - 10
        graph_width = (unit * graph_width) - 10
        x = x * unit
        y = y * unit
        return {
            height: `${graph_height}px;`,
            width: `${graph_width}px;`,
            top: `${y}px;`,
            left: `${x}px;`,
        }
    }

    /**
     * Save the current dashboard configuration.
     */
    onSave() {
        var vals = this.stack.save(false, true)
        this.orm.call("dashboard.config", "save_position", [this.id, vals])
        this.disableChange()
        this.vals = vals
    }

    /**
     * Discard any unsaved changes to the dashboard.
     */
    async onDiscard() {
        for (var val of this.vals.children) {
            var $el = $(this.ref.el).find(`#elem_${val.id}`)
            $el.attr('gs-x', val.x)
            $el.attr('gs-y', val.y)
            $el.attr('gs-w', val.w)
            $el.attr('gs-h', val.h)
            var stack_item = this.stackItems[`elem_${val.id}`]
            stack_item.reRender(false, val.h, val.w)
        }
        this.disableChange()
    }

    /**
     * Disable the change state for the dashboard.
     */
    disableChange() {
        this.state.change = false
    }

    /**
     * Handle changes in the dashboard configuration.
     */
    onChange() {
        this.state.change = true
    }

    /**
     * Navigate back to the original dashboard.
     * @returns {Object} - The action to navigate back.
     */
    onBack() {
        browser.history.go(-1)
    }

    /**
     * Get grid options for the given item.
     * @param {Object} item - The dashboard item.
     * @returns {Object} - The grid options.
     */
    gridValues(item) {
        var sheetPosition = item.dashboard_sheet_option_ids
        var [graph_height, graph_width] = [3, 4]
        if (sheetPosition.length) {
            var x, y
            ({graph_height, graph_width, x, y} = sheetPosition[0].attributes);
        }
        var girdOptions = {
            w: graph_width,
            h: graph_height,
            id: item.id,
            ...this.gridStackOptions,
            type: item.type
        }
        if (this.state.rearrange) {
            girdOptions = {...girdOptions, x, y}
        }
        if (item.type === 'kpi') {
            girdOptions.noResize = true
        }
        return girdOptions;
    }

    /**
     * Get grid stack options.
     * @returns {Object} - Grid stack options.
     */
    get gridStackOptions() {
        return {
            noMove: false,
            noResize: false,
            locked: false
        }
    }

    dragStop(event, el) {
        if (el.classList.contains('kpi_class')) {
            const id = el.getAttribute("id")
            this.stackItems[id]?.reRender(false, 1, 3)
        }
    }
}

// Define the template for the EditDashboard component
EditDashboard.template = "cyllo_analytics.EditDashboard"
// Register the EditDashboard component in the actions category
registry.category("actions").add("edit_dashboard", EditDashboard);