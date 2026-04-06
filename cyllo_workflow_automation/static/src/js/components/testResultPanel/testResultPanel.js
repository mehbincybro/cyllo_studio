/** @odoo-module */
import { Component } from "@odoo/owl";

export class TestResultPanel extends Component {
    get hasErrors() {
        return Boolean(this.props.summary?.error);
    }
}

TestResultPanel.template = "cyllo_workflow_automation.TestResultPanel";
