/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useState, useEffect, Component, useRef, onWillStart, onMounted, onWillUpdateProps, status} from "@odoo/owl";
import {ChartMaker} from "../../chart_maker"
import {useService} from "@web/core/utils/hooks";
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
            height,
            width
        } = this.props
        this.state = useState({
            style: "",
            cardStyle: "",
            theme,
            rec_id: false,
            hasData: true,
        })
        this.orm = useService('orm')
        this.is_init = true
        this.rootRef = useRef('root')
        this.env.bus.addEventListener("REFRESH_GRAPH", async () => {
            this.setStyle()
            await this.reRender()
        })
        useEffect(() => {
            this.setupGraphData()
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
    }

    /**
     * Re-renders the graph when there are changes in the theme.
     * @function
     */
    async reRender() {
        if (this.eChart) {
            if (this.props.item?.type == 'map') {
                var params = this.props.themeColor ? {themeColor: this.props.themeColor} : {};
                this.options = await this.maker.regenGraphOptions(params)
            }
            this.eChart.dispose()
            this.addElement()
        }
    }

    /**
     * Sets up the initial data for the graph.
     * @async
     * @function
     */
    async setupGraphData() {
        if (this.props.value) {
            this.state.rec_id = this.props.value.id
            this.setOptions(this.props.value)
            if (this.is_init) {
                await this.setStyle()
                this.is_init = false
            }
            this.options = await this.maker.makeGraphOptions()
            if (this.props.value.type == 'map') {
                this.addElement()
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
        var cardStyle = Object.keys(this.props.style).map(key => {
            return `${key}:${this.props.style[key]}`;
        }).join('');
        var style = Object.keys(this.props.style).filter(key => ['height', 'width'].includes(key)).map(key => {
            return `${key}:${this.props.style[key]}`;
        }).join('');
        this.state.cardStyle = cardStyle
        this.state.style = style
    }

    /**
     * Sets the options for the graph based on the provided props.
     * @param {Object} props - The props for configuring the graph.
     * @function
     */
    async setOptions(props) {
        var params = {
            toolFeatures: {},
        }
        if (this.props.themeColor) {
            params.themeColor = this.props.themeColor
        }
        this.state.hasData = Boolean(props.data?.length)
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
    async addElement() {
        if (status(this) === "destroyed") return
        try {
            this.eChart = echarts.init(this.rootRef.el, this.state.theme)
            this.eChart.setOption(this.options)
            this.eChart.on('finished', () => {
                this.props.setImage(this.Image, this.maker.name, this.props.item?.id || this.props.value?.id)
            })
        }
        catch { }
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
            this.state.rec_id = res.id
            let props = {
                data: res,
                name: item.name,
                measures: eval(item.measure),
                dimension: item.dimension,
                dimension_axis: item.dimension_axis,
                type: item.type,
                id: item.id,
            }
            await this.setOptions(props)
            this.options = await this.maker.makeGraphOptions()
            if (item.type == 'map') {
                this.addElement()
            }
            this.reRender()
        })
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
                type: 'png', // can be jpeg or png
                pixelRatio: 1, // image's ratio. default is 1
                backgroundColor: '#fff', // hex color defining the background of the chart
            });
        } catch (e) {
            console.warn("Could not get Image from eChart")
        }
        return imgSrc;
    }

}

// Define the template for the GraphTile component
GraphTile.template = "GraphTile";
// Define default properties for the GraphTile component
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
}
GraphTile.props = {
    onClickChart: {type: Function, optional: true},
    setImage: {type: Function, optional: true},
    style: {type: Object, optional: true},
    theme: {type: String, optional: true},
    themeColor: {type: Object, optional: true},
    value: {type: Object, optional: true},
    item: {type: Object, optional: true},
    footer: {type: Boolean, optional: true},
    slots: {type: Object, optional: true},
    toggleClass: {type: String, optional: true},
}