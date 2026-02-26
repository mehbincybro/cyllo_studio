/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
import { Component, useState } from  "@odoo/owl";
import { QualityCheck } from "@cyllo_quality/js/components/quality_check/qualityCheck";
import { CogMenuForm } from "@cyllo_base/js/cog_menu_form";

export class QualityCheckFormView extends FormController {
    static template = "QualityCheckFormView";

    async afterExecuteActionButton(clickParams){
        if (clickParams.name  === 'action_quality_check') {
            this.env.bus.trigger("GET_QUALITY_ACTIONS")
            return super.afterExecuteActionButton(clickParams)
        } else return super.afterExecuteActionButton(clickParams)
    }

    get rootData() {
        return this.model.root
    }

    get qualityProps() {
        return {
            resId: this.rootData.resId,
            qualityCheckIds : this.rootData.data.quality_check_ids._currentIds //Todo: make 'quality_check_ids' dynamic
        }
    }
}
QualityCheckFormView.components = {
    ...FormController.components,
    QualityCheck, CogMenuForm
}

export const qualityCheckFormView = {
   ...formView,
   Controller: QualityCheckFormView,
};

registry.category("views").add("quality_check_view", qualityCheckFormView);