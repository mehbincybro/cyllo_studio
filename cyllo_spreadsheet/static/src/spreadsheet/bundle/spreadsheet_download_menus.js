/** @odoo-module **/
import {_lt } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
const {Spreadsheet, Model} = spreadsheet;
const { topbarMenuRegistry } = spreadsheet.registries;
    // Function triggers while clicking the download button from a sheet
    topbarMenuRegistry.addChild("Download", ["file"], {
    name: _lt("Download"),
    execute: (env) => env.download_sheet(env),
    icon: "cyllo_spreadsheet.Download",
});
