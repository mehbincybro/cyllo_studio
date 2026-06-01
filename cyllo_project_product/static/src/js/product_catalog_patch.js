/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useSubEnv } from "@odoo/owl";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { _t } from "@web/core/l10n/translation";

// Patch 1: Pass project_task_id in every RPC update call
patch(ProductCatalogKanbanRecord.prototype, {
    _getUpdateQuantityAndGetPrice() {
        const result = super._getUpdateQuantityAndGetPrice();
        if (this.env.projectTaskId) {
            result.project_task_id = this.env.projectTaskId;
        }
        return result;
    }
});

// Patch 2: "Back to Task" button in the catalog header
patch(ProductCatalogKanbanController.prototype, {
    setup() {
        super.setup();
        this.taskId = this.props.context.default_project_task_product_id;
        if (this.taskId) {
            useSubEnv({ projectTaskId: this.taskId });
        }
    },

    async _defineButtonContent() {
        if (this.taskId) {
            this.buttonString = _t("Back to Task");
            return;
        }
        await super._defineButtonContent();
    },

    async backToQuotation() {
        if (this.taskId) {
            if (this.env.config.breadcrumbs.length > 1) {
                await this.action.restore();
            } else {
                await this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "project.task",
                    views: [[false, "form"]],
                    view_mode: "form",
                    res_id: this.taskId,
                });
            }
            return;
        }
        await super.backToQuotation();
    }
});
