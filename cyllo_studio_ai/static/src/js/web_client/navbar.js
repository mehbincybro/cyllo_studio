/** @odoo-module **/
import {
    CylloNavBar
} from "@cyllo_studio/js/navbar/navbar";
import {
    patch
} from '@web/core/utils/patch';
import {
    useService
} from "@web/core/utils/hooks";
import {
    AIPage
} from '@cyllo_studio_ai/js/new_app_options/new_app_options';
import { useState, onRendered, onWillUpdateProps } from "@odoo/owl";


patch(CylloNavBar.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        onWillUpdateProps(async (nextProps) => {
            const hashParams = new URLSearchParams(window.location.hash.slice(1));
            const actionId = hashParams.get('action');
        });
    },
    createApp() {
        const currentUrl = window.location.href;
        this.dialogService.add(AIPage, {
            title: 'Cyllo Studio',
        })
    },

    handleClose() {
        const currentUrl = this.action.currentController.action.tag === "PromptDialog" ?
            new URL(localStorage.getItem('ExistingStudioPage')?.split(",")[0] || window.location.href) :
            localStorage.getItem('X2ManysStudioPage')?.split(",")[1] ?
            new URL(localStorage.getItem('X2ManysStudioPage').split(",")[0] || window.location.href) :
            new URL(window.location.href);
        const studio = currentUrl.searchParams.get("studio");
        if (studio === "1") {
            currentUrl.searchParams.delete("studio");
            history.replaceState(null, "", currentUrl.toString());
        }
        currentUrl.searchParams.set("studio", "");
        window.location.href = currentUrl.toString();
        setTimeout(() => window.location.reload(), 500);
    }
})
CylloNavBar.props = {
    ...CylloNavBar.props,
    isAI: { type: Boolean, optional: true },
};
