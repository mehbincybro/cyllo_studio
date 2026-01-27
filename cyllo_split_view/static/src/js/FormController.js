/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";


patch(FormController.prototype, {
    setup(){
        super.setup();
        this.orm = useService('orm');
        this.splitView = null;
        this.orm.call("ir.model", "search_read", [], {
            fields: ["id", "list_split_view"],
            domain: [["model", "=", this.env.searchModel.resModel]],
        }).then(result => {
            this.splitView= result[0].list_split_view;
            if (this.splitView){
                this.canCreate = false;
            }
        });
        onMounted(() => {
            if (this.rootRef.el.offsetParent && this.rootRef.el.offsetParent.classList.contains('o_content'))
            {
                var viewTypeElements = this.rootRef.el.querySelector('.o_control_panel_navigation');
                if (viewTypeElements){
                    viewTypeElements.remove();
                }
                this.rootRef.el.classList.remove('no-smart-button')
                if (this.props.resModel === 'mrp.production'){
                    var formfieldElement = this.rootRef.el.querySelector('.o_form_view .o_group')
                    formfieldElement.style.width = '160%'
                    formfieldElement.style.setProperty('flex-direction', 'column', 'important');
                }
                var attachmentElement = this.rootRef.el.querySelector('.o_form_renderer');
                    if (attachmentElement){
                        const style = document.createElement('style');
                        style.setAttribute('id', 'o_attachment_style');
                        style.textContent = `
                        .o_form_renderer:has(>.o_attachment_preview) {
                          flex-direction: column !important;
                        }
                        .o_attachment_preview {
                          width: 100%;
                        }
                      `;
                      document.head.appendChild(style);
                    }
                var invoice_tax_element = this.rootRef.el.querySelector('.oe_subtotal_footer');
                if (invoice_tax_element){
                    invoice_tax_element.parentElement.style.flex = 'auto'
                }
            }
            else{
                const styleToRemove = document.getElementById('o_attachment_style');
                if (styleToRemove) {
                    document.head.removeChild(styleToRemove);
                }
            }
        })
        onPatched(() => {
            if(this.splitView){
                if (this.model.config.mode === 'edit'){
                        const titleElements = this.rootRef.el.querySelector('.oe_title')
                        requestAnimationFrame(() => {
                                const textareaElements = this.rootRef.el.querySelector('#name_0');
                                if (!textareaElements){
                                    const textareaElements = this.rootRef.el.querySelector('#name_1');
                                }
                                if (titleElements) {
                                    titleElements.style.height = '100px'
                                    if (textareaElements){
                                        textareaElements.style.width = 'auto'
                                        textareaElements.style.position = 'relative'
                                        textareaElements.style.left = '30px'
                                    }
                                }
                                else{
                                    if(textareaElements){
                                        textareaElements.style.width = 'auto'
                                    }
                                }
                            });
                    }
            }
        });
    },
    get deleteValidation() {
            return {
                title: _t("Validation Error"),
                body: _t("You cannot delete a record while in split view"),
                cancel: () => {},
            };
        },
    async deleteRecord() {
        if(this.splitView){
               this.dialogService.add(ConfirmationDialog, this.deleteValidation);
        }
        else{
            super.deleteRecord()
        }
    },
})
FormController.components = {
    ...FormController.components,
};



