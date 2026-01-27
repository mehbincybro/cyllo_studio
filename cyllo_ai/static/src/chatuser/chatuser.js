/** @odoo-module **/
import { Component } from "@odoo/owl";
export class ChatUser extends Component{
    static props = {
        text: { type: String, optional: true},
        html: { type: String, optional: true},
        userImage: { type: String, optional: true},
    };
    setup(){
    super.setup(...arguments);

    }
}
ChatUser.template = "ChatUser";
