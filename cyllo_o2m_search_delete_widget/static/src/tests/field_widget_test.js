/** @odoo-module **/

import { click, dragAndDrop, getNodesTextContent, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module('section_and_note', (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                invoice: {
                    fields: {
                        invoice_line_ids: {
                            string: "Lines",
                            type: 'one2many',
                            relation: 'invoice_line',
                            relation_field: 'invoice_id'
                        },
                    },
                    records: [
                        {id: 1, invoice_line_ids: [1, 2]},
                    ],
                },
                invoice_line: {
                    fields: {
                        sequence: { string: "sequence", type: "integer", sortable: true },
                        display_type: {
                            string: 'Type',
                            type: 'selection',
                            selection: [['line_section', "Section"], ['line_note', "Note"]]
                        },
                        invoice_id: {
                            string: "Invoice",
                            type: 'many2one',
                            relation: 'invoice'
                        },
                    },
                    records: [
                        {id: 1, display_type: false, invoice_id: 1,},
                        {id: 2, display_type: 'line_section', invoice_id: 1},
                    ]
                },
            },
        };
        setupViewRegistries();
    });
    QUnit.test('correct display of O2mSearchDelete widget', async (assert) => {
        await makeView({
            type: 'form',
            resModel: 'invoice',
            serverData,
            arch: `
                <form>
                    <field name="invoice_line_ids" widget="one2many_search_delete">
                        <tree editable="bottom">
                            <field name="sequence" />
                            <field name="display_type" column_invisible="1"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        // Ensure that the widget is correctly initialized
        const o2mSearchDeleteWidget = document.querySelector('.o_field_widget[name="invoice_line_ids"]');
        assert.ok(o2mSearchDeleteWidget, 'O2mSearchDelete widget is present');
        assert.doesNotHaveClass(target.querySelector('tr.o_data_row:nth-child(1'), 'o_is_line_section',
            "should not have a some text");
    });
});