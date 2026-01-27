/** @odoo-module **/

import { useState, Component, xml, useEffect, useRef, onMounted, onWillStart } from '@odoo/owl';
import { patch } from "@web/core/utils/patch";
import { useBus, useService } from "@web/core/utils/hooks";
import { MenuSideBar } from '@cyllo_base/js/menu_sidebar';

patch(MenuSideBar.prototype, {
    setup() {
        super.setup();
        this.websiteCustomMenus = useService('website_custom_menus');
        (function() {
            const pushState = history.pushState;
            const replaceState = history.replaceState;

            function fireUrlChange() {
                window.dispatchEvent(new Event('urlchange'));
            }

            history.pushState = function(...args) {
                pushState.apply(history, args);
                fireUrlChange();
            };

            history.replaceState = function(...args) {
                replaceState.apply(history, args);
                fireUrlChange();
            };

            window.addEventListener('popstate', fireUrlChange);
        })();

        window.addEventListener('urlchange', async () => {
            this.state.menus = await this.detectWebsiteContext() ? this.getMenus() : this.getMenus()
        });

        useEffect(() => {
            (async () => {
                this.state.menus = await this.detectWebsiteContext() ? this.getMenus() : this.getMenus()
                if (this.resetOptions.condition) {
                    await this.menuService.reload()
                    this.resetOptions.condition = false;
                }
            })()
        }, () => [this.state.isApp, this.resetOptions.actionId])

        onMounted(async () => {
            this.mainMenuVisibility = (localStorage.getItem('mainMenuVisibility') !== null) ? (localStorage.getItem('mainMenuVisibility') === 'true') : true;
            if (!this.isSidebarOnBoolean) {
                this.cyLeftSidebar.el.parentElement.classList.add('menuListFixed')
            }
            this.state.menus = await this.detectWebsiteContext() ? this.getMenus() : this.getMenus()
        });
    },

    async detectWebsiteContext() {
        let isWebsite = false;
        const path = window.location?.pathname;
        if (!path.startsWith('/web')) isWebsite = true;
        return isWebsite;
    },

    async onClickMenu(id, isApp, name = false) {
        super.onClickMenu(id, isApp, name);
        this.state.menus = await this.detectWebsiteContext() ? this.getMenus() : this.getMenus()
    },

    get currentAppSections() {
        const currentAppSections = this.currentApp?.id
            ? this.menuService.getMenuAsTree(this.currentApp.id)?.childrenTree || []
            : [];

        if (this.currentApp?.xmlid === 'website.menu_website_configuration') {
            return this.websiteCustomMenus
                .addCustomMenus(currentAppSections)
                .filter(section => section.childrenTree?.length);
        }
        return currentAppSections;
    }

});