/** @odoo-module */
import { FormLabel } from "@web/views/form/form_label";
import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';
patch(FormLabel.prototype, {
/** Patch FormLabel to edit the label on double click */
    setup(){
        super.setup();
        this.orm = useService('orm');
    },
    async onDblClick(ev){
    /** Edit label via double click on it */
        this.access = false
        var self = this;
        self.field_name = ''
        if(ev.target.localName === 'label'){
            var input = document.createElement('input');
            input.id = 'label_edit';
            input.className = 'edit_label';
            input.dataset.label_for = ev.target.getAttribute('for');
            input.value = ev.srcElement.innerText;
            self.input = input;
            self.field_name = ev.srcElement.innerText;
            ev.target.parentNode.replaceChild(input, ev.target);
            document.querySelector("#label_edit").onmouseout = function() {self.ChangeLabel(event)};
        }
    },
     ChangeLabel(event) {
        /** Changes the label after move the mouse outside the label box */
        var self = this;
        var input = self.input
        var ModelName = this.props.record.resModel
        var ViewType = this.env.config.viewType
        var inputField = this.field_name
        var inputValue = event.srcElement.value
        var field_tech_name;
        var inputFieldName = document.querySelector("#label_edit").getAttribute('data-label_for')
        this.orm.call('ir.ui.view',
         'edit_xml_field_label', [ModelName, ViewType, inputField, inputFieldName, inputValue]
        ).then(function(result) {
            if (result === true) {
            event.srcElement.innerText = inputValue;
            event.target.parentNode.replaceChild(input, event.target);
            location.reload();
            }
        });
     }
});
