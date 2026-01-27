/** @odoo-module **/
import { Component, onMounted, useRef, onWillStart, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

/**
 * Menu item appended in the systray part of the navbar
*/
export class NightModeTheme extends Component {
    setup() {
        // Access the ORM service
        this.orm = useService('orm')
        // Initialize the component state
        this.state = useState({checked: false})
        // Reference to the root element
        this.root = useRef('root')
        // Access to the block and unblock functions from the UI service
        const {block, unblock} = this.env.services.ui
        this.block = block;
        this.unblock = unblock;
        // Fetch the initial night mode state when the component will start
        onWillStart(async () =>
            this.state.checked = await this.orm.call('res.users', 'get_active', [])
        )
        // When the component is mounted, set the initial night mode state and enable DarkReader if it's active
        onMounted(async () => {
            this.root.el.querySelector('#cy_check').checked = this.state.checked;
            if (this.state.checked) {
                DarkReader.enable();
            }
        })
    }

    /**
     * Handle the click event when toggling night mode.
     * @param {Event} event - The click event.
     */
    async onToggleClick() {
        let toggleValue = this.root.el.querySelector('#cy_check')
        toggleValue.checked = !toggleValue.checked
        let backend = await this.orm.call('res.users', 'toggle_night_mode', [toggleValue.checked])
        this.state.checked = backend
        backend ? DarkReader.enable() : DarkReader.disable();
    }
}
// Set the template for the NightModeTheme component
NightModeTheme.template = 'systrayThemeMenu';
export const NightModeSystrayItem = {
    Component: NightModeTheme,
};
// Add the NightModeTheme to the systray category
registry.category("systray").add("NightModeTheme", NightModeSystrayItem, {sequence: 0});