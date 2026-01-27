 /** @odoo-module **/
import {Component, useState} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
const { components } = owl
import { browser } from "@web/core/browser/browser";

/**
 * Component for spreadsheet sheet naming
 */
export class SpreadsheetName extends Component {
    setup() {
        this.state = useState({
            name: this.props.name,
        });
    }
    _onNameChanged(ev) {
        if (ev.target.value) {
            this.env.saveRecord({name: ev.target.value});
        }
        this.state.name = ev.target.value;
    }
}
SpreadsheetName.template = "cyllo_spreadsheet.SpreadsheetName";

export class SpreadsheetControlPanel extends ControlPanel {
    goBack() {
        browser.history.go(-1)
    }
}

SpreadsheetControlPanel.template = "cyllo_spreadsheet.SpreadsheetControlPanel";
SpreadsheetControlPanel.props = {
    ...ControlPanel.props,
    record: Object,
};
SpreadsheetControlPanel.components = {
    SpreadsheetName,
};