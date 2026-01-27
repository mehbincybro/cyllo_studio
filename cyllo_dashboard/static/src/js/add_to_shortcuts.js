/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { jsonrpc } from "@web/core/network/rpc_service";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import {session} from "@web/session";
import { _t } from "@web/core/l10n/translation";
const { Component, useState,onMounted } = owl;
const cogMenuRegistry = registry.category("cogMenu");
export class AddToShortcut extends Component {
    setup() {
        this.orm = useService('orm');
        this.notification = useService("notification");
        this.state = useState({
            name: this.env.config.getDisplayName(),
            isAddedToShortcut : false,
        });
        onMounted(async () => {
            var shortcut = await this.orm.searchRead('shortcut.menu', [])
            var is_added_to_shortcut = shortcut.find((rec) => rec.window_action_id[0] === this.env.config.actionId
                                       && rec.create_uid[0] === session.uid)
            if (is_added_to_shortcut){
                this.state.isAddedToShortcut = true
            }
        }
    )}
    async addToShortcuts() {
        if (this.env.config.actionId){
            const result = await jsonrpc('/add_to_shortcuts', {
                actionId : this.env.config.actionId,
                name : this.state.name,
                model : this.env.searchModel.resModel
            });
            if (result) {
                this.notification.add(
                    sprintf(_t(`"%s" added to your shortcuts`), this.state.name),
                    {
                        title: 'Shortcut Added',
                        type: "success",
                    }
                );
                this.state.name = this.env.config.getDisplayName();
                this.env.services['action'].doAction('reload_context');
            }
            else {
                this.notification.add(_t("Could not add shortcut to dashboard"), {
                    type: "danger",
                });
            }
        }
    }
}

AddToShortcut.template = "cyllo_dashboard.AddToShortcuts";
AddToShortcut.components = { DropdownItem ,Dropdown };

export const addToShortcutItem = {
    Component: AddToShortcut,
    groupNumber: 20,
    isDisplayed: ({ config }) => config.viewType != "form",
};

cogMenuRegistry.add("add-to-shortcut", addToShortcutItem, { sequence: 10 });
