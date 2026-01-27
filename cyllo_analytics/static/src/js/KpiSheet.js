/** @odoo-module **/

import { Component, useState, useEffect, useRef, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
const ICONCLASS = ['ri-time-line', 'ri-history-fill', 'ri-discuss-line', 'ri-roadster-line', 'ri-calendar-2-line', 'ri-line-chart-line', 'ri-folder-chart-line', 'ri-team-fill', 'ri-user-2-fill', 'ri-pie-chart-2-fill', 'ri-image-2-fill', 'ri-tools-fill', 'ri-store-2-fill', 'ri-notification-3-fill', 'ri-arrow-up-line', 'ri-arrow-right-up-line', 'ri-arrow-left-up-line', 'ri-arrow-up-down-fill', 'ri-medal-line', 'ri-store-3-fill', 'ri-database-line', 'ri-wallet-3-fill', 'ri-coupon-3-line', 'ri-thumb-up-line', 'ri-group-line', 'ri-contacts-book-line', 'ri-global-line', 'ri-funds-box-fill', 'ri-mail-line', 'ri-briefcase-4-line', 'ri-shake-hands-line', 'ri-megaphone-fill', 'ri-pencil-fill', 'ri-bank-card-line', 'ri-contacts-book-2-line', 'ri-book-fill', 'ri-customer-service-fill', 'ri-dashboard-3-line', 'ri-survey-line', 'ri-hand-heart-fill', 'ri-map-pin-line', 'ri-pushpin-fill', 'ri-truck-line', 'ri-filter-fill', 'ri-emotion-happy-line'];

export class KpiSheet extends Component {
    setup(){
        this.actionService = useService("action");
        this.ref = useRef("proBar")
        this.state = useState({
            name: this.props.name,
            description: false,
            target: false,
            query: this.props.query,
            props: this.props,
            className: '',
            measureView: 'View 1',
            redirect: false,
            model: this.props.model,
            query_data: this.props.query_data,
            data: false,
            kpiTarget: 0,
            style: "",
            height: "",
            iconDefault: 'ri-time-line'
        })
        this.query_data = useState({
            dimension: []
        })
        useEffect(() => {
            this.updateClass();
        }, () => [this.state.target, this.state.measureView, this.kpiTarget])
        useEffect(() => {
            this.updateView();
        }, () => [this.state.measureView])
        onWillUpdateProps((newProps) => {
            this.state.name = newProps.name
        })
        useEffect(() => {
            this.onSaveData();
        }, () => [this.state.target, this.state.measureView, this.state.description, this.state.redirect, this.state.name, this.state.iconDefault])

        onWillStart(async () => {
            if(this.props.kpi){
                this.state.target = this.props.kpi.target
                this.state.description = this.props.kpi.description
                this.state.measureView = this.props.kpi.measureView || this.state.measureView
                this.state.redirect = this.props.kpi.redirect
                this.state.name = this.props.kpi.name || this.props.name
                this.state.kpiTarget = this.props.kpi.kpiTarget
                this.state.iconDefault = this.props.kpi.icon || 'ri-time-line'
            }
        })
        this.kpi_config = useRef('KpiConfig')
    }
    get kpiData(){
        if(this.state.props.query.data && this.state.props.query.data.measures){
            var key = this.props.query.data.measures[0]
            var val = 0
            var result = this.props.query.data.data
            if (result) {
                for (let i = 0; i < result.length; i++) {
                    val += parseFloat(result[i][key]);
                }
            }
            return val?.toFixed(2)
        }
    }
    get kpiTarget(){
        if(this.state.target && this.state.props.query.data){
            const target_value = Number(this.state.target)
            const kpi_data = Number(this.kpiData)
            const growth = ((kpi_data/target_value)*100)
            this.state.kpiTarget = growth.toFixed(2)
            return growth.toFixed(2)
        }
    }
    updateClass(){
        var condition = this.kpiTarget
        if (this.stylePercentageWidth === 100) {
            const percentageElement = this.ref.el?.querySelector(".percentage");
            if (percentageElement) {
                const percentageWidth = percentageElement.offsetWidth;
                const containerWidth = percentageElement.parentElement.offsetWidth;
                const newLeftPercentage = (((containerWidth - percentageWidth) / containerWidth) * 100);
                percentageElement.style.setProperty('--left-percentage', `${newLeftPercentage}%`);
            }
        }
        if (condition >= 100 && this.state.measureView == 'View 2') {
            this.state.className = 'ri-arrow-right-up-line  cy-success-txt'
        } else {
            this.state.className = 'ri-arrow-right-down-line  cy-danger-txt'
        }
    }
    updateView(){
        return this.state.measureView
    }
    get stylePercentage() {
        return this.kpiTarget > 100 ? 93  : this.kpiTarget;
    }
    get stylePercentageWidth() {
        return this.kpiTarget > 100 ? 100 : this.kpiTarget;
    }
    domain(){
        if(this.state.query_data.where.length != 0){
            if(this.state.query_data.where[0].active){
                var conditionString = this.state.query_data.where[0].domain;
                var parts = conditionString.split(' ');
                var field = parts[0].split('.')[1];
                var operator = parts[1];
                var value = parts[2].replace(/'/g, '');
                var condition = [field, operator, value];
                return [condition]
            }
        }
    }
     onSaveData(){
        var vals ={
            target: this.state.target || false,
            measureView: this.state.measureView || false,
            description: this.state.description || false,
            redirect: this.state.redirect || false,
            name: this.state.name || this.props.name,
            kpiTarget: this.state.kpiTarget || false,
            icon: this.state.iconDefault || 'ri-time-line',
        }
        this.props.onUpdate && this.props.onUpdate(vals)
    }
    openRecord(){
        if(this.state.redirect){
            return this.actionService.doAction({
                name: _t("My Dashboard"),
                type: 'ir.actions.act_window',
                res_model: this.state.model[0].model,
                view_mode: 'tree,form,calendar',
                views: [[false, 'list'],[false, 'form']],
                domain: this.domain(),
                target: 'current',
            });
        }
    }
    onClickKpiIcon(){
        this.kpi_config.el.querySelector(".cy-sheet_icon-selection-box").classList.toggle("show")
    }
    onCloseKpiIcon(){
        this.kpi_config.el.querySelector(".cy-sheet_icon-selection-box").classList.remove("show")
    }
    selectIcon(className){
         this.state.iconDefault = className
    }
   get IconClass(){
        return ICONCLASS
   }
}
KpiSheet.template = "cyllo_analytics.KpiSheet"
