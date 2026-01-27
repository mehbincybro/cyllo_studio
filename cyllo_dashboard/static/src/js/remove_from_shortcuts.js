/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import {session} from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
const { Component, useState, onMounted } = owl;
const cogMenuRegistry = registry.category("cogMenu");

export class RemoveFromShortcut extends Component {
    setup() {
        this.orm = useService('orm');
        this.notification = useService("notification");
        this.rpc = useService("rpc");
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
    async removeFromShortcuts() {
        if (this.env.config.actionId){
            const result = await jsonrpc('/remove_from_shortcuts', {
                actionId : this.env.config.actionId,
            });
            if (result) {
                this.notification.add(
                    sprintf(_t(`"%s" removed from shortcut`), this.state.name),
                    {
                        title: 'Shortcut Removed',
                        type: "warning",
                    }
                );
                this.state.name = this.env.config.getDisplayName();
                this.env.services['action'].doAction('reload_context');
            } else {
                this.notification.add(_t("Could not remove shortcut from dashboard"), {
                    type: "danger",
                });
            }
        }
    }
}

RemoveFromShortcut.template = "cyllo_dashboard.RemoveFromShortcuts";
RemoveFromShortcut.components = { DropdownItem };

export const RemoveFromShortcutItem = {
    Component: RemoveFromShortcut,
    groupNumber: 20,
    isDisplayed: ({ config }) => config.viewType != "form",
};

cogMenuRegistry.add("remove-from-shortcut", RemoveFromShortcutItem, { sequence: 10 });
