/** @odoo-module **/
import { SwitchLanguageMenu } from "@cyllo_language_switch/js/switch_language";
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
let target;
let serverData;

QUnit.module("Language Switch", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                'res.lang': {
                    fields: {
                        name: { string: 'Name', type: 'char' },
                        active :{ string: 'Active', type: 'boolean' },
                    },
                    records: [
                        {
                            id: 1,
                            name : 'English (US)',
                            active: true,
                        },
                        {
                            id : 4,
                            name : 'Arabic (Syria) / الْعَرَبيّة',
                            active : true,
                        }
                    ],
                },
            },
        };
        setupViewRegistries();
    });
    QUnit.test("active languages",
    async function (assert) {
        await createSwitchLanguageMenu();
        const form = await makeView({
            type: "form",
            resModel: "res.lang",
            serverData,
            arch: `
            <form>
                <field name="name" class="lang_name"/>
                <field name="active" class="active_lang"/>
            </form>`,
            resId: 1,
        });
        const ActiveLangs = serverData.models["res.lang"].records.length
        assert.strictEqual(ActiveLangs, 2,"Two or more active languages are there");
        if (ActiveLangs >=2){
            const divElement = document.createElement('div');
            divElement.innerText = $('.lang_name')[0].innerText
            target.append(divElement)
        }
        var currentLanguage = $('.lang_name')[0].innerText
        assert.strictEqual(languageMenu, currentLanguage,"Current user language displayed")
    });
});
