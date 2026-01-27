/** @odoo-module **/
import {Component, useState, useRef, onWillStart, useEffect} from "@odoo/owl";
import {KpiSheet} from "@cyllo_analytics/js/KpiSheet";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {convertToTitleCase} from "./chart_maker"

export class KpiSheetChart extends KpiSheet {
    setup() {
        super.setup();
        this.orm = useService('orm')
        useEffect(() => {
            if (this.state.query.query) {
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

    get kpiData() {
        if (this.state.query.data) {
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

    get kpiTarget() {
        if (this.state.target && this.state.query.data) {
            const target_value = Number(this.state.target)
            const kpi_data = this.kpiData
            const growth = ((kpi_data / target_value) * 100)
            this.state.kpiTarget = growth.toFixed(2)
            return this.state.kpiTarget
        }
    }

    setPercentage() {
    }

    fetchData(item) {
        var sql = item.query.replace(/\n/g, ' ');
        this.orm.call("dashboard.config", "sql_execute", [sql]).then(async (res) => {
            this.state.query.data = res
            this.state.query.measures = eval(item.measure)
        })
    }

    get Title() {
        return convertToTitleCase(this.props.name, " ")
    }
}

KpiSheetChart.defaultProps = {
    style: {
        height: `215px;`,
        width: `500px;`,
    },
    footer: false,
    editSheet: false,
}

KpiSheetChart.KpiViewType1 = owl.xml`
    <div class="media kpi-view_1 d-flex align-items-center card-inner-body">
        <div class="w-100">
            <div class="kpi-heading-container">
                <div class="kpi-heading-name" t-out="capitalizeFirstLetter(state.name)"/>
                <div class="position-relative kpi-tools-container">
                    <div class="description-kpi">
                        <div t-if="state.description" class="kpi-info-container ri-information-line">
                            <div class="kpi-info-content" t-out="state.description"/>
                        </div>
                        <t t-slot="footer"/>
                    </div>
                </div>
            </div>
            <div class="d-flex view_1-container">
                <div class="d-flex flex-column align-item-center">
                    <div class="kpi-content-view">
                        <div class="kpi-left-aligned-container">
                            <div class="kpi-left-container">
                                <div class="align-self-center kpi-icon-size">
                                    <i t-att-class="state.iconDefault" class=""/>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="kpi-middle-container">
                    <div class="media-body text-right">
                        <div class="kpi-structure">
                            <div class="me-1" t-out="formatNumber(kpiData)"/>
                            <t t-if="state.target">
                                <div>/</div>
                                <div class="ms-1" t-esc="formatNumber(state.target)"/>
                            </t>
                        </div>
                    </div>
                    <div class="progress-container">
                        <div t-att-class="getKPIClass('main')" class="small-screen-kpi-view-1">
                            <div class="progress cy-kpi-progress-bar_2"
                                 t-attf-style="width: {{stylePercentageWidth}}%;">
                                <span t-att-class="getKPIClass('sub1')"><t t-out="kpiTarget"/>%
                                </span>
                            </div>
                            <span class="is-for-small-screen" t-if="stylePercentageWidth lte 40" t-att-class="getKPIClass('sub2')" ><t t-out="kpiTarget"/>%
                            </span>
                        </div>
                        <div class="progress cy-kpi-progress-bar"
                             t-attf-style="width: {{stylePercentageWidth}}%;"/>
                        <div class="percentage-sheet cy-kpi-progress-bar-value"
                             t-attf-style="left: {{stylePercentageWidth}}%;">
                            <span><t t-out="kpiTarget"/>%
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
`
KpiSheetChart.KpiViewType2 = owl.xml`
    <div class="media d-flex kpi-view-2 justify-content-between align-items-center card-inner-body">
        <div class="kpi-content-view">
            <div class="kpi-heading-container">
                <div class="kpi-heading-name" t-out="capitalizeFirstLetter(state.name)"/>
            </div>
            <div class="kpi-left-aligned-container">
                <div class="kpi-left-container">
                    <div class="align-self-center kpi-icon-size">
                        <i t-att-class="state.iconDefault" class=""/>
                    </div>
                </div>
                <div class="kpi-middle-container">
                    <div class="media-body text-right">
                        <div class="kpi-structure">
                            <div class="me-1" t-out="formatNumber(kpiData)"/>
                            <t t-if="state.target">
                                <div>/</div>
                                <div class="ms-1" t-out="formatNumber(state.target)"/>
                            </t>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="kpi-right-container">
            <div class="kpi-view-icon-status" t-att-class="state.className"/>
            <div class="kpi-target-percentage">
                <span class="me-1" t-out="kpiTarget || '0.00'"/>
                <span>%</span>
            </div>
        </div>
        <div class="position-relative">
            <div class="description-kpi">
                <div t-if="state.description" class="kpi-info-container ri-information-line">
                    <div class="kpi-info-content" t-out="state.description"/>
                </div>
                 <t t-slot="footer"/>
            </div>
        </div>
    </div>
`
KpiSheetChart.KpiViewType3 = owl.xml`
<div class="media d-flex kpi-view-2 justify-content-between align-items-center card-inner-body">
            <div class="kpi-content-view">
                <div class="kpi-heading-container">
                    <div class="kpi-heading-name" t-out="capitalizeFirstLetter(state.name)"/>
                </div>
                <div class="kpi-left-aligned-container">
                    <div class="kpi-left-container">
                        <div class="align-self-center kpi-icon-size">
                            <i t-att-class="state.iconDefault" class=""/>
                        </div>
                    </div>
                    <div class="kpi-middle-container w-100">
                        <div class="media-body text-right">
                            <div class="kpi-structure">
                                <div class="me-1" t-out="formatNumber(kpiData)"/>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="position-relative">
                <div class="description-kpi">
                    <div t-if="state.description" class="kpi-info-container ri-information-line">
                        <div class="kpi-info-content" t-out="state.description"/>
                    </div>
                     <t t-slot="footer"/>
                </div>
            </div>
        </div>
`
KpiSheetChart.KpiInnerTemplate = owl.xml`
    <div class="card-content">
        <div class="card-body kpi-card-body">
            <t t-if="state.measureView === 'View 1'" t-call="{{ constructor.KpiViewType1 }}"/>
            <t t-if="state.measureView === 'View 2'" t-call="{{ constructor.KpiViewType2 }}"/>
            <t t-if="state.measureView === 'no_view'" t-call="{{ constructor.KpiViewType3 }}"/>
        </div>
    </div>
`
KpiSheetChart.template = owl.xml`
    <t t-if="!props.editSheet">
        <div class="card chart-container-absolute cy-kpi-top-card cy-sheet_progress-card cy_tile_o" style="justify-content: center;" t-att-style="state.style">
            <t t-call="{{ constructor.KpiInnerTemplate }}"/>
        </div>
    </t>
    <t t-else="" t-call="{{ constructor.KpiInnerTemplate }}"/>
`