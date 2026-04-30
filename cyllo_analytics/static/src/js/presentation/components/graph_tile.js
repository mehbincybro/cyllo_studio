/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useState, useEffect, Component, useRef, onWillStart, onMounted, onWillUpdateProps, status, onWillDestroy} from "@odoo/owl";
import {ChartMaker} from "../../chart_maker"
import { useService, useBus } from "@web/core/utils/hooks";

export const RE_RENDER_GRAPHS = ['map', 'heatmap', 'pictorialBar']
export const NO_ZOOM_CHARTS = ["map", "gauge", "doughnut", "radar", "pie", "funnel"]

/**
 * GraphTile class for displaying a graph in a dashboard view.
 * @class
 */
export class GraphTile extends Component {
    /**
     * Initializes the GraphTile class.
     * @function
     */
    setup() {
        const {
            theme,
        } = this.props
        this.state = useState({
            style: "",
            cardStyle: "",
            theme,
            rec_id: false,
            hasData: true,
            zoom: 0,
            showZoom: false,
            showColorGuide: false
        })
        this.orm = useService('orm')
        this.is_init = true
        this.rootRef = useRef('root')

        useBus(this.env.bus, "REFRESH_GRAPH", async () => {
            this.setStyle()
            await this.reRender()
        })
        let reRender = true
        useEffect(() => {
            if (reRender) {
                this.setupGraphData()
            }
            reRender = this.props.reRender
        }, () => [this.props.item?.query, this.props.value])
        
        useEffect(() => {
            this.setStyle()
        }, () => [this.props.style])
        
        useEffect(() => {
            if (this.props.theme != this.state.theme) {
                this.state.theme = this.props.theme
                this.reRender()
            }
        }, () => [this.props.theme])

        useEffect(() => {
            if (this.options) {
                this.addElement()
            }
        }, () => [this.options])

        onMounted(() => {
            if (this.options) {
                this.addElement()
            }
            this.resizeObserver = new ResizeObserver(() => {
                if (this.eChart) {
                    this.eChart.resize();
                }
            });
            if (this.rootRef.el) {
                this.resizeObserver.observe(this.rootRef.el);
            }
        })
        
        onWillDestroy(() => {
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
            }
        })
    }

    toggleColorGuide() {
        this.state.showColorGuide = !this.state.showColorGuide;
    }

    /**
     * Re-renders the graph when there are changes in the theme.
     * @function
     */
    async reRender() {
        if (this.props.item?.type && RE_RENDER_GRAPHS.includes(this.props.item?.type)) {
            var params = this.props.themeColor ? {themeColor: this.props.themeColor} : {};
            this.options = await this.maker.regenGraphOptions(params)
        } else {
            this.setOptions(this.props.value || this.props.item)
            this.options = await this.maker.makeGraphOptions()
        }
        this.addElement()
    }

    /**
     * Sets up the initial data for the graph.
     * @async
     * @function
     */
    async setupGraphData() {
        if (this.props.value) {
            this.state.rec_id = this.props.value.id
            if (this.is_init) {
                await this.setStyle()
                this.is_init = false
            }
            this.reRender()
        } else if (this.props.item) {
            this.state.rec_id = this.props.item.id
            if (this.is_init) {
                await this.setStyle()
                this.is_init = false
            }
            await this.fetchData(this.props.item)
        }
    }

    /**
     * Sets the style for the graph tile.
     * @function
     */
    setStyle() {
        let cardStyle = "";
        let style = "";
        if (this.props.style) {
            Object.keys(this.props.style).forEach(key => {
                let val = this.props.style[key];
                if (!val.endsWith(';')) val += ';';
                let k = key === 'card_width' ? 'width' : key;
                cardStyle += `${k}:${val} `;
                if (['height', 'width'].includes(key)) {
                    style += `${k}:${val} `;
                }
            });
        }
        this.state.cardStyle = cardStyle + " border-radius: 12px;"
        this.state.style = style + " border-radius: 12px;"
    }

    /**
     * Sets the options for the graph based on the provided props.
     * @param {Object} props - The props for configuring the graph.
     * @function
     */
    setOptions(props) {
        var params = {
            toolFeatures: {},
            measureNames: props.measureNames || {},
            color_mappings: props.color_mappings || [],
        }
        if (this.props.themeColor) {
            params.themeColor = this.props.themeColor
        }
        this.maker = new ChartMaker(props.data, props.dimension, props.measures,
            props.name, props.type, props.dimension_axis, params)
    }

    /**
     * Handles the click event on the chart.
     * @param {Event} ev - The click event.
     * @function
     */
    onClickChart(ev) {
        var hasData = true
        if (this.props.value) {
            hasData = Boolean(this.props.value.data?.length)
        }
        this.props.onClickChart(ev, hasData);
    }

    /**
     * Adds the graph element to the DOM.
     * @async
     * @function
     */
    addElement() {
        if (status(this) === "destroyed") return
        setTimeout(() => {
            if (status(this) === "destroyed") return
            try {
                if (this.eChart) {
                    this.eChart.dispose();
                }
                const themeName = this.props.isDarkMode ? `${this.state.theme}_dark` : this.state.theme
                this.eChart = echarts.init(this.rootRef.el, themeName)
                if (this.options) {
                    this.eChart.setOption(this.options, true)
                }
                this.eChart.resize();
                this.eChart.on('finished', () => {
                    this.props.setImage(this.Image, this.maker?.name || 'Chart', this.props.item?.id || this.props.value?.id)
                })
            } catch (e) {
                console.error("ECharts init error:", e);
            }
        }, 150);
    }

    /**
     * Fetches data for the graph based on the provided item.
     * @param {Object} item - The item containing information for data retrieval.
     * @function
     */
    fetchData(item) {
        if (status(this) == "destroyed") return
        var sql = item.query.replace(/\n/g, ' ');
        this.orm.call("dashboard.config", "sql_execute", [sql]).then(async (res) => {
            if (!res || (res && res.__query_error__)) {
                const msg = res && res.message ? res.message : 'The query returned no data.';
                this.state.hasData = false;
                this.options = {
                    graphic: [{
                        type: 'text',
                        left: 'center',
                        top: 'center',
                        style: { text: msg, fill: '#999', font: '14px sans-serif' }
                    }]
                };
                this.addElement();
                return;
            }

            let measuresList = item.measure;
            if (typeof measuresList === 'string') {
                try {
                    measuresList = JSON.parse(measuresList);
                } catch (e) {
                    measuresList = JSON.parse(measuresList.replaceAll("'", '"'));
                }
            }
            const measureAliases = measuresList.map(m => typeof m === 'object' ? m.alias : m);
            const measureNames = (Array.isArray(measuresList) ? measuresList : []).reduce((acc, m) => {
                if (typeof m === 'object' && m.isPreset) {
                    acc[m.alias] = m.value;
                }
                return acc;
            }, {});

            let props = {
                data: res,
                name: item.name,
                measures: measureAliases,
                measureNames: measureNames,
                dimension: item.dimension,
                dimension_axis: item.dimension_axis,
                type: item.type,
                id: item.id,
                color_mappings: item.color_mappings || [],
            }
            this.state.hasData = Boolean(res?.length)
            this.setOptions(props)
            this.options = await this.maker.makeGraphOptions()
            this.addElement()
        });
    }

    /**
     * Gets the base64-encoded image of the chart.
     * @member {string}
     * @readonly
     */
    get Image() {
        var imgSrc
        try {
            imgSrc = this.eChart.getDataURL({
                type: 'png',
                pixelRatio: 1,
                backgroundColor: '#fff',
            });
        } catch (e) {
            console.warn("Could not get Image from eChart")
        }
        return imgSrc;
    }

    get showZoom() {
        const valueType = this.props.value?.type;
        const itemType = this.props.item?.type;
        return !NO_ZOOM_CHARTS.includes(valueType || itemType);
    }

    async zoom(arg) {
        if (arg === 'in') {
            if (this.options.dataZoom[0].start < 100) {
                this.options.dataZoom[0].start += 1
            }
        } else {
            if (this.options.dataZoom[0].start > 10) {
                this.options.dataZoom[0].start -= 1
            }
        }
        this.state.zoom = this.options.dataZoom[0].start
        this.state.showZoom = true;
        setTimeout(() => {
            this.state.showZoom = false;
        }, 500)
        this.eChart.dispose()
        this.addElement()
    }
}

GraphTile.template = "GraphTile";
GraphTile.defaultProps = {
    style: {
        height: `400px;`,
        width: `440px;`,
    },
    footer: false,
    onClickChart: () => {
    },
    setImage: () => {
    },
    theme: "",
    reRender: true,
    width: "",
    isDarkMode: false,
}
GraphTile.props = {
    onClickChart: {type: Function, optional: true},
    reRender: {type: Boolean, optional: true},
    width: {type: String, optional: true},
    setImage: {type: Function, optional: true},
    style: {type: Object, optional: true},
    theme: {type: String, optional: true},
    themeColor: {type: Object, optional: true},
    value: {type: Object, optional: true},
    item: {type: Object, optional: true},
    footer: {type: Boolean, optional: true},
    slots: {type: Object, optional: true},
    toggleClass: {type: String, optional: true},
    itemId: {type: Number, optional: true},
    isDarkMode: {type: Boolean, optional: true},
}