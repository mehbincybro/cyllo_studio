/** @odoo-module **/
import {SettingsFormCompiler} from '@web/webclient/settings_form_view/settings_form_compiler'
import {append, createElement} from "@web/core/utils/xml";
import {toStringExpression} from "@web/views/utils";
import {patch} from "@web/core/utils/patch";

const Icons = {
    'stock': 'cyllo_base/static/src/icons/inventory.png',
    'event': 'cyllo_base/static/src/icons/events.png',
    'crm': 'cyllo_base/static/src/icons/crm.png',
    'sale_management': 'cyllo_base/static/src/icons/sales.png',
    'calendar': 'cyllo_base/static/src/icons/calendar.png',
    'website': 'cyllo_base/static/src/icons/website.png',
    'website_slides': 'cyllo_base/static/src/icons/eLearning.png',
    'purchase': 'cyllo_base/static/src/icons/purchase.png',
    'mrp': 'cyllo_base/static/src/icons/manufacturing.png',
    'maintenance': 'cyllo_base/static/src/icons/maintenance.png',
    'account': 'cyllo_base/static/src/icons/invoicing.png',
    'project': 'cyllo_base/static/src/icons/project.png',
    'hr_timesheet': 'cyllo_base/static/src/icons/task-log.png',
    'mass_mailing': 'cyllo_base/static/src/icons/email-marketing.png',
    'hr': 'cyllo_base/static/src/icons/employee.png',
    'hr_recruitment': 'cyllo_base/static/src/icons/recruitment.png',
    'hr_attendance': 'cyllo_base/static/src/icons/attendance.png',
    'hr_expense': 'cyllo_base/static/src/icons/expenses.png',
    'fleet': 'cyllo_base/static/src/icons/fleet.png',
    'lunch': 'cyllo_base/static/src/icons/lunch.png',
    'point_of_sale': 'cyllo_base/static/src/icons/pos.png',
    'general_settings': 'cyllo_base/static/src/icons/cyllo_setting.png'
} // todo: add icons for cyllo products

patch(SettingsFormCompiler.prototype, {
    setup() {
        super.setup();
    },
    compileApp(el, params) {
        if (el.getAttribute("notApp") === "1") {
            //An app noted with notApp="1" is not rendered.

            //This hack is used when a technical module defines settings, and we don't want to render
            //the settings until the corresponding app is not installed.

            // For example, when installing the module website_sale, the module sale is also installed,
            // but we don't want to render its settings (notApp="1").
            // On the contrary, when sale_management is installed, the module sale is also installed
            // but in this case we want to see its settings (notApp="0").
            return;
        }
        const nameAttr = el.getAttribute("name");
        const path = Icons[nameAttr] || el.getAttribute("logo") || `/${nameAttr}/static/description/icon.png`;
        const module = {
            key: nameAttr,
            string: el.getAttribute("string"),
            imgurl: path
        };
        params.modules.push(module);
        const settingsApp = createElement("SettingsApp", {
            key: toStringExpression(module.key),
            string: toStringExpression(module.string || ""),
            imgurl: toStringExpression(module.imgurl),
            selectedTab: "settings.selectedTab",
            slots: "{}"
        });

        for (const child of el.children) {
            append(settingsApp, this.compileNode(child, params));
        }

        return settingsApp;
    }
})