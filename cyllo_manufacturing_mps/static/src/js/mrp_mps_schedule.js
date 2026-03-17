/** @odoo-module */
import { registry} from '@web/core/registry';
import { Component } from "@odoo/owl";
export class MPSClientAction extends Component {

setup(){

}
}
MPSClientAction.template = "cyllo_manufacturing_mps.MPSClientAction"
registry.category("actions").add("cyllo_manufacturing_mps.mps", MPSClientAction)
