/** @odoo-module **/
import {_t} from "@web/core/l10n/translation";
import {ListController} from "@web/views/list/list_controller";
import {patch} from "@web/core/utils/patch";
import {View} from "@web/views/view";
import {useBus, useService} from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const {useState, useRef} = owl;

patch(ListController.prototype, {
    setup() {
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

    async selected_split_model() {
        await this.orm.call('ir.model', "add_split_view", [this.model.env.searchModel.resModel])
    },

    async unselect_split_model() {
        await this.orm.call('ir.model', "remove_split_view", [this.model.env.searchModel.resModel])
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

    set SpiltFormView(value) {
        return value
    },

    async openRecord(record) {
        this.is_split_view = await this.orm.call("ir.model", "get_split_view_mode", [this.model.env.searchModel.resModel]);
        if (this.is_split_view[0].list_split_view) {
            if (this.state.currentSelectedId != record.resId) {
                this.state.currentSelectedId = record.resId;
                this.rootRef.el.querySelector('.o_content').style.display = 'flex';
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
        } else {
            super.openRecord(record);
        }
    },

    closeSplit(ev) {
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

    getStaticActionMenuItems() {
        const list = this.model.root;
        const isM2MGrouped = list.groupBy.some((groupBy) => {
            const fieldName = groupBy.split(":")[0];
            return list.fields[fieldName].type === "many2many";
        });
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.onExportData(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped,
                sequence: 20,
                icon: "ri-archive-line",
                description: _t("Archive"),
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped,
                sequence: 30,
                icon: "ri-inbox-unarchive-line",
                description: _t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            },
            duplicate: {
                isAvailable: () => this.activeActions.duplicate && !isM2MGrouped,
                sequence: 35,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecords(),
            },
            delete: {
                isAvailable: () => this.activeActions.delete && !isM2MGrouped,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            },
        };
    }
})
ListController.components = {...ListController.components, View}