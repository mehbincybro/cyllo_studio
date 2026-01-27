/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {ModelViewer} from "./model_viewer";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {DragItem, DropZone} from "./drag_n_drop"
import {GraphTile} from "@cyllo_analytics/js/presentation/components/graph_tile";
import {SQLEditor} from "./editor/SQLEditor";
import {FilterDialog} from "./sheet_filter/filter_dialog";
import {browser} from "@web/core/browser/browser";

const {Component, useState, onWillStart, useEffect, onWillDestroy, useRef} = owl
import {useSaveContext} from "@cyllo_analytics/js/useSaveContext";
import {SQLQueryParser} from "./query/query_manager"
import {FieldAutoComplete} from "@cyllo_analytics/js/sheet_filter/field_auto_complete"
import {FieldAutoCompleteGlobal} from "@cyllo_analytics/js/sheet_filter/field_auto_complete_global"
import {KpiSheet} from "@cyllo_analytics/js/KpiSheet";
import {Table} from "@cyllo_analytics/js/table/table";
import {Number} from "@cyllo_analytics/js/fields/number";
import {DeleteDialog} from "./delete_dialog_box";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";


export class SheetDeleteDialog extends DeleteDialog {
    async _confirm() {
        if (typeof this.props.callBackAction === 'function') {
            this.props.callBackAction()
            this.props.close()
        } else {
            await this.orm.unlink(this.props.model, [this.props.id]);
            this.props.removeManually && this.props.removeManually()
            this.props.close()
            this.props.onConfirm()
        }

    }

    static defaultProps = {
        ...DeleteDialog.defaultProps,
        callBackAction: false
    }
}

class FieldList extends Component {
    setup() {

        this.state = useState({
            data: this.props.data,
            search: ''
        })
        useEffect(() => {
            this.state.data = this.props.data
        }, () => [this.props.data])
        useEffect(() => {
            if (this.state.search) {
                this.state.data = this.props.data.filter(item => {
                    var search = this.state.search.toLowerCase()
                    return item.label.toLowerCase().includes(search) || item.name.toLowerCase().includes(search)
                })
            } else {
                this.state.data = this.props.data
            }
        }, () => [this.state.search])
    }
}

FieldList.template = "FieldList"
FieldList.components = {DragItem}

export class CylloSheet extends Component {
    /** Class for creating a CylloSheet component. */
    setup() {
        const {id, saveManually, removeManually} = useSaveContext()
        this.id = id
        this.isNewSheet = false;
        onWillDestroy(removeManually)
        this.sheet = useRef('sheet')
        this.saveManually = saveManually
        this.removeManually = removeManually
        this.model = 'dashboard.sheet'
        this.orm = useService("orm")
        this.dialog = useService("dialog")
        this.notification = useService("notification")
        this.avoid_fields = []
        this.action = useService("action")
        this.ChartData = useState({data: {}, generate: false})
        this.measures_field_types = ["float", "monetary", "integer"]
        this.avoid_field_types = ["many2many", "one2many"]
        this.unlinkList = {
            axis: [],
            tables: [],
            where: [],
            configs: [],
        }
        this.previewLimit = {
            is_enable: false,
            limit: 0
        }
        this.filterOptions = {}
        this.state = useState({
            name: false,
            models: [],
            fields: [],
            limit: 0,
            query: '',
            need_save: false,
            sheetTypes: [],
            chart: [],
            selectedType: [1, 'line'],
            configs: [],
            globalFilters: [],
            image: "",
            option: {},
            kpiValue: {}
        })
        this.query_data = useState({
            dimension: [],
            measure: [],
            join: [],
            joinData: [],
            where: [],
            groupBy: [],
            orderBy: [],
            dimension_axis: 'x',
        })
        this.navState = useState({
            allRecords: [],
            recordValue: 1
        })
        onWillStart(async () => {
            this.state.sheetTypes = await this.orm.searchRead('dashboard.sheet.type', [])
            this.navState.allRecords = await this.orm.search('dashboard.sheet', [])
            if (this.id) {
                var value = this.navState.allRecords.findIndex(item => item == this.id)
                this.navState.recordValue = value + 1
            }
            if (this.props.action.context?.dashboard_id) {
                var context = this.props.action.context
                this.state.configs.push({id: context.dashboard_id, display_name: context.display_name})
            }
            await this.orm.call(this.model, 'get_config_data', []).then((res) => {
                this.state.sheetTypes = res.sheet_types
                this.previewLimit = {
                    is_enable: res.is_enable,
                    limit: res.limit
                }
            })
        })
        this.env.bus.addEventListener("CY:UPDATE_UNLINKS", (ev) => {
            var {type, id} = ev.detail
            this.unlinkList[type].push(id)
        })
        this.env.bus.addEventListener("CY:UPDATE_QUERY", (ev) => {
            var {type, data} = ev.detail
            this.query_data[type] = data
            if (["measure", "dimension"].includes(type)) {
                this.query_data.measure = this.query_data.measure.filter(item => item.type == "measure")
                this.query_data.dimension = this.query_data.dimension.filter(item => item.type == "dimension")
            }
            this.genQuery()
        })
        useEffect(() => {
            this.updateSheet()
        }, () => [this.id])
        useEffect(() => {
                this.calculateLimit()
                this.genQuery()
            },
            () => [...Object.keys(this.query_data), this.state.limit])
        useEffect(() => {
                this.calculateLimit()
                this.state.need_save = true
            },
            () => [this.state.selectedType[0]])
        useEffect(() => {
            this.generateChart()
        }, () => [this.state.query])
        useEffect((event) => {
            this.setTableSave()
        }, () => [this.state.models, this.state.limit])
        useEffect(() => {
            const navBar = document.body.querySelector('.o_navbar');
            navBar.style.display = "none";
            return () => {
                navBar.style.display = "flex";
            }
        });
    }

    get yZoneInfo() {
        return {
            condition: this.state.selectedType[1] === "pictorialBar" && this.query_data.measure.length < 2,
            message: "Two Measures are required.",
            className: "dropzone-warning-panel"
        }
    }

    setTableSave() {
        this.state.need_save = (this.state.models.length > 0)
    }

    async updateSheet() {
        await this.updateData();
        this.globalFilters()
    }

    /**
     * Generate the SQL query based on query data.
     */
    calculateLimit() {
        if (['pie', 'doughnut', 'radar', 'funnel'].includes(this.state.selectedType[1]) && (this.state.limit > 30 || !this.state.limit)) {
            this.state.limit = 30
            let message = `Maximum count of data can be shown in a ${this.state.selectedType[1]} chart is 30`
            this.showMessage(message, "warning")
        }
    }

    genQuery() {
        var query_data = this.query_data
        if (!query_data.measure.length) {
            this.state.query = ''
            this.ChartData.generate = false
            return
        }
        var columns = [...query_data.dimension, ...query_data.measure]
        var columnStr = columns.length ? columns.map(item => item.query).join(', ') : ''
        var join = query_data.join.join(' \n')
        var groupColumn = columns.filter(item => !item.query.includes('(')).map(item => item.alias)
        var groupByQuery = query_data.groupBy.length ? query_data.groupBy.map(item => item.column) : []
        var totalGroupBy = groupByQuery.length || columns.filter(item => item.query.includes('(')).length ? [...groupByQuery, ...groupColumn] : []
        totalGroupBy = [...new Set(totalGroupBy)]
        var groupBy = totalGroupBy.length ? '\n GROUP BY ' + totalGroupBy.join(', ') : ''
        var orderBy = query_data.orderBy.length ? '\n ORDER BY ' + query_data.orderBy.map(item => item.query).join(', ') : ''
        var whereData = query_data.where.filter(item => item.active).map(item => item.domain)
        var where = whereData.length ? '\n WHERE ' + whereData.join(' AND ') : ''
        var limit = this.state.limit ? ` LIMIT ${this.state.limit}` : ''
        this.state.query = `SELECT ${columnStr}
                            FROM ${join} ${where} ${groupBy} ${orderBy}${limit}`
        if (this.previewLimit.is_enable) {
            limit = limit && this.state.limit < parseInt(this.previewLimit.limit) ? limit : ` LIMIT ${this.previewLimit.limit}`
            if (this.state.limit > parseInt(this.previewLimit.limit) || !this.state.limit) {
                let message = `The data shown in the preview graph is not accurate.
                    The data is limited to ${this.previewLimit.limit} rows or groups. If
                    you want more data to be shown please change the limit in settings`
                this.showMessage(message, "warning")
            }
        }
        this.state.previewQuery = `SELECT ${columnStr}
                                   FROM ${join} ${where} ${groupBy} ${orderBy}${limit}`
        if (!columns.length) {
            this.ChartData.data = false
            this.ChartData.generate = false
        }
    }

    /**
     * Check weather there is at least one column and one table
     */
    get isGoodQuery() {
        return this.query_data.measure.length && this.query_data.join.length
    }

    /**
     * Execute the generated query to generate the graph
     */
    generateChart() {
        try {
            if (this.isGoodQuery) {
                this.orm.call("dashboard.config", "sql_execute", [this.state.previewQuery]).then((data) => {
                    if (data.length) {
                        let props = {
                            data,
                            name: this.state.name || '',
                            measures: this.query_data.measure.map(item => item.alias),
                            dimension: this.query_data.dimension.map(item => item.alias),
                            dimension_axis: this.query_data.dimension_axis,
                            type: this.state.selectedType[1],
                        }
                        this.ChartData.data = props
                        this.ChartData.generate = true
                    }
                })
            }
        } catch (error) {
            this.ChartData.data = false
            this.ChartData.generate = false
        }
    }

    /**
     * Set the models and fields for the sheet.
     * @param {Array} models - The list of models.
     */
    setModel(models) {
        this.state.models = models
        this.setFields()
        this.setTableSave()
    }

    checkHasLink(model) {
        var hasField = []
        var hasModel = []
        var fields = []
        fields = fields.concat(this.query_data.dimension)
        fields = fields.concat(this.query_data.measure)
        fields = fields.concat(this.query_data.groupBy)
        fields = fields.concat(this.query_data.orderBy)
        fields.forEach((field) => {
            if (field.query.includes(model.table))
                hasField.push(field)
        })
        var joinCheck = this.query_data.joinData.filter(join => join.model != model.model)
        joinCheck.forEach(join => {
            if (join.join.includes(model.table))
                hasModel.push(join)
        })
        return {
            fields: hasField,
            models: hasModel,
            link: !!(hasField.length || hasModel.length)
        }
    }

    /**
     * Set the available fields for the sheet.
     */
    setFields() {
        var fields = []
        for (var model of this.state.models) {
            Object.values(model.fields).forEach(field => {
                if (!this.avoid_fields.includes(field.name) && !this.avoid_field_types.includes(field.type)) {
                    fields.push({
                        model: {
                            id: field.model.id,
                            name: field.model.name,
                            table: field.model.table,
                            relation: field.relation
                        },
                        type: this.measures_field_types.includes(field.type) ? 'measure' : 'dimension',
                        name: field.name,
                        label: `${field.model.name} > ${field.string}`,
                        field_type: field.type,
                        selection: field.selection || false,
                        is_json: field.type == 'char' && field.translate ? true : false
                    })
                }
            })
        }
        this.state.fields = fields
    }

    /**
     * Get the list of measures.
     * @returns {Array} - The list of measures.
     */
    get measures() {
        return this.state.fields.filter(field => field.type == 'measure')
    }

    /**
     * Get a object with
     */
    get getAxisData() {
        const getLimit = (yAxisType) => {
            var xLimit, yLimit
            switch (this.state.selectedType[1].toLowerCase()) {
                case "gauge":
                case "kpi":
                    xLimit = 1;
                    yLimit = 0;
                    break;
                case "heatmap":
                    xLimit = 1;
                    yLimit = 2;
                    break;
                case "map":
                    xLimit = 1;
                    yLimit = 1;
                    break;
                case "pictorialbar":
                    xLimit = 1;
                    yLimit = 2;
                    break;
                case "funnel":
                    xLimit = 1;
                    yLimit = 1;
                    break;
                default:
                    xLimit = 1;
                    yLimit = 5;
            }
            if (yAxisType === "measure") {
                return {xLimit, yLimit}
            } else {
                return {"xLimit": yLimit, "yLimit": xLimit}
            }
        };

        let type = 'both';
        let yType = 'both';

        if (this.query_data.dimension_axis === 'x') {
            if (this.query_data.dimension.length || this.query_data.measure.length) {
                type = 'dimension';
                yType = 'measure';
            }
            const {xLimit, yLimit} = getLimit(yType);
            return {
                x: this.query_data.dimension,
                xType: type,
                y: this.query_data.measure,
                yType,
                xLimit, //1
                yLimit, //5
            };
        }

        if (this.query_data.measure.length) {
            type = 'measure';
            yType = 'dimension';
        }
        const {xLimit, yLimit} = getLimit(yType);
        return {
            x: this.query_data.measure,
            xType: type,
            y: this.query_data.dimension,
            yType,
            xLimit,
            yLimit,
        };
    }

    /**
     * Get the list of dimensions.
     * @returns {Array} - The list of dimensions.
     */
    get dimensions() {
        return this.state.fields.filter(field => field.type == 'dimension')
    }

    /**
     * Save the sheet configuration.
     */
    async onSave() {
        var joinData = [...this.query_data.joinData]
        joinData.forEach((item) => {
            delete item.model?.fields
        })
        if (this.state.selectedType[1] == 'kpi') {
            var kpiEl = this.sheet.el.querySelector(".kpi_sheet")
            const canvas = await html2canvas(kpiEl)
            this.state.image = canvas.toDataURL('image/png');
        } else if (this.state.selectedType[1] == 'table') {
            var el = this.sheet.el.querySelector(".cy_table_sheet")
            const canvas = await html2canvas(el)
            this.state.image = canvas.toDataURL('image/png');
        }
        let vals = {
            image: this.Image,
            id: this.id || false,
            limit: this.state.limit,
            joinData: joinData,
            group_by: this.query_data.groupBy,
            order_by: this.query_data.orderBy,
            dimension: this.query_data.dimension[0],
            measure: this.query_data.measure,
            where: this.query_data.where,
            type: this.state.selectedType,
            dimension_axis: this.query_data.dimension_axis,
            query: this.state.query,
            configs: this.state.configs,
            unlink_list: this.unlinkList,
            options: this.filterOptions,
            kpi: this.state.kpiValue
        }
        if (!this.state.name) {
            this.showMessage('Please provide a name first', 'danger')
        } else {
            vals['name'] = this.state.name.substring(0, 32)
            this.orm.call(this.model, 'update_data', [vals]).then(async (data) => {
                this.id = data.rec_id
                this.saveManually(this.id)
                this.showMessage("Saved", "success")
                this.state.need_save = false
                const {show_position_warning} = data
                if (show_position_warning){
                    this.showMessage(`As the chart shifted from being a KPI to ${this.state.selectedType[1]}, it required removing the previous positions.`, "warning")
                }
                this.isNewSheet = data.is_new_sheet;
                data.sheet_filter.forEach(item => {
                    this.query_data.where.find(where => where.name == item.name).id = item.id
                })
                this.navState.allRecords = await this.orm.search('dashboard.sheet', [])
            })
        }
    }

    async globalFilters() {
        const ids = await this.state.configs.map((config) => config.id);
        const globalFilters = await this.orm.searchRead('dashboard.global.filter', [['dashboard_config_id', 'in', ids]], [])
        const filteredDict = {};
        globalFilters.forEach((filter) => {
            const {dashboard_config_id, id, name, code, type, relation, operator} = filter;

            if (dashboard_config_id) {
                if (!filteredDict[dashboard_config_id[1]]) {
                    filteredDict[dashboard_config_id[1]] = [];
                }
                filteredDict[dashboard_config_id[1]].push({name, id, code, type, relation, operator});
            }
        });
        this.state.globalFilters = filteredDict
    }

    get Image() {
        return this.state.image
    }

    setImage(image) {
        this.state.image = image
    }

    async updateData() {
        if (!this.id) return
        await this.orm.call(this.model, 'get_sheet_data', [this.id]).then(data => {
            this.state.name = data.name
            this.state.limit = data.limit
            this.state.selectedType = data.type
            this.state.configs = data.configs
            data.models.forEach(model => {
                for (var i in model.fields) {
                    model.fields[i].model = model
                }
            })
            this.setModel(data.models)
            this.query_data.join = data.join
            this.query_data.joinData = data.joinData
            this.query_data.dimension = data.dimension
            this.query_data.measure = data.measure
            this.query_data.groupBy = data.groupBy
            this.query_data.orderBy = data.orderBy
            this.query_data.dimension_axis = data.dimension_axis
            this.query_data.where = data.where
            this.filterOptions = data.options
            this.state.kpiValue = data.kpi
        })
    }

    showMessage(message, type) {
        this.notification.add(message, {type})
    }

    onFilterClick() {
        this.dialog.add(FilterDialog, {fields: this.state.fields, confirm: this.addWhere.bind(this)})
    }

    addWhere(domain) {
        if (domain.edit) {
            var item = this.query_data.where.find(item => item.id == domain.id)
            for (const key of Object.keys(domain)) {
                item[key] = domain[key]
            }
        } else {
            this.query_data.where.push(domain)
        }
        this.genQuery()
    }

    updateWhere(where) {
        where.active = !where.active
        this.genQuery()
    }

    onClickSheetType(type) {
        this.state.selectedType = type
        this.generateChart()
    }

    async onDashboardSelect(config) {
        const conf = await this._nameGet(config[0].id)
        this.state.configs.push(conf)
        this.setTableSave()
        this.globalFilters()
    }

    async _nameGet(recordId) {
        const result = await this.orm.read("dashboard.config", [recordId], ["display_name"]);
        return {id: result[0].id, display_name: result[0].display_name};
    }

    dashboardDomain() {
        var ids = this.state.configs.map(item => item.id)
        return [["id", "not in", ids]]
    }

    onRemoveDashboard(config) {
        this.state.configs = this.state.configs.filter(item => item.id !== config.id)
        this.unlinkList.configs.push(config.id)
    }

    get style() {
        return {
            height: `450px;`,
            width: `750px;`,
        }
    }

    onDelete() {
        this.dialog.add(SheetDeleteDialog, {
            id: this.id,
            removeManually: this.removeManually.bind(),
            model: this.model,
            body: `Are you sure you want to delete ${this.state.name}?`,
            onConfirm: () => {
                this.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "Successfully Deleted",
                        'type': 'success',
                        'sticky': false,
                    }
                })
                browser.history.go(-1)
            }
        })
    }

    onOptionClick(option, filter) {
        if (!option) return
        this.filterOptions[filter] = {
            'global_filter_id': filter,
            'field': option.model.table + '.' + option.name,
            'name': option.label
        }
    }

    getGlobalFilters(type, relation) {
        if (relation) {
            return this.state.fields.filter(item => item.field_type === type && item.model.relation === relation)
        }
        return this.state.fields.filter(item => item.field_type === type)
    }

    getDefaultOption(options, filter) {
        var selectedOption = this.getSelectedOption(filter)
        if (selectedOption !== undefined) {
            return options.find(item => item.label === selectedOption.name)
        }
        ;
        const {code} = filter
        const getOptions = () => {
            switch (code) {
                case "start-date":
                case "end-date":
                    return options.find(item => item.name === 'create_date');
                case "company":
                    return options.find(item => item.name === 'company_id');
                case "user":
                    return options.find(item => item.name === 'user_id');
                default:
                    return false;
            }
        }
        var option = getOptions()
        this.onOptionClick(option, filter.id)
        return option
    }

    getSelectedOption(filter) {
        if (this.filterOptions.length == undefined) {
            var value = Object.values(this.filterOptions).find(item => item.global_filter_id === filter.id);
            return value
        }
        return false
    }

    onClickDuplicate() {
        this.orm.call(this.model, 'duplicate_sheet', [this.id]).then(rec_id => {
            if (rec_id) {
                this.action.doAction('reload_context').then(() => {
                    this.saveManually(rec_id)
                })
            }
        })
    }

    setContentEmpty() {
        var axis = [...this.query_data.groupBy, ...this.query_data.orderBy, ...this.query_data.measure, ...this.query_data.dimension]
        axis.forEach(item => {
            if (item.id) {
                this.unlinkList.axis.push(item.id)
            }
        })
        this.state.models.forEach(item => {
            if (item.linked_by?.id) {
                this.unlinkList.tables.push(item.linked_by.id)
            }
        })
        this.query_data.where.forEach(item => {
            if (item.id) {
                this.unlinkList.where.push(item.id)
            }
        })
        this.state.models = []
        this.query_data.join = []
        this.query_data.joinData = []
        this.query_data.measure = []
        this.query_data.dimension = []
        this.query_data.where = []
        this.query_data.groupBy = []
        this.query_data.orderBy = []
        this.state.limit = false
    }

    async onQueryChange(query) {
        try {
            this.setContentEmpty()
            const parser = new SQLQueryParser(query);
            const parsedData = parser.parse();
            const tableAlias = {}
            if (!parsedData.joins) {
                return
            }
            // Joins
            for (var join of parsedData.joins) {
                var alias = join.alias || join.join
                var n_join = join.join
                var split = this.splitJoinOnClause(n_join)
                n_join = n_join.replace(`AS ${alias}`, '')
                tableAlias[alias] = join.model
                if (split) {
                    split.forEach(item => {
                        var [table, field] = item
                        var table_name = tableAlias[table]
                        n_join = n_join.replace(`${table}.${field}`, `${table_name}.${field}`)
                    })
                }
                join.join = n_join
                await this.setModelFromTable(join)
            }
            // Measure and Dimension
            parsedData.columns.forEach(column => {
                var [mode, col] = this.splitStringWithParentheses(column.column)
                var [table, field] = col.split('.')
                field = field.replace(`->>'en_US'`, '').trim()
                var table_name = tableAlias[table] || table
                if (table_name) {
                    var val_to_change = `${table}.${field}`
                    var val_new = `${table_name}.${field}`
                    column.column = column.column.replace(val_to_change, val_new)
                    column.query = column.query.replace(val_to_change, val_new)
                }
                var fieldData = this.state.fields.filter(item => {
                    return item.model.table == table_name && item.name == field
                })
                if (fieldData.length) {
                    this.updateColumns(fieldData, column, fieldData[0].type, mode)
                }
            })
            // Sheet Filters
            parsedData.where.forEach(where => {
                Object.entries(tableAlias).forEach((alias) => {
                    var val_to_change = ` ${alias[0]}.`
                    var val_new = ` ${alias[1]}.`
                    where.domain = where.domain.replaceAll(val_to_change, val_new)
                })
                //            var has_where = this.query_data.where.filter(item => item.query == where.query)
                //            if(!has_where.length){
                this.query_data.where.push(where)
                //            }
            })
            // Group by
            parsedData.groupBy.forEach(groupBy => {
                if (groupBy.column.includes('.')) {
                    var [table, field] = groupBy.column.split('.')
                    var table_name = tableAlias[table]
                    var val_to_change = `${table}.${field}`
                    var val_new = `${table_name}.${field}`
                    groupBy.column = groupBy.column.replace(val_to_change, val_new)
                    groupBy.query = groupBy.query.replace(val_to_change, val_new)
                    var field = this.state.fields.filter(item => {
                        return item.model.table == table_name && item.name == field
                    })
                    if (field.length) {
                        var type = field[0].type
                        this.updateColumns(field, groupBy, 'groupBy')
                    }
                }
            })
            // Order by
            parsedData.orderBy.forEach(orderBy => {
                if (orderBy.column.includes('.')) {
                    var [table, field] = orderBy.column.split('.')
                    var table_name = tableAlias[table]
                    var val_to_change = `${table}.${field}`
                    var val_new = `${table_name}.${field}`
                    orderBy.column = orderBy.column.replace(val_to_change, val_new)
                    orderBy.query = orderBy.query.replace(val_to_change, val_new)
                    var field = this.state.fields.filter(item => {
                        return item.model.table == table_name && item.name == field
                    })
                    if (field.length) {
                        var type = field[0].type
                        this.updateColumns(field, orderBy, 'orderBy')
                    }
                }
            })
            // Limit
            this.state.limit = parsedData.limit || false
            this.setTableSave()
        } catch {
            this.setContentEmpty()
            this.showMessage('This query is not compatible', "danger")
        }
    }

    splitStringWithParentheses(input) {
        const match = input.match(/([^()]+)(?:\(([^)]+)\))?/);
        if (match) {
            const [, outsideParentheses, insideParentheses] = match;
            const firstPart = outsideParentheses.trim();
            const secondPart = insideParentheses ? insideParentheses.trim() : false;
            if (!secondPart) {
                return [false, firstPart]
            }
            return [firstPart, secondPart];
        }
        return [false, input.trim()];
    }

    splitJoinOnClause(joinClause) {
        const regex = /JOIN\s+([\w_]+)\s+\bAS\b\s+([\w_]+)?\s+ON\s+([^]+?)(?=(?:JOIN|$))/ig;
        const matches = [...joinClause.matchAll(regex)];
        if (matches.length > 0) {
            const [, table, alias, onCondition] = matches[0];
            const [leftTable, leftField, rightTable, rightField] = onCondition.split(/[.=]/).map((part) => part.trim());
            return [
                [leftTable || table, leftField],
                [rightTable || (alias || table), rightField],
            ];
        }
        return null;
    }

    updateColumns(field, column, type, mode) {
        var cur_field = field[0]
        var val = {
            query: column.query,
            alias: column.alias,
            column: column.column,
            value: cur_field.label,
            id: false,
            type
        }
        if (mode) {
            val.AGG = mode
        }
        if (!this.query_data[type].filter(item => item.query == val.query).length) {
            this.query_data[type].push(val)
        }
    }

    async setModelFromTable(join) {
        await this.orm.call('ir.model', 'get_model_from_table', [join.model]).then(model => {
            if (!this.state.models.map(mdl => mdl.id).includes(model.id)) {
                join.model = model.model
                join.name = model.name
                model.linked_by = join
                model.linked_by.string = join.linked ? this.getLinkString(join, model) : false
                Object.values(model.fields).forEach(field => {
                    field.model = model
                })
                this.state.models.push(model)
                this.setFields()
            }
        })
    }

    onUpdate(data) {
        this.state.kpiValue = data
        return this.state.kpiValue
    }

    onClickDashboardPage(dashboard) {
        const selectedDashboard = this.sheet.el.querySelectorAll(dashboard)[0]
        this.sheet.el.querySelectorAll('.dashboard-note').forEach(div => {
            if (div !== selectedDashboard) {
                div.classList.remove('show');
            }
        });
        selectedDashboard.classList.add('show');
    }

    getLinkString(join, model) {
        if (!join.join) return false
        var link = join.join.replace(/join/ig, ' Linked by ')
        return link
    }

    onClickDeleteFilter(index, filterId) {
        this.query_data.where = this.query_data.where.filter((item, idx) => idx !== index);
        this.updateWhere(this.query_data.where)
        if (filterId) {
            this.orm.unlink("dashboard.sheet.filter", [filterId]);
        }
    }

    onClickEditFilter(filter) {
        let filterDomain = [];
        let idCounter = 0;
        filter.domain.split(' OR ').forEach(element => {
            let splitBySpace = element.trim().split(' ');
            let field = splitBySpace[0].split('.')[1];
            let table = splitBySpace[0].split('.')[0];
            let operator = splitBySpace[1];
            let rhs = splitBySpace.slice(2).join(' ');
            filterDomain.push({id: idCounter++, field, table, operator, rhs});
        });
        this.dialog.add(FilterDialog, {
            filterData: filter,
            filterDomain,
            edit: true,
            fields: this.state.fields,
            confirm: this.addWhere.bind(this)
        })
    }

    goBack() {
        browser.history.go(-1)
        if (this.isNewSheet) {
            this.env.bus.trigger("PN:RLD")
        }
    }

    changeRecord(event) {
        if (!this.id) {
            return
        }
        var index = this.navState.allRecords.findIndex(item => item == this.id)
        index = event === "fwd" ? index + 1 : index - 1
        if (index > this.navState.allRecords.length - 1) {
            index = 0
        } else if (index < 0) {
            index = this.navState.allRecords.length - 1
        }
        this.id = this.navState.allRecords[index]
        this.saveManually(this.id)
        this.navState.recordValue = index + 1
        this.updateSheet()
    }

    get axis() {
        var x, y, group;
        switch (this.state.selectedType[1].toLowerCase()) {
            case "gauge":
            case "kpi":
                x = false;
                y = true;
                group = false;
                break;
            case "map":
                x = true;
                y = true;
                group = false;
                break;
            default:
                x = true;
                y = true;
                group = true;
        }
        return {
            x,
            y,
            group
        };
    }

    onClickDiscard() {
        this.action.doAction("soft_reload")
    }

    onClickNew() {
        this.removeManually()
        return this.action.doAction({
            target: "current",
            tag: "cy_analytic_sheet",
            type: "ir.actions.client",
        })
    }

    static props = {...standardActionServiceProps}
}

// Define the template for the CylloSheet component
CylloSheet.template = "CylloSheet"
CylloSheet.components = {
    FieldList,
    ModelViewer,
    DropZone,
    SQLEditor,
    GraphTile,
    Many2XAutocomplete,
    FieldAutoComplete,
    FieldAutoCompleteGlobal,
    KpiSheet,
    Table,
    Number
}
registry.category("actions").add("cy_analytic_sheet", CylloSheet);
