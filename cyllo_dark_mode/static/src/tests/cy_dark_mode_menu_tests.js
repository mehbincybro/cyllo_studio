/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { Command } from "@mail/../tests/helpers/command";
import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";
import { browser } from "@web/core/browser/browser";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, triggerEvents } from "@web/../tests/utils";

QUnit.module("dark mode menu");

QUnit.test("should have dark mode menu button in systray", async () => {
    await start();
    await contains(".o_menu_systray i[id='fa-icon']");
    await contains(".fa-sun-o");
});

QUnit.test("rendering with dark mode", async (assert) => {
    patchBrowserNotification("default");
    await start();
    await click(".o_menu_systray i[id='fa-icon']");
    await assert.ok(getMenuItemTexts(target));
});