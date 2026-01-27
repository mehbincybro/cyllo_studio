/** @odoo-module **/
const { Component } = owl;
import { useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { WhatsappPartnerProfile } from './whatsapp_partner_profile'
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { session } from "@web/session";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";


export class WhatsappSidebar extends Component {
    /* This function appears to initialize various properties and set up
    event listeners. */
    async setup() {
        this.orm = useService('orm')
        this.actionService = useService("action");
        this.searchBox = useRef('searchBox')
        this.account_uid = useRef('account_uid')
        this.app_uid = useRef('app_uid')
        this.phone_uid = useRef('phone_uid')
        this.token = useRef('token')
        this.dialog = useService("dialog");
        this.state = useState({
            partnerHistory: {},
            dropdown: false,
            user: {},
            configuration: false
        })
        this.state.user = await this.orm.call("res.users", "get_user_data", [{}, session.uid])
    }

    /* Quick search button function to visible global search area */

    /*
    Keyup function of search area to show partners as dropdown based
    on search
    */
    async onKeyUpSearch(ev) {
        this.state.partnerHistory = await this.orm.searchRead(
            "res.partner",
            [
                ["name", "ilike", this.searchBox.el.value],
                ["whatsapp_number", "!=", null],
            ],
            []
        );
        this.state.dropdown = true
    }

    onSelectPartner(partner) {
        this.searchBox.el.value = ""
        this.state.dropdown = false
        this.env.bus.trigger('SEARCH_PARTNER', {partner: partner})
    }

    async getUserProfile() {
        const views = await this.orm.call("res.users", "get_whatsapp_user_view", [])
        await this.actionService.doAction({
            name: 'User',
            res_model: "res.users",
            views: [[views[0].id, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
            res_id: this.env.session.uid,
            target: "new",
        });
    }

    async getTemplate() {
        await this.actionService.doAction({
            name: 'Whatsapp Template',
            res_model: "whatsapp.template",
            views: [[false, "tree"]],
            type: "ir.actions.act_window",
            view_mode: "tree",
            target: "current",
        });
    }

    async updateConfig() {
        if (this.state.configuration) {
            if (this.account_uid.el.value === this.state.user['account_uid'] &&
                this.app_uid.el.value === this.state.user['app_uid'] &&
                this.phone_uid.el.value === this.state.user['phone_uid'] &&
                this.token.el.value === this.state.user['token']) {
                this.state.configuration = false
            } else {
                this.dialog.add(ConfirmationDialog, {
                    body: _t("Do you want to save the changes?"),
                    confirmLabel: _t("Yes"),
                    confirm: async () => {
                        await this.orm.call("res.users", "action_update_data", [session.uid,
                            this.account_uid.el.value, this.app_uid.el.value,
                            this.phone_uid.el.value, this.token.el.value])
                        window.location.reload();
                    },
                    cancel: () => {
                        window.location.reload();
                    },
                });
            }
        } else {
            this.state.configuration = true
        }
    }
}

/* Associate 'WhatsappSidebar' template with the WhatsappSidebar component.*/
WhatsappSidebar.template = 'WhatsappSidebar';
WhatsappSidebar.components = {
    WhatsappPartnerProfile,
    Dropdown,
    DropdownItem,
}