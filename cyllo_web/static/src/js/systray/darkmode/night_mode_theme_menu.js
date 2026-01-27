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
        this.env.bus.addEventListener("TOGGLE_DARK_MODE", async () => {
            await this.onToggleClick()
        })
        this.orm = useService('orm')
        // Initialize the component state
        this.state = useState({checked: false})
        // Reference to the root element
        this.root = useRef('root')
        this.refs = useRef('iconContainer')
        this.backend = ''
        // Access to the block and unblock functions from the UI service
        const {block, unblock} = this.env.services.ui
        this.block = block;
        this.unblock = unblock;
        this.darkReader = false
        // Fetch the initial night mode state when the component will start
        onWillStart(async () =>
            this.state.checked = await this.orm.call('res.users', 'get_active', [])
        )
        // When the component is mounted, set the initial night mode state and enable DarkReader if it's active
        onMounted(() => {
    this.root.el.querySelector('#cy_check').checked = this.state.checked;

    if (this.state.checked) {
        DarkReader.enable();
        this.updateIcons(true);
    } else {
        this.updateIcons(false);
    }

    this.env.bus.addEventListener("DARK_MODE_UPDATED", (event) => {
        this.state.checked = event.detail;
        this.updateIcons(event.detail);
    });
});

            }


    getSunIcon() {
        return `
            <svg height="22" width="32" fill="none" stroke="#dddad5" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 1v4" />
                  <path d="M12 19v4" />
                  <path d="M4.22 4.22L6.34 6.34" />
                  <path d="M19.78 19.78L17.66 17.66" />
                  <path d="M1 12h4" />
                  <path d="M19 12h4" />
                  <path d="M4.22 19.78L6.34 17.66" />
                  <path d="M19.78 4.22L17.66 6.34" />
                  <path d="M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
            </svg>
        `;
    }

    getMoonIcon() {
        return `
            <svg height="20" width="32" fill="none" stroke="#121212" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path clip-rule="evenodd"
                      d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z"
                      fill-rule="evenodd">
                </path>
            </svg>
        `;
    }

    updateIcons(isDark) {
        const icon1 = this.refs.el;
        const iconHtml = isDark ? this.getSunIcon() : this.getMoonIcon();
        if (icon1) icon1.innerHTML = iconHtml;
    }

    /**
     * Handle the click event when toggling night mode.
     * @param {Event} event - The click event.
     */
    async onToggleClick() {
    this.state.checked = !this.state.checked;

    const backend = await this.orm.call('res.users', 'toggle_night_mode', [this.state.checked]);
    localStorage.setItem('darkMode', this.state.checked);

    if (backend) {
        this.backend = 'true';
        DarkReader.enable();
    } else {
        this.backend = 'false';
        DarkReader.disable();
    }

    this.env.bus.trigger('DARK_MODE_UPDATED', this.state.checked);
    this.updateIcons(this.state.checked);
}


}
// Set the template for the NightModeTheme component
NightModeTheme.template = 'NightModeTheme';
export const NightModeSystrayItem = {
    Component: NightModeTheme,
};
// Add the NightModeTheme to the systray category
registry.category("systray").add("NightModeTheme", NightModeSystrayItem, {sequence: 0});