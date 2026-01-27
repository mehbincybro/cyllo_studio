/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, useState, onWillStart, onMounted, onWillDestroy, useRef } = owl
import { browser } from "@web/core/browser/browser";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";

export class CustomerChurnDetails extends Component {
    setup(){
        this.rootRef = useRef("root")
        this.actionService = useService("action");
        this.savedContext = useSaveContext()
        this.state = useState({
            custDetails: [],
            dateRange: [],
            period: [],
            chartData: [],
            saleOrders: {}
        });
        this.orm = useService('orm')
        onWillStart(async () => {
            var cust, dateRange, period
            if(this.props.action.context.cust){
                ({ cust, dateRange, period } = this.props.action.context)
                this.savedContext.saveManually(this.props.action.context, "context")
            }else {
                ({ cust, dateRange, period } = this.savedContext.context)
            }
            this.state.custDetails = cust
            this.state.dateRange  = dateRange;
            this.state.period  = period;
        })
        onMounted(async () => {
            await this.renderChart()
            await this.getSale()
        })
    }

    renderChart(){
        const frequencyValues = {};
        const monetaryValues = {};
        for (const key in this.state.custDetails) {
            const f_regex = /^frequency_(\d+)$/;
            const m_regex = /^monetary_(\d+)$/;
            const freq_match = key.match(f_regex);
            const mon_match = key.match(m_regex);
            if (freq_match) {
                const i = freq_match[1];
                frequencyValues[`${this.state.period}-${i}`] = this.state.custDetails[key];
            }
            if (mon_match) {
                const i = mon_match[1];
                monetaryValues[`${this.state.period}-${i}`] = this.state.custDetails[key];
            }
        }
        if(this.state.custDetails.total_sales){
            const freqChart = echarts.init(this.rootRef.el.querySelector('#freq_chart'), null, {
                width: 800,
                height: 530
            })
            const monChart = echarts.init(this.rootRef.el.querySelector('#mon_chart'), null, {
                width: 800,
                height: 530
            })
            this.renderDetails(freqChart, frequencyValues, 'Total Sale Orders')
            this.renderDetails(monChart, monetaryValues, 'Total Sale Amount')
        }
    }

    getSale() {
        let dateRange = this.state.dateRange;
        if (dateRange){
            dateRange.forEach( async(date, index) => {
                const domain = [['date_order', '>=', date[0]], ['date_order', '<=', date[1]], ['partner_id', '=', this.state.custDetails.custId]];
                this.state.saleOrders[`${index + 1}`] = await this.orm.searchRead("sale.order", domain);
            });
        }
    }
    goBack() {
        browser.history.go(-1)
    }
    onClickSaleOrder(orderId){
        this.actionService.doAction({
            name: "Sale",
            res_model: "sale.order",
            res_id: orderId,
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
            target: "current",
        });
    }

    renderDetails(chart, vals, name){
        const data = Object.keys(vals).map((key) => ({
        name: key,
        value: vals[key],
        }));
        const option = {
            title: {
              text: name,
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                }
            },
            xAxis: {
              type: 'category',
              data: data.map((item) => item.name),
            },
            yAxis: {
              type: 'value',
              axisLabel: {
                    formatter: '{value}'
                },
                axisPointer: {
                    snap: true
                }
            },
            series: [
              {
                name: name,
                type: 'bar',
                data: data.map((item) => item.value),
              },
            ],
        };
        chart.setOption(option);
    }
}
// Define the template for the CustomerChurnDetails component
CustomerChurnDetails.template = "CustomerChurnDetails"
registry.category("actions").add("cyllo_sale_analytics.customer_details", CustomerChurnDetails);
