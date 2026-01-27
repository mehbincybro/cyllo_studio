/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart } from "@odoo/owl";
import { Record } from "@web/model/record";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { CharField } from "@web/views/fields/char/char_field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ShareDialog extends Component {
    // This is a class for share dialog box
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.data = {}
    }

    /**
     * Get properties for the Record component.
     * @returns {object} - Record properties.
     */
     get recordProps() {
        var related = {
            display_name: {
                name: "display_name",
                type: "char"
            }
        }

         var name = {
             type: "char",
             string: "Name",
         }

         var reader_ids = {
             type: "many2many",
             string: "users",
             relation: "res.users",
             related: {
                activeFields: related,
                fields: related,
             },
         }

         var contributor_ids = {
             type: "many2many",
             string: "users",
             relation: "res.users",
             related: {
                activeFields: related,
                fields: related,
             },
         }
         var fields = { name, reader_ids, contributor_ids }
         var self = this
         return {
             mode: "edit",
             onRecordChanged: (record, changes) => {
                for (var key in changes){
                    self.data[key] = changes[key]
                }
             },
             resModel: "spreadsheet.spreadsheet",
             resId: this.props.id,
             fieldNames: fields,
             activeFields: fields,
         };
    }

    /**
     * Handles the sharing of a spreadsheet sheet.
     * If the sheet already exists (identified by the presence of 'id' in props), updates the existing sheet data
     * using the ORM write operation.
     * Triggers notification of successful sharing and closes the dialog.
     *
     * @returns {void}
     */
    async onShareSheet() {
        if(this.props.id){
            this.orm.write("spreadsheet.spreadsheet", [this.props.id], this.data);
            this.props.onClickSave(this.data)
            this.notification.add(_t("Successfully Shared"), {
                type: "success",
            });
        }
        this.props.close()
    }

    get defaultConfProps() {
        return {
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
        }
    }

}
// Define the template and components for the ShareDialog component
ShareDialog.template = "cyllo_spreadsheet.ShareDialog";
ShareDialog.defaultProps = {
    onClickSave: () => {}
};
ShareDialog.components = { Dialog, Record, Many2OneField, CharField , Many2ManyTagsField, IntegerField };