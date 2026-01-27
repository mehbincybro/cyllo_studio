/** @odoo-module **/
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { View } from "@web/views/view";
import { useBus, useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
const { useState, useRef } = owl;


patch(ListController.prototype, {
    setup(){
        super.setup();
        this.orm = useService('orm');
        this.is_split_view = null
        this.spil = useState({
            split_view_enable: false
        })
        this.state = useState({
            currentSelectedId: false
        })
        this.splitViewForm = useRef('split-form-parent')
        useBus(this.env.bus, "split_view_selected_model", this.selected_split_model);
        useBus(this.env.bus, "remove_split_view_selected_model", this.unselect_split_model);
        useBus(this.env.bus, "update_current_selected_id", this.updateCurrentSelectedId);
    },
    selected_split_model(){
        this.orm.call('ir.model',"add_split_view",[this.model.env.searchModel.resModel])
    },
    unselect_split_model(){
        this.orm.call('ir.model',"remove_split_view",[this.model.env.searchModel.resModel])
    },
    get SpiltFormView() {
        this.props.display.controlPanel = true;
        return {
            type: "form",
            mode: "edit",
            resModel: this.props.resModel,
            resId: this.state.currentSelectedId,
            loadActionMenus: true,
            context: this.props.context,
        }
    },
    set SpiltFormView(value){
        return value
    },
    async openRecord(record) {
        this.is_split_view = await this.orm.call("ir.model", "search_read", [], {
            fields: ["id", "list_split_view"],
            domain: [["model", "=", this.model.env.searchModel.resModel]],
        });
        if(this.is_split_view[0].list_split_view){
            if(this.state.currentSelectedId!=record.resId){
                this.state.currentSelectedId = record.resId
                this.rootRef.el.querySelector('.o_content').style.display = 'flex'
                const purchaseDashboardElement = this.rootRef.el.querySelector('.o_purchase_dashboard');
                if (purchaseDashboardElement) {
                    purchaseDashboardElement.style.display = 'none';
                }
                const expenseDashboardElement = this.rootRef.el.querySelector('.o_expense_container');
                if (expenseDashboardElement) {
                    expenseDashboardElement.classList.add('expense_hidden');
                }
                this.env.bus.trigger('split_view_record_clicked');
            }
        }
        else{
            super.openRecord(record)
        }
    },
    closeSplit(ev){
        this.env.bus.trigger('split_view_close_clicked');
        this.state.currentSelectedId = false
        if (this.rootRef.el.querySelector('.o_content').style.display === 'flex') {
            this.rootRef.el.querySelector('.o_content').style.display = ''
        }

        const purchaseDashboardElement = this.rootRef.el.querySelector('.o_purchase_dashboard');
        if (purchaseDashboardElement) {
            purchaseDashboardElement.style.display = '';
        }
    },
    updateCurrentSelectedId() {
        this.state.currentSelectedId = false
    },
})
ListController.components = {...ListController.components, View}
