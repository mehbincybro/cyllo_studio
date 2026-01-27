/** @odoo-module **/
const { useState, onWillStart, onMounted, useEffect, useRef } = owl;
import { useService } from "@web/core/utils/hooks";
import { ThemeMaker } from "@cyllo_analytics/js/theme_maker";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
const TIMEFRAMES = {
  'This Week': 'week',
  'This Quarter': 'quarter',
  'Last Quarter': 'quarter_l',
  'This Month': 'month',
  'Last Month': 'month_l',
  'This Year': 'year',
  'Last Year': 'year_l',
  'Custom': 'custom'
}

export function CyAnalyticMixin(CyComponent) {
    return class extends CyComponent {
        setup() {
            super.setup();
            this.env.bus.addEventListener("PN:RLD", () => setTimeout(() => { window.location.reload() }, 50))
            this.edit = false;
            this.dateFormats = {
                display: 'YYYY/MM/DD',
                actual: 'YYYY-MM-DD',
            }
           useEffect(() => {
               const navBar = document.body.querySelector('.o_navbar');
               navBar.style.display = "none";
               return () => {
                   navBar.style.display = "flex";
               }
            })
            this.filters = useState({})
            const { id, removeManually, getKeyValue, saveToSession } = useSaveContext()
            this.saveContext = { removeManually, getKeyValue, saveToSession }
            this.removeManually = removeManually
            this.hasAccess = session.is_admin;
            this.id = id
            this.orm = useService("orm")
            this.actionService = useService("action")
            this.notification = useService('notification');

            this.busService = this.env.services.bus_service
            this.channel = "CY:ANALYTICS"
            this.busService.addChannel(this.channel)
            this.busService.addEventListener("notification", this.onMessage.bind(this))
            this.themes = []
            this.themeState = useState({
                theme: false,
                theme_id: false,
                items: [],
                currentTheme: false,
            });
            this.bannerState = useState({
                banner: []
            })
            this.filterData = {
                selected: this.defaultFilterTag
            }
            this.ChartData = useState({
                data: [],
                itemData: [],
                items: [],
                loading: true,
            })
            this.timFrameState = useState({
                selected: this.defaultFilterTag,
                date_0 : "",
                date_1 : "",
                company : [],
                user : []
            })
            this.dashboard = useRef('dashboard')
            this.state = useState({
                width: 0,
                globalFilters: [],
                sources: [],
                optionClass: 'collapse-filter',
                options: [],
                currentItem: false,
                sortedItems: [],
                search: "",
                previousSearch: "",
                showInfo: false,
            })
            onWillStart(this.onWillStart)
            useEffect(() => {
                this.state.sortedItems = this.sortedItems
                const filter = this.timFrameState.selected.split('_')
                const flag = !Boolean(filter.length > 1)
                this.dateOrder(flag, filter[0], true)
                this.applyAllFilters()
            }, () => [this.ChartData.items])
            useEffect(() => {
                if (!this.edit && (this.state.search.length || this.state.previousSearch.length)){
                    const data = this.state.search.length > this.state.previousSearch.length ? this.state.sortedItems : this.items
                    const searchWord = this.state.search.toLowerCase().split(' ')
                    var filtered = data.filter(item => {
                        const names = item.name.toLowerCase().split(" ")
                        var nameLength = names.length -1
                        var subNameMatch = true;
                        for (let i = 0; i <= searchWord.length -1; i++){
                            if (i > nameLength) return false;
                            if (searchWord.length === 1) {
                                subNameMatch = names.some(item => item.includes(searchWord[i]))
                                continue;
                            }
                            if (i === searchWord.length -1 && subNameMatch) {
                                subNameMatch = names[i].includes(searchWord[i])
                            }
                            else {
                                subNameMatch = names[i] === searchWord[i]
                            }
                        }
                        return subNameMatch;
                    })
                    this.state.search.length && this.resetPosition()
                    this.state.sortedItems = this.state.search.length ? filtered : this.sortedItems
                    this.state.previousSearch = this.state.search
                }

            }, () => [this.state.search])
        }
         get TimeFrame(){
            return TIMEFRAMES
        }
        async onWillStart() {
            var data = await this.orm.call("dashboard.config", "get_sheets", [this.id])
            this.items = data[0]
            this.state.showInfo = !Boolean(this.items.length);
            this.ChartData.items = data[0]
            this.id = data[1]
            this.name = data[3]
            this.state.name = data[3]
            this.themeState.theme = data[2]
            this.bannerState.banner = data[4]
            if (this.themeState.theme) {
                this.themeState.theme_id = data[2].id
                var theme_maker = new ThemeMaker(this.themeState.theme)
                this.themeState.currentTheme = theme_maker.getTheme()
            }
            this.fetchThemes()

        }
        onClickSearch() {
            const searchRef = this.dashboard.el.querySelector(".dash_searchbar");
            [".icon", "input[type='text']"].forEach(item => $(searchRef).find(item).toggleClass("active"))
            if (!this.state.search.length) {
                $(searchRef).find(".search_input_main").focus();
            }else {
                this.resetPosition()
                this.state.sortedItems = this.sortedItems
            }
            this.state.search = ""
            this.state.previousSearch = ""
        }
        onMessage({ detail: notifications }) {
            notifications = notifications.filter(item => item.payload.channel === "CY:ANALYTICS")
            notifications.forEach(item => {
                var res = this.ChartData.itemData.find(data => data.id === item.payload.id )
                if (res) {
                    res.data = item.payload.result
                    this.ChartData.data.push(res)
                }
            })
        }
        dateOrder(flag, value, defaultVal){
            var momentValue = flag ? moment() : moment().subtract(1,value);
            var startDate = momentValue.startOf(value).toDate();
            var endDate = momentValue.endOf(value).toDate();
            this.timFrameState.date_0 = moment(startDate).format(this.dateFormats.actual)
            this.timFrameState.date_1 = moment(endDate).format(this.dateFormats.actual)
            this.filters['start-date'] = moment(startDate).format(this.dateFormats.actual)
            this.filters['end-date'] = moment(endDate).format(this.dateFormats.actual)
            if (defaultVal){
                this.filterData.date_0 = moment(startDate).format(this.dateFormats.display)
                this.filterData.date_1 = moment(endDate).format(this.dateFormats.display)
            }
        }
        resetPosition(){
            this.positions = {
                x: 0,
                y: 0,
                w: 0,
                h: 0,
                ft: true,
                maxH: []
            }
            this.firstLine = true
        }
        storeDefaultFilter() {
            var defaultFilterObject = {
                ...this.timFrameState
            }
            this.saveContext.saveToSession("defaultFilter", defaultFilterObject, true)
        }
        get defaultFilterOpts() {
            return this.saveContext.getKeyValue("defaultFilter")
        }
        get defaultFilterTag() {
            var selectedTag = 'month_l'
            if (this.defaultFilterOpts?.selected){
                selectedTag = this.defaultFilterOpts.selected == "custom" ? selectedTag : this.defaultFilterOpts.selected
            }
            return selectedTag
        }
        /**
         * Fetch available themes.
         */
        async fetchThemes() {
            this.themes = await this.orm.call("dashboard.theme", 'search_read', [], {
                fields: ["name"]
            })
        }
        /**
         * Fetch data for charts.
         */
        async fetchData() {
            var itemLength = this.items.length
            this.ChartData.loading = Boolean(itemLength)
            this.items.forEach((item, i) => {
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
                    this.ChartData.data.push(props)
                    itemLength --;
                    this.ChartData.loading = !(itemLength == 0)
                })
            })
        }
        getKpi(item) {
            return {
                description: item.kpi_description,
                redirect: item.kpi_redirect,
                target: item.kpi_target,
                measureView: item.kpi_view,
                icon: item.kpi_icon,
                model: item.table_ids[0].model
            }
        }
        get sortedItems() {
            const copiedItems = this.items.slice();
            const value = copiedItems.sort((a, b) => {
                const aValue = a.dashboard_sheet_option_ids.length ? a.dashboard_sheet_option_ids[0].attributes : {};
                const bValue = b.dashboard_sheet_option_ids.length ? b.dashboard_sheet_option_ids[0].attributes : {};
                // Compare y values first
                if (aValue.y !== undefined && bValue.y !== undefined) {
                    if (aValue.y < bValue.y) return -1;
                    if (aValue.y > bValue.y) return 1;
                } else {
                    // Handle case where y is undefined
                    if (aValue.y === undefined && bValue.y !== undefined) return 1;
                    if (aValue.y !== undefined && bValue.y === undefined) return -1;
                }
                // If y values are equal or both are undefined, compare x values
                if (aValue.x !== undefined && bValue.x !== undefined) {
                    if (aValue.x < bValue.x) return -1;
                    if (aValue.x > bValue.x) return 1;
                } else {
                    // Handle case where x is undefined
                    if (aValue.x === undefined && bValue.x !== undefined) return 1;
                    if (aValue.x !== undefined && bValue.x === undefined) return -1;
                }
                // If both y and x values are equal or both are undefined, consider objects equal
                return 0;
            });
            return value
        }
        applyAllFilters(){
            this.state.sortedItems.forEach(item => {
                this.applyItemFilter(item)
            })
            if (this.presentation) {
                this.fetchData()
            }
        }
        applyItemFilter(item){
            var domains = item.filter_ids
                .filter(item => item.is_active)
                .map(item => item.domain)
            var where = domains.join(' AND ')
            item.sheet_filter_ids.forEach(filter => {
                var { operator, code } = filter.global_filter_id
                var value = this.filters[code]
                if(value?.length){
                    value = typeof value == 'string' ? `'${value}'`:
                            typeof value == 'object' ? `(${value.join(', ')})` : value
                    var domain = `${filter.field} ${operator} ${value}`
                    domain = where ? ` AND ${domain}` : domain
                    where += domain
                }
            })
            var new_query = this.applyFilters(item.query, where)
            item.query = new_query
        }
        applyFilters(query, newCondition) {
            var currentWhere = query.match(/WHERE\s+([^]+?)(?:GROUP BY|ORDER BY|LIMIT|$)/i)
            if (currentWhere) {
                let conditions = currentWhere[1].trim()
                if(newCondition){
                    query = query.replace(conditions, newCondition)
                } else {
                    query = query.replace(conditions, '')
                    query = query.replace('WHERE', '')
                }
            } else {
                const groupByRegex = /\bGROUP\s+BY\b/i;
                const orderByRegex = /\bORDER\s+BY\b/i;
                const limitRegex = /\bLIMIT\b/i;
                const insertPosition =
                    groupByRegex.test(query) ? groupByRegex.exec(query).index :
                    orderByRegex.test(query) ? orderByRegex.exec(query).index :
                    limitRegex.test(query) ? limitRegex.exec(query).index :
                    query.length;
                const beforeInsert = query.substring(0, insertPosition);
                const afterInsert = query.substring(insertPosition);
                if(newCondition){
                    query = `${beforeInsert} WHERE ${newCondition} ${afterInsert}`
                }
            }
            return query;
        }
        static props = { ...standardActionServiceProps }
    }
}