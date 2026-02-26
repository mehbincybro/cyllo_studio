/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";


export class QualityInstructions extends Component {

}
QualityInstructions.template = "cyllo_quality.InstructionDialog";
QualityInstructions.components = {Dialog};
registry.category("actions").add("quality_instruction_action", QualityInstructions);


