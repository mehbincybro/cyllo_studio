/** @odoo-module **/

import { fieldService } from "@web/core/field_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { getFixture, makeDeferred, mount, nextTick } from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");

function getModelInfo(resModel) {
    return {
        resModel,
        fieldDefs: serverData.models[resModel].fields,
    };
}

let serverData;
QUnit.module("Rental Service Test", {
    async beforeEach() {
        serverData = {
            models: {
                rentalOrder: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        age: { type: "integer", string: "Age" },
                        location_id: { type: "many2one", string: "Location", relation: "location" },
                        species: { type: "many2one", string: "Species", relation: "species" },
                        property_field: {
                            string: "Properties",
                            type: "properties",
                            definition_record: "species",
                            definition_record_field: "definitions",
                        },
                    },
                },
                species: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        definitions: { string: "Definitions", type: "properties_definition" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "new rentalOrder",
                            definitions: [
                                {
                                    name: "location_ids",
                                    string: "Locations",
                                    type: "many2many",
                                    relation: "location",
                                },
                            ],
                        },
                    ],
                },
            },
        };
        serviceRegistry.add("field", fieldService);
    },
});
QUnit.test("rental request test", async (assert) => {
    assert.expect(5);

    const mockRPC = (route) => {
        if (route.includes("fields_get")) {
            assert.step("fields_get");
            return Promise.reject("new error");
        }
    };

    const env = await makeTestEnv({ serverData, mockRPC });

    try {
        await env.services.field.loadFields("take.five");
    } catch (error) {
        assert.strictEqual(error, "new error");
    }
    try {
        await env.services.field.loadFields("take.five");
    } catch (error) {
        assert.strictEqual(error, "new error");
    }
    assert.verifySteps(["fields_get", "fields_get"]);
});
