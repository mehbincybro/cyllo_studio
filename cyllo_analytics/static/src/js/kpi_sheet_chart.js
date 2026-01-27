/** @odoo-module **/
import { Component, useState, useRef, onWillStart, useEffect } from "@odoo/owl";
import { KpiSheet } from "@cyllo_analytics/js/KpiSheet";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { convertToTitleCase } from "./chart_maker"

export class KpiSheetChart extends KpiSheet {
    setup(){
        super.setup();
        this.orm = useService('orm')
        useEffect(() => {
            if(this.state.query.query){
                this.fetchData(this.state.query)
            }
        }, () => [this.state.query.query])
        useEffect(() => {
            this.setStyle()
        }, () => [this.props.style])
    }
    setStyle() {
       var style = Object.keys(this.props.style).map(key => {
                          return `${key}:${this.props.style[key]}`;
                        }).join('');
       this.state.style = style
    }

    get kpiData(){
        if(this.state.query.data){
            var key = this.state.query.measures[0]
            var val = 0
            var result = this.state.query.data
            if (result) {
                for (let i = 0; i < result.length; i++) {
                    val = val + result[i][key];
                }
            }
            return val.toFixed(2)
        }
    }

    get kpiTarget(){
        if(this.state.target && this.state.query.data){
            const target_value = Number(this.state.target)
            const kpi_data = this.kpiData
            const growth = ((kpi_data/target_value)*100)
            this.state.kpiTarget = growth.toFixed(2)
            return this.state.kpiTarget
        }
    }
    setPercentage() {}

    fetchData(item){
        var sql = item.query.replace(/\n/g, ' ');
        this.orm.call("dashboard.config", "sql_execute", [sql]).then(async (res) => {
            this.state.query.data = res
            this.state.query.measures = eval(item.measure)
        })
    }
    get Title () {
        return convertToTitleCase(this.props.name, " ")
    }
}
KpiSheetChart.defaultProps = {
    style: {
        height:`215px;`,
        width:`500px;`,
    },
    footer: false,
    editSheet: false,
}
KpiSheetChart.InnerTemplate = owl.xml`
    <div class="d-flex align-items-center gap-2 justify-content-end cy_kpi_dashboard" style="position: absolute; right: 2%; top: 0px;">
        <div class="cy-sheet_info-icon cy_kpi d-flex">
            <t t-if="this.state.description">
                <button class="cy_kpi_icon pe-3">
                    <i class="ri-information-line cy_kpi-query-line"/>
                    <div class="cy-sheet_info-content" t-esc="this.state.description"/>
                </button>
                
            </t>
            <t t-slot="footer"/>
        </div>
    </div>
    <div class="d-flex  cy-kpi-div-container" >
        <div class="p-1 pt-0">
            <button class="cy_kpi_icon">
                <i t-att-class="this.state.iconDefault" class="kpi-icon cy-kpi-chart-icon"/>
            </button>
        </div>
        <div class="py-2 px-3" t-att-style="'height: 112.0234375px; width: 85%;'">
            <div><span class="cy-sheet_card-heading cy-kpi-query-sheet-head" style="width: 75%; text-wrap: nowrap; overflow: hidden; text-overflow: ellipsis;">
                <t t-out="Title"/>
            </span></div>
            <div><span class="cy-sheet_card-progress-count">
                <h3 class="cy-kpi-query-data"   >
                    <t t-esc="kpiData"/>
                    <t t-if="this.state.target">  /
                        <t t-esc="this.state.target"/>
                    </t>
                </h3>
            </span></div>
            <div t-if="this.state.target" class="pb-0 cy-kpi-progress-container" >
                <t t-if="this.state.measureView == 'View 1' and this.state.target">
                    <div class="progress-container" t-ref="proBar">
                        <div class="progress cy-kpi-progress-bar" t-attf-style="width: {{stylePercentageWidth}}%;"/>
                        <div class="cy-kpi-progress-bar-value percentage" t-attf-style="left: {{stylePercentage}}%;">
                            <span><t t-out="kpiTarget"/>%</span>
                        </div>
                        <div class="progress cy-kpi-progress-bar_2" t-attf-style="width: {{stylePercentageWidth}}%;">
                            <span><t t-out="kpiTarget"/>%</span>
                        </div>
                    </div>
                </t>
                <t t-if="this.state.measureView == 'View 2'">
                    <span class="cy-sheet_prgress-state_count cy-kpi-view_2-span"
                          t-if="this.state.target"><t t-esc="kpiTarget"/> %
                        <i t-att-class="state.className"/>
                    </span>
                </t>
            </div>
        </div>
    </div>
`
KpiSheetChart.template = owl.xml`
    <t t-if="!props.editSheet">
        <div class="card chart-container-absolute cy-kpi-top-card cy-sheet_progress-card cy_tile_o" style="justify-content: center;" t-att-style="state.style">
            <t t-call="{{ constructor.InnerTemplate }}"/>
        </div>
    </t>
    <t t-else="" t-call="{{ constructor.InnerTemplate }}"/>
`

