/** @odoo-module **/
import { Systray } from "@cyllo_web/js/systray/cyllo_systray/systray";
import { patch } from "@web/core/utils/patch";
import {ChatBot} from "../chatbot/chatbot";
import {useState, useSubEnv} from "@odoo/owl";

patch(Systray.prototype, {
    setup() {
        super.setup()
        this.state = useState({
            ...this.state,
            isChatOpen: true,
        })
    },
});
Systray.components = {
    ...Systray.components,
    ChatBot
};