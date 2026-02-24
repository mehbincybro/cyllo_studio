/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import { session } from "@web/session";
import {ModelViewer} from "./model_viewer";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {DragItem, DropZone} from "./drag_n_drop"
import {GraphTile} from "@cyllo_analytics/js/presentation/components/graph_tile";
import {SQLEditor} from "./editor/SQLEditor";
import {browser} from "@web/core/browser/browser";
import {useSaveContext} from "@cyllo_analytics/js/useSaveContext";
import {SQLQueryParser} from "./query/query_manager"
import {FieldAutoComplete} from "@cyllo_analytics/js/sheet_filter/field_auto_complete"
import {FieldAutoCompleteGlobal} from "@cyllo_analytics/js/sheet_filter/field_auto_complete_global"
import {KpiSheet} from "@cyllo_analytics/js/KpiSheet";
import {Table} from "@cyllo_analytics/js/table/table";
import {Number} from "@cyllo_analytics/js/fields/number";
import {DeleteDialog} from "./delete_dialog_box";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";
import {_t} from "@web/core/l10n/translation";
import {SheetFilterDomain} from "./sheet_filter/sheetFilterDomain";
const {Component, useState, onWillStart, useEffect, onWillDestroy, useRef} = owl


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
            search: '',
        })
        useEffect(() => {
            this.state.data = this.props.data
            this.state.search = ""
        }, () => [this.props.data])
        useEffect(() => {
            if (this.state.search) {
                this.state.data = this.props.data.filter(item => {
                    const search = this.state.search.toLowerCase()
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
        this.hasMonetary = false //multi
        this.isNewSheet = false;
        onWillDestroy(removeManually)
        this.sheet = useRef('sheet')
        this.saveManually = saveManually
        this.removeManually = removeManually
        this.model = 'dashboard.sheet'
        this.orm = useService("orm")
        this.company = useService("company")
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
            false_linking: false,
            sheetTypes: [],
            chart: [],
            selectedType: [1, 'line'],
            configs: [],
            globalFilters: [],
            image: "",
            option: {},
            kpiValue: {},
            saveClicked: false,
            id: id,
            currency: false,
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
            this.navState.allRecords = await this.orm.search('dashboard.sheet', [])
            if (this.id) {
                const value = this.navState.allRecords.findIndex(item => item == this.id)
                this.navState.recordValue = value + 1
            }
            if (this.props.action.context?.dashboard_id) {
                const context = this.props.action.context
                this.state.configs.push({id: context.dashboard_id, display_name: context.display_name})
            }
            const res = await this.orm.call(this.model, 'get_config_data', [])
            this.state.sheetTypes = res.sheet_types
            this.previewLimit = {
                is_enable: res.is_enable,
                limit: res.limit
            }
            //fetch current company currency
            const companyData = await this.orm.read("res.company", [this.company.currentCompany?.id || 1], ["currency_id"])
            const currency = await this.orm.read("res.currency", [companyData[0].currency_id[0]], ["id", "display_name"])
            this.state.currency = currency[0]
        })
        this.env.bus.addEventListener("CY:UPDATE_UNLINKS", (ev) => {
            var {type, id} = ev.detail
            this.unlinkList[type].push(id)
        })
        this.env.bus.addEventListener("CY:UPDATE_QUERY", (ev) => {
            this.state.false_linking = false
            var {type, data} = ev.detail

            if (type === 'groupBy') {
                // Detect which date groupBy items were just removed
                const oldGroupBy = this.query_data.groupBy || []
                const removedDateItems = oldGroupBy.filter(
                    g => g.source_column && !data.some(n => n.source_column === g.source_column)
                )
                this.query_data[type] = data
                // Revert removed date dimensions back to their plain column query
                if (removedDateItems.length > 0) {
                    this.query_data.dimension = this.query_data.dimension.map(dim => {
                        const removed = removedDateItems.find(r => r.source_column === dim.column)
                        if (removed) {
                            const baseAlias = dim.column.replace('.', '_')
                            const cleanLabel = (dim.original_value || dim.value)
                                .replace(/^(Day|Month|Year)\s+of\s+/i, '').trim()
                            return {
                                ...dim,
                                alias: baseAlias,
                                query: `${dim.column} AS ${baseAlias}`,
                                value: cleanLabel,
                                original_value: cleanLabel,
                                DATE_GROUP: null,
                            }
                        }
                        return dim
                    })
                    // onWillUpdateProps always-sync will pick this up; CY:SYNC_CHILDREN as backup
                    this.env.bus.trigger("CY:SYNC_CHILDREN", {
                        targetType: 'dimension',
                        children: this.query_data.dimension,
                    })
                }
            } else {
                this.query_data[type] = data
                if (["measure", "dimension"].includes(type)) {
                    this.query_data.measure = this.query_data.measure.filter(item => item.type == "measure")
                    this.query_data.dimension = this.query_data.dimension.filter(item => item.type == "dimension")
                    // When dimension is removed, clean up any date groupBy tags for it
                    if (type === 'dimension') {
                        const activeColumns = new Set(this.query_data.dimension.map(d => d.column))
                        this.query_data.groupBy = this.query_data.groupBy.filter(
                            item => {
                                if (item.source_column && !activeColumns.has(item.source_column)) {
                                    if (item.id) {
                                        this.unlinkList.axis.push(item.id)
                                    }
                                    return false
                                }
                                return true
                            }
                        )
                    }
                }
            }
            this.genQuery()
        })
        // Add / replace a date group-by tag in the Group By zone
        this.env.bus.addEventListener("CY:ADD_DATE_GROUPBY", (ev) => {
            const { groupByItem } = ev.detail
            let existingId = null
            // Remove any existing date_group entry for the same source column
            this.query_data.groupBy = this.query_data.groupBy.filter(
                item => {
                    const hasSameSource = item.source_column === groupByItem.source_column;
                    // Fallback for duplicates or older records missing source_column
                    const hasSameColumnSubstring = !item.source_column && item.column && typeof item.column === 'string' && item.column.includes(groupByItem.source_column) && /^TO_CHAR/i.test(item.column);

                    if (hasSameSource || hasSameColumnSubstring) {
                        if (item.id) {
                            if (!existingId) {
                                existingId = item.id; // Reuse the first matched ID to avoid creating a new DB record
                            } else {
                                this.unlinkList.axis.push(item.id); // If there are multiple, unlink the rest to clean up the DB
                            }
                        }
                        return false;
                    }
                    return true;
                }
            )
            if (existingId) {
                groupByItem.id = existingId;
            }
            this.query_data.groupBy.push(groupByItem)
            this.genQuery()
        })
        useEffect(() => {
            (async () => await this.updateSheet())()
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
        this.genQuery()
        await this.generateChart()
        await this.globalFilters()
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
        this.hasMonetary = false
        if (!query_data.measure.length) {
            this.state.query = ''
            this.ChartData.generate = false
            return
        }
        query_data.measure.forEach(measure => {
            if (measure.monetaryInBase) {
                this.hasMonetary = true
                // modify the query here for changing currency
                const substring = measure.query.substring(measure.query.indexOf('ROUND'), measure.query.lastIndexOf('2)') + 2)
                const replaceString = measure.monetaryInBase.replaceAll('{selectedCurrency}', `${this.state.currency?.id}`)
                measure.query = measure.query.replaceAll(substring, replaceString)
            }
        });
        var columns = [...query_data.dimension, ...query_data.measure]
        // Defensive: if a dimension still has a TO_CHAR query but its Group By tag was removed,
        // revert it to the plain column reference for this query (source of truth: query_data.groupBy)
        const activeGroupCols = new Set(
            query_data.groupBy.filter(g => g.source_column).map(g => g.source_column)
        )
        columns = columns.map(col => {
            if (col.type === 'dimension' && /^TO_CHAR\s*\(/i.test(col.query) &&
                !activeGroupCols.has(col.column)) {
                // Keep the stored alias so the chart data lookup still matches its key
                return { ...col, query: `${col.column} AS ${col.alias}` }
            }
            return col
        })
        var tableNames = columns.map(col => col.column.split('.')[0]);
        var uniqueTableNames = new Set(tableNames);
        if (this.state.models.length > uniqueTableNames.size) {
            this.state.false_linking = true
        } else {
            this.state.false_linking = false
        }
        var join = query_data.join.join(' \n')
        // ── GROUP BY construction ─────────────────────────────────────────────
        // Only dimension-type items belong in GROUP BY.
        // Measures (including monetary ROUND) must never appear there.
        const dateGroupedCols = new Set(
            query_data.groupBy.filter(g => g.source_column).map(g => g.source_column)
        )
        var groupColumn = columns
            .filter(item => item.type === 'dimension')            // only dimensions
            .filter(item => !dateGroupedCols.has(item.column))    // skip date-grouped ones
            .map(item => item.alias)
        var groupByQuery = query_data.groupBy.length ? query_data.groupBy.map(item => item.column) : []
        var hasAggregates = columns.some(item => /(\bSUM\b|\bAVG\b|\bCOUNT\b|\bMIN\b|\bMAX\b)/i.test(item.query))
        var totalGroupBy = groupByQuery.length || hasAggregates
            ? [...groupByQuery, ...groupColumn] : []
        totalGroupBy = [...new Set(totalGroupBy)]
        // When GROUP BY is active, auto-wrap non-aggregate measure queries in SUM()
        // so PostgreSQL doesn't error with "column must appear in GROUP BY or aggregate"
        if (totalGroupBy.length > 0) {
            columns = columns.map(item => {
                if (item.type === 'measure' && !/(\bSUM\b|\bAVG\b|\bCOUNT\b|\bMIN\b|\bMAX\b)/i.test(item.query)) {
                    const alias = item.alias
                    // monetaryInBase retains '{selectedCurrency}' placeholder — resolve it
                    const rawExpr = item.monetaryInBase
                        ? item.monetaryInBase.trim().replaceAll('{selectedCurrency}', `${this.state.currency?.id}`)
                        : item.column
                    return { ...item, query: `SUM(${rawExpr}) AS ${alias}` }
                }
                return item
            })
        }
        var columnStr = columns.length ? columns.map(item => item.query).join(', ') : ''
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
                this.orm.call("dashboard.config", "sql_execute", [
                    this.state.previewQuery
                ]).then((data) => {
                    this.ChartData.data = {
                        data,
                        name: this.state.name || '',
                        measures: this.query_data.measure.map(item => item.alias),
                        dimension: this.query_data.dimension.map(item => item.alias),
                        dimension_axis: this.query_data.dimension_axis,
                        type: this.state.selectedType[1],
                    }
                    this.ChartData.generate = true
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

    /**
     * Set the currency for monetary measures in sheet.
     * @param {Array} currency - id and display_name of currency.
     */
    setCurrency(currency){
        this.state.currency = currency
        this.genQuery()
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
            let xLimit, yLimit;
            switch (this.state.selectedType[1].toLowerCase()) {
                case "gauge":
                    xLimit = 0;
                    yLimit = 1;
                    break;
                case "kpi":
                    xLimit = 0;
                    yLimit = 1;
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
                return { xLimit, yLimit };
            } else {
                return { xLimit: yLimit, yLimit: xLimit };
            }
        };

        if (this.state.selectedType[1].toLowerCase() === "kpi") {
            // Force clear the X axis if anything is there
            if (this.query_data.dimension?.length) {
                this.query_data.dimension = [];
            }

            // This object is the return value
            return {
                x: [],
                xType: "dimension",
                y: this.query_data.measure,
                yType: "measure",
                xLimit: 0,
                yLimit: 1,
            };
        }
        if (this.state.selectedType[1].toLowerCase() === "gauge") {
            // Force clear dimensions
            if (this.query_data.dimension?.length) {
                this.query_data.dimension = [];
            }

            return {
                x: [],
                xType: "dimension",
                y: this.query_data.measure,
                yType: "measure",
                xLimit: 0,
                yLimit: 1,
            };
        }

        // Normal flow for other chart types
        let type = "both";
        let yType = "both";

        if (this.query_data.dimension_axis === "x") {
            if (this.query_data.dimension.length || this.query_data.measure.length) {
                type = "dimension";
                yType = "measure";
            }
            const { xLimit, yLimit } = getLimit(yType);
            return {
                x: this.query_data.dimension,
                xType: type,
                y: this.query_data.measure,
                yType,
                xLimit,
                yLimit,
            };
        }

        if (this.query_data.measure.length) {
            type = "measure";
            yType = "dimension";
        }
        const { xLimit, yLimit } = getLimit(yType);
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
        if (this.state.saveClicked) return
        this.state.saveClicked = true
        var joinData = [...this.query_data.joinData]
        joinData.forEach((item) => {
            delete item.model?.fields
        })
        if (this.state.selectedType[1] == 'kpi') {
            var kpiEl = this.sheet.el.querySelector(".kpi-sheet-parent")
            const canvas = kpiEl ? await html2canvas(kpiEl) : false
            if (canvas) {
                this.state.image = canvas.toDataURL('image/png');
            }
        } else if (this.state.selectedType[1] == 'table') {
            var el = this.sheet.el.querySelector(".cy_table_sheet")
            const canvas = el ? await html2canvas(el) : false
            if (canvas) {
                this.state.image = canvas.toDataURL('image/png');
            }
        }
        const isInteger = value => typeof value === 'number' && isFinite(value, "") && Math.floor(value) === value;

        let vals = {
            image: this.Image,
            id: this.id || false,
            limit: this.state.limit,
            joinData: joinData,
            group_by: this.query_data.groupBy,
            order_by: this.query_data.orderBy,
            dimension: this.query_data.dimension[0],
            measure: this.query_data.measure,
            where: this.query_data.where.map(filter => {
                return {
                    ...filter,
                    id: isInteger(filter.id) ? filter.id : false
                }
            }),
            type: this.state.selectedType,
            dimension_axis: this.query_data.dimension_axis,
            query: this.state.query,
            configs: this.state.configs,
            unlink_list: this.unlinkList,
            options: this.filterOptions,
            kpi: this.state.kpiValue,
            currency: this.state.currency.id,
        }
        if (!this.state.name) {
            this.showMessage('Please provide a name first', 'danger')
        } else {
            try {
                vals['name'] = this.state.name.substring(0, 32)
                const data = await this.orm.call(this.model, 'update_data', [vals])
                this.id = data.rec_id
                this.state.id = data.rec_id
                this.saveManually(this.id)
                this.showMessage("Saved", "success")
                this.state.need_save = false
                const { show_position_warning } = data
                if (show_position_warning) {
                    this.showMessage(`As the chart shifted from being a KPI to ${this.state.selectedType[1]}, it required removing the previous positions.`, "warning")
                }
                this.isNewSheet = data.is_new_sheet;
                data.sheet_filter.forEach(item => {
                    this.query_data.where.find(where => where.name === item.name).id = item.id
                })
                this.navState.allRecords = await this.orm.search('dashboard.sheet', [])
            }
            catch {
                this.showMessage(`There was an error while saving the record`, "warning")
                this.state.saveClicked = false
            }
        }
        this.state.saveClicked = false
    }

    async globalFilters() {
        const ids = this.state.configs.map((config) => config.id);
        const globalFilters = await this.orm.searchRead('dashboard.global.filter', [['dashboard_config_id', 'in', ids]], [])
        const filteredDict = {};
        globalFilters.forEach((filter) => {
            const { dashboard_config_id, id, name, code, type, relation, operator } = filter;

            if (dashboard_config_id) {
                if (!filteredDict[dashboard_config_id[1]]) {
                    filteredDict[dashboard_config_id[1]] = [];
                }
                filteredDict[dashboard_config_id[1]].push({ name, id, code, type, relation, operator });
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
        const data = await this.orm.call(this.model, 'get_sheet_data', [this.state.id])
        if (data.has_error.error) {
            const model = data.has_error.value.length > 1 ? "models" : "model"
            this.notification.add(_t(`The sheet cannot display the graph because it is missing some information. It cannot access the ${model}: ${data.has_error.value.join(", ")}.`), { type: "warning" });
        }
        this.state.name = data.name
        this.state.currency = data.currency[0]
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
        // Restore field_type and date grouping state so options and tags persist
        this.query_data.dimension = data.dimension.map(dim => {
            if (!dim.field_type && dim.column) {
                const [tableName, fieldName] = dim.column.split('.')
                for (const model of data.models) {
                    if (model.table === tableName && model.fields && model.fields[fieldName]) {
                        dim.field_type = model.fields[fieldName].type
                        break
                    }
                }
            }
            // If there's a matching date groupBy, restore the markers
            const dateGroup = data.groupBy.find(g => g.source_column === dim.column && g.date_group)
            if (dateGroup) {
                dim.DATE_GROUP = dateGroup.date_group
                dim.original_value = dim.value
            }
            return dim
        })
        this.query_data.measure = data.measure
        this.query_data.groupBy = data.groupBy
        this.query_data.orderBy = data.orderBy
        this.query_data.dimension_axis = data.dimension_axis
        this.query_data.where = data.where
        this.filterOptions = data.options
        this.state.kpiValue = data.kpi
    }

    showMessage(message, type) {
        this.notification.add(message, { type })
    }

    onFilterClick() {
        const where = {
            name: "",
            domain: "",
            domain_py_expression: [],
            active: true,
        }
        this.dialog.add(SheetFilterDomain, {
            confirm: this.addWhere.bind(this),
            models: this.state.models,
            where,
            isEdit: false
        })
    }

    addWhere(domain) {
        if (domain.isEdit) {
            this.query_data.where = [
                ...this.query_data.where.filter(item => item.id !== domain.id),
                domain
            ]
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
        // set the new type
        this.state.selectedType = type;

        // if KPI is selected -> backup and clear X-axis related fields (temporary removal)
        if (type && type[1] && String(type[1]).toLowerCase() === 'kpi') {
            // create backup object so we can restore when leaving KPI
            this._backup_query_data = {
                dimension: Array.isArray(this.query_data.dimension) ? [...this.query_data.dimension] : [],
                groupBy: Array.isArray(this.query_data.groupBy) ? [...this.query_data.groupBy] : [],
                orderBy: Array.isArray(this.query_data.orderBy) ? [...this.query_data.orderBy] : [],
                dimension_axis: this.query_data.dimension_axis
            };
            // clear X axis related arrays so KPI has no X-axis
            this.query_data.dimension = [];
            this.query_data.groupBy = [];
            this.query_data.orderBy = [];
            // ensure the axis is set so UI expects measure on Y (helps acceptance)
            this.query_data.dimension_axis = 'y';
        } else {
            // if we have a backup and we are switching away from KPI, restore it
            if (this._backup_query_data) {
                this.query_data.dimension = Array.isArray(this._backup_query_data.dimension) ? [...this._backup_query_data.dimension] : [];
                this.query_data.groupBy = Array.isArray(this._backup_query_data.groupBy) ? [...this._backup_query_data.groupBy] : [];
                this.query_data.orderBy = Array.isArray(this._backup_query_data.orderBy) ? [...this._backup_query_data.orderBy] : [];
                this.query_data.dimension_axis = this._backup_query_data.dimension_axis || 'x';
                // clear backup
                this._backup_query_data = null;
            }
        }

        // regenerate chart preview
        this.generateChart();
    }

    async onDashboardSelect(config) {
        const conf = await this._nameGet(config[0].id)
        this.state.configs.push(conf)
        this.setTableSave()
        this.globalFilters()
    }

    async _nameGet(recordId) {
        const result = await this.orm.read("dashboard.config", [recordId], ["display_name"]);
        return { id: result[0].id, display_name: result[0].display_name };
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
        const { code } = filter
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
                this.query_data.where.push(where)
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
        const isInteger = typeof filterId === 'number' && isFinite(filterId) && Math.floor(filterId) === filterId;
        if (filterId && isInteger) {
            this.orm.unlink("dashboard.sheet.filter", [filterId]);
        }
    }

    onClickEditFilter(where) {
        this.dialog.add(SheetFilterDomain, {
            where,
            isEdit: true,
            confirm: this.addWhere.bind(this),
            models: this.state.models
        })
    }

    goBack() {
        browser.history.go(-1)
        if (this.isNewSheet) {
            this.env.bus.trigger("PN:RLD")
        }
    }

    async changeRecord(event) {
        if (!this.id) {
            return
        }
        var index = this.navState.allRecords.findIndex(item => item === this.id)
        index = event === "fwd" ? index + 1 : index - 1
        if (index > this.navState.allRecords.length - 1) {
            index = 0
        } else if (index < 0) {
            index = this.navState.allRecords.length - 1
        }
        this.id = this.navState.allRecords[index]
        this.state.id = this.navState.allRecords[index]
        this.saveManually(this.id)
        this.navState.recordValue = index + 1
    }

    get axis() {
        let x, y, group;
        switch (this.state.selectedType[1].toLowerCase()) {
            case "gauge":
            case "kpi":
                const dimensionAxis = this.query_data.dimension_axis
                x = dimensionAxis === 'y';
                y = !x;
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