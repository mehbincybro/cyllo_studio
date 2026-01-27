/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
/**  Extends  publicWidget to get value onClick selection in website **/
publicWidget.registry.ServicePortal = publicWidget.Widget.extend({
    selector: '.cy_service_create',
    events: {
        'change .cy_service_handler': '_onChangeHandler',
        'change .request_type': '_onChangeRequestType',
        'change .category_sel': '_onChangeCategory',
    },
    /**  Assign service handler based on user's related employee**/
    start() {
        this.orm = this.bindService("orm");
        var handler = this.$el.find(".cy_service_handler")
        const handler_data = handler[0][1].getAttribute('value')
        var emp_hidden = this.$el.find("#cy_emp_hidden")
        if (handler[0].length == 2){
            var handler_name = handler[0][1].innerText
            var emp_inp = this.el.children[0][1];
            var department = this.$el.find(".handlers_dept")
            department.empty()
            department.append("<option value=" + handler[0][1].getAttribute('data')
            +  ">" + handler[0][1].getAttribute('title') + "</option>")
            handler.empty();
            handler.append("<option value=" + handler_data +
              " data=" + emp_hidden.value + " title=" + emp_inp.getAttribute('title') + ">"
              + handler_name + "</option>")
        }
    },
    /** Add department of employee on change service handler selection **/
    _onChangeHandler: function(ev) {
        var department = this.$el.find(".handlers_dept")
        department.empty()
        department.append("<option value=" + ev.target.options[ev.target.selectedIndex].getAttribute('data') +
          ">" + ev.target.options[ev.target.selectedIndex].getAttribute('title') + "</option>")
    },
    /** Show/Hide maintenance type and service equipment based on category **/
    _onChangeCategory: async function(ev) {
        const ser_category = this.$el.find(".category_sel")
        const ser_equip_div = this.$el.find(".cy-ser_equip")
        const cy_service_equip = this.$el.find(".cy_service_equip")
        const maintenance_type_sel = this.$el.find(".cy_maintenance_type")
        const maintenance_type = this.$el.find(".cy-maintenance_type")
        const category = ev.target.options[ev.target.selectedIndex].value
//        if (category){
//            const services = await this.orm.searchRead("hr.service.category",
//                [["id", "=", Number(category)]])
//            if (services[0].require_maintenance_order){
//                ser_equip_div.removeClass('d-none');
//                cy_service_equip[0].setAttribute('required', true);
//                maintenance_type.removeClass('d-none');
//                maintenance_type_sel[0].setAttribute('required', true);
//            }else{
//                ser_equip_div.addClass('d-none');
//                cy_service_equip[0].removeAttribute('required');
//                maintenance_type.addClass('d-none');
//            }
//        }else{
//            ser_equip_div.addClass('d-none');
//            cy_service_equip[0].removeAttribute('required');
//            maintenance_type.addClass('d-none');
//        }
        const categoryy = ev.target.value;
        console.log("category", categoryy)
        console.log("category", ev.target.options[ev.target.selectedIndex].value)
        if (category) {
          this.orm.searchRead("hr.service.category", [["id", "=", Number(category)]])
            .then(services => {
              const requiresMaintenance = services[0]?.require_maintenance_order;
              ser_equip_div.toggleClass('d-none', !requiresMaintenance);
              cy_service_equip[0].toggleAttribute('required', requiresMaintenance);
              maintenance_type.toggleClass('d-none', !requiresMaintenance);
              maintenance_type_sel[0].toggleAttribute('required', requiresMaintenance);
            });
        } else {
          // Reset elements when category is empty
          ser_equip_div.addClass('d-none');
          cy_service_equip[0].removeAttribute('required');
          maintenance_type.addClass('d-none');
        }

    },
    /** Show service details and custody details inputs based on selecting the type **/
    _onChangeRequestType: function(ev) {
        var equipment = this.$el.find(".equipment")
        var equipment_sel = this.$el.find("#equipment_sel")
        var return_dt_div = this.$el.find(".return_dt_div")
        var return_date = this.$el.find(".return_date")
        var category = this.$el.find(".category")
        var category_sel = this.$el.find(".category_sel")
        if (ev.target.options[ev.target.selectedIndex].value == 'custody'){
          category_sel[0].removeAttribute('required');
          equipment.removeClass('d-none');
          equipment_sel[0].setAttribute('required', true);
          return_dt_div.removeClass('d-none');
          return_date[0].setAttribute('required', true);
          category[0].removeAttribute('required');
          category.addClass('d-none');
        }
        else{
          equipment.addClass('d-none');
          equipment[0].removeAttribute('required');
          return_dt_div.addClass('d-none');
          return_date[0].removeAttribute('required');
          category.removeClass('d-none');
          category_sel[0].setAttribute('required', true);
        }
    },
});