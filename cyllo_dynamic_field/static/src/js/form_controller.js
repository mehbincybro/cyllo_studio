/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";
/**
patch the FormController class to add new menu in action button
*/
patch(FormController.prototype, {
    async setup() {
        super.setup();
        this.orm = useService('orm');
        var self = this;
        onWillStart(async () => {
            self.settingsAccess = await this.user.hasGroup('base.group_system');
        });
    },
    /**
    *Get current view's form_external_id and model. Then Open wizard for create new field
    */
     CreateField(){
         this.orm.call('field.create', 'get_xml_ids', [1], {model: this.props.resModel}).then((result) => {
         var form_external_id = result.form_external_id;
         var model = result.model;
         this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Field Creation'),
            res_model: "field.create",
            target: 'new',
            context: {
                'active_model': this.props.resModel,
                'default_form_view_external_id': form_external_id,
                'default_model': model,
            },
            views: [[false, 'form']],
        });
        })
    },
    /**
    *function that creates archive, unarchive, duplicate, delete and Create_field
    *menus in action button
    */
    getStaticActionMenuItems() {
        const { activeActions } = this.archInfo;
        return {
            archive: {
                isAvailable: () => this.archiveEnabled && this.model.root.isActive,
                sequence: 10,
                description: _t("Archive"),
                icon: "oi oi-archive",
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !this.model.root.isActive,
                sequence: 20,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.model.root.unarchive(),
            },
            duplicate: {
                isAvailable: () => activeActions.create && activeActions.duplicate,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecord(),
            },
            delete: {
                isAvailable: () => activeActions.delete && !this.model.root.isNew,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.deleteRecord(),
                skipSave: true,
            },
            /* function that show Add a New Field menu in all action button*/
            Create_field: {
                isAvailable: () => this.settingsAccess,
                sequence: 50,
                description: _t("Add Field"),
                callback: () => this.CreateField(),
                skipSave: true,
            },
        };
    },
});
