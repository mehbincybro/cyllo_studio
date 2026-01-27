/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { CharField } from "@web/views/fields/char/char_field";


export class MenuDialog extends Component {
    /** Class for creating a menu dialog */

    setup(){
        this.orm = useService('orm')
        this.action = useService('action')
        this.menuService = useService("menu")
        this.notification = useService("notification")
        this.data = {};
    }
    /**
     * Define the domain for menu selection.
     * @returns {Array} - The domain for menu selection.
     */
    domain() {
        const { id } = this.menuService.getCurrentApp()
        return [["id", '!=', id],["action", '=', false]]
    }
    /**
     * Get record properties for the dialog.
     * @returns {Object} - Record properties.
     */
    get recordProps() {
         var name = {
             type: "char",
             string: "Name",
         }
         var menu_id = {
             type: "many2one",
             relation: "ir.ui.menu",
             string: "Menus",
             relatedFields: ["id", "name"],
         }
         var fields = { name, menu_id }
         return {
             mode: "edit",
             onRecordChanged: (record, changes) => {
                for (var key in changes){
                    this.data[key] = changes[key]
                }
             },
             resModel: "dashboard.config.menu",
             resId: this.id,
             fieldNames: fields,
             activeFields: fields,
         };
    }
    /**
     * Handle confirmation of menu creation.
     */
    async handleConfirm() {
        if(!this.data.name){
            this.notification.add('Please provide a name', { type: 'danger' })
            return
        }
        if(!this.data.menu_id){
            this.notification.add('Please choose a menu', { type: 'danger' })
            return
        }
        const action = await this.createAction();
        const menuData = [{
            name: this.data.name,
            parent_id: this.data.menu_id,
            action: `ir.actions.client,${action}`,
            is_cyllo_analytic_menu: true,
        }]
        const menu = await this.orm.create('ir.ui.menu', menuData)
        await this.orm.call("dashboard.config", "append_menu",[this.props.rec_id, menu[0]])
        this._cancel()
        this.action.doAction("reload_context")
    }
    /**
     * Create a custom action for the menu.
     * @returns {Promise} - The created action.
     */
    async createAction() {
        const actionData = [{
            name: this.props.name,
            tag: 'cy_analytic_dashboard',
            target: 'current',
            context: {
                rec_id: this.props.rec_id,
                is_subAction: true,
            }
        }]
        const action = await this.orm.create('ir.actions.client', actionData)
        return action
    }
    /**
     * Handle cancel action and close the dialog.
     */
    async _cancel() {
         this.props.close();
    }
    get defaultProps() {
        return {
            canCreate: false,
            canCreateEdit: false,
            canOpen: false,
            canQuickCreate: false,
        }
    }
}
// Define the template for the MenuDialog component
MenuDialog.template = "cyllo_analytics.MenuDialog"
MenuDialog.components = { Dialog, Record, Many2OneField, CharField };