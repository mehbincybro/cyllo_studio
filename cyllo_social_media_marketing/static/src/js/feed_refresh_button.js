/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
patch(FormController.prototype, "sale_order", {
   setup(){
      this._super.apply();
      this.action = useService("action")
   },
   buttonClicked(){}
});