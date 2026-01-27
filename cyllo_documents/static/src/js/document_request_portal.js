/* @odoo-module */
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.serviceRequestForm = publicWidget.Widget.extend({
    selector: '.document_req_portal, .document_req_nav',
    events: {
        'change #document_request_template': 'changeSelection',
    },
    changeSelection: function (ev) {
        /* function to add template into page if the template field changes*/
        var self = this;
        jsonrpc('/document_request/templates', {
            'template_id': ev.target.value
        }).then(function (result) {
            self.el.children[0].children[0].children[0][1].nextElementSibling.nextElementSibling.innerHTML = result
        })
    },
});