/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import { Component, useState, useSubEnv} from "@odoo/owl";
import { DialPad } from '@cyllo_twilio_voice_call/js/outgoing_call'
import { FetchIncomingCall } from '@cyllo_twilio_voice_call/js/incoming_call'

class SystrayIcon extends Component {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.state = useState({
            showKeypad: false,
            showIncomingCall: false
        })
        this.props.showIncomingCall = this.state.showIncomingCall
        useSubEnv({
            toggle_keypad: this.toggle_keypad.bind(this),
        });
    }

    toggle_keypad() {
        this.state.showKeypad = false
    }
}
SystrayIcon.template = "dial_button";
SystrayIcon.components = {
    DialPad,
    FetchIncomingCall
};
const systrayItem = {
    Component: SystrayIcon,
};
registry.category("systray").add("SystrayIcon", systrayItem, {});