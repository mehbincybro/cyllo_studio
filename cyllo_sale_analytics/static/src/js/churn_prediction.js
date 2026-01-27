/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, useRef, onMounted } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";
import { GraphTile } from "@cyllo_analytics/js/presentation/components/graph_tile";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { BlockUI, unblockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
import { FilterDropdown } from "@cyllo_analytics/js/filterDropdown"

const PERIODS = {
    quarter: 'Quarter',
    year: 'Year',
    month: 'Month',
    six_months: 'Half Year',
    current_date: 'current_date',
    financial_year: 'financial_year',
}

export class ChurnPredictionDashboard extends Component {
    setup(){
        super.setup(...arguments);
        this.orm = useService('orm')
        this.notification = useService("notification");
        this.root = useRef("root")
        this.savedContext = useSaveContext()
        this.period = useRef("period")
        this.periodType = useRef("period_type")
        this.input = useRef("input")
        this.actionService = useService("action")
        this.state = useState({
            churnData : [],
            numberOfPeriods : 4,
            period: 'Quarter',
            periodType: 'current_date',
            cust: false,
            generate: false,
            customer: [],
            churnChart: false,
            offset: 0,
            arr: [],
            data: [],
            heading: [],
            count: 0,
            min: 0,
            searchText: false,
            predictData: true,
        });
        onWillStart(async () => {
            var period, periodType, numberOfPeriods
            if(!this.savedContext?.state){
                ({ period, periodType, numberOfPeriods } = this.state)
            }else {
                ({ period, periodType, numberOfPeriods } = this.savedContext.state)
            }
            this.state.period = period
            this.state.periodType  = periodType;
            this.state.numberOfPeriods  = numberOfPeriods;
            await this.renderChurnData();
        })
    }

    async onChangePeriod(){
        if (this.input.el.value < 4) {
            this.input.el.value = 4
            this.state.numberOfPeriods = 4
            this.notification.add(_t("Number of periods must be at least 4"), {
                type: "warning",
            });
            this.renderChurnData()
        } else {
            this.state.period = PERIODS[this.period.el.value];
            this.state.periodType = PERIODS[this.periodType.el.value];
            this.state.numberOfPeriods = this.input.el.value
            this.renderChurnData()
            this.savedContext.saveManually(this.state, "state")
        }
    }

    async renderChurnData(){
        this.state.churnData = await this.orm.call('res.partner','get_date_range', [this.state.period, this.state.periodType, this.state.numberOfPeriods])
        this.state.predictData = this.state.churnData.predict;
        if (this.state.predictData){
            this.state.min = this.state.churnData.cust_wise_details.length > 6 ? 6 : this.state.churnData.cust_wise_details.length;
            this.state.count = this.state.churnData.cust_wise_details.length
            let props = {
                data: [{ value: this.state.churnData.churn_perc, name: 'Churn', itemStyle: { color: '#FF5733' } },
                       { value: this.state.churnData.not_churn_perc, name: 'Not Churn', itemStyle: { color: '#FF5763' } }],
                measures: ['value'],
                dimension: 'name',
                dimension_axis: 'y',
                type: 'pie',
            }
            this.state.churnChart = props
            this.state.generate = true
            this.onClickCustomer(this.state.churnData.cust_wise_details[0]);
            this.setArr()
        }
    }

    onClickCustomer(cust){
        let props = {
            data: [{ value: cust.prob_yes, name: 'Churn' },
                   { value: cust.prob_no, name: 'Not Churn' }],
            measures: ['value'],
            dimension: 'name',
            dimension_axis: 'y',
            type: 'pie',
        }
        this.state.cust = props
        this.state.generate = true
        this.state.customer = cust.custName
    }

    async exportPDF(){
        var head = this.root.el?.querySelector('.churn_prediction-graph_img')
        if(head){
            var canvas = await html2canvas(head)
            head = canvas.toDataURL('image/png');
        }
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: 'cyllo_sale_analytics.report_churn_prediction',
            report_file: "cyllo_sale_analytics.report_churn_prediction",
            data: {
                head,
                'churnData': this.state.churnData,
                'period': this.state.period,
                'numberOfPeriods': this.state.numberOfPeriods
            }
        });
    }
    exportXLSX(){
        BlockUI;
	    download({
	           url: '/smartd_xlsx_reports',
	           data: {
                 'model': 'res.partner',
                 'data': JSON.stringify(this.state),
                 'output_format': 'xlsx',
                 'report_name': 'Churn Prediction',
               },
	           complete: () => unblockUI,
	           error: (error) => this.call('crash_manager', 'rpc_error', error),
	           });
    }

    onInputCustomer(ev) {
        this.state.searchText = ev.toLowerCase();
        this.setArr()
    }

    get chartStyle() {
        return {
            height:`320px;`,
            width:`320px;`,
        }
    }
    onClickCustomerDetails(cust){
        return this.actionService.doAction({
            target: "current",
            tag: "cyllo_sale_analytics.customer_details",
            type: "ir.actions.client",
            context: {
                cust: cust,
                dateRange: this.state.churnData.date_range,
                period: this.state.period
            }
        })
    }
    get hasNext(){
        return !(this.state.offset + this.state.min >= this.state.count)
    }
    get hasPrev(){
        return this.state.offset !== 0
    }
    onClick(num){
        this.state.offset += this.state.min * num
        this.setArr()
    }
    setArr(){
        var min = this.state.min - 1
        var next_min = this.state.count - (this.state.offset + 1)
        next_min = next_min > min ? min : next_min
        var start = this.state.offset
        var end = this.state.offset + next_min
        this.state.arr = this.createArray(start, end)
    }
    createArray(start, end) {
        const result = [];
        if(this.state.searchText){
            const filteredData = this.state.churnData.cust_wise_details.filter(item => {
                const custName = item.custName.toLowerCase();
                return custName.includes(this.state.searchText);
            })
            if (filteredData){
                this.state.count = filteredData.length
                for (let i = start; i <= end; i++) {
                    result.push(filteredData[i]);
                }
            }
        }
        else{
            for (let i = start; i <= end; i++) {
                result.push(this.state.churnData.cust_wise_details[i]);
            }
        }
        return result;
    }
    onClickFrequency(cust){
        const lastPeriodDate = this.state.churnData.date_range[this.state.churnData.date_range.length-1]
        const domain = [['date_order', '>=', this.state.churnData.date_range[0][0]], ['date_order', '<=', this.state.churnData.date_range[this.state.churnData.date_range.length-1][1]], ['partner_id', '=', cust.custId]];
        if(cust.total_sales != 0){
            this.actionService.doAction({
                name: "Sale orders of " +  cust.custName + " from " +  this.state.churnData.date_range[0][0] + " to "
                    + this.state.churnData.date_range[this.state.churnData.date_range.length-1][1],
                res_model: "sale.order",
                views: [[false, "tree"], [false, "form"]],
                type: "ir.actions.act_window",
                view_mode: "tree",
                domain: domain,
                target: "current",
            });
        }
    }
}

ChurnPredictionDashboard.template = "ChurnPredictionDashboard";
ChurnPredictionDashboard.components = { GraphTile, FilterDropdown }
registry.category("actions").add("churn_prediction", ChurnPredictionDashboard);