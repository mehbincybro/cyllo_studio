/** @odoo-module **/

import { actionService } from "@web/webclient/actions/action_service";
import { registry } from "@web/core/registry";

/**
 * Global Support for 'workflow' Button Type
 * 
 * This patch overrides the action service to natively support buttons with type="workflow".
 * It intercepts the doActionButton call and treats it as an 'object' type call
 * so it can trigger the custom Python methods injected by Cyllo Workflow Automation.
 */
const originalActionService = actionService;

const patchedActionService = {
    ...originalActionService,
    start(env) {
        console.log("Cyllo Workflow: Global Action Service Started");
        const actionManager = originalActionService.start(env);
        const originalDoActionButton = actionManager.doActionButton;

        actionManager.doActionButton = async function (params) {
            console.log("Cyllo Workflow: Global Intercept", params);
            if (params.type === "workflow") {
                console.log("Cyllo Workflow: Executing workflow button click as object action");
                params = { ...params, type: "object" };
            }
            return originalDoActionButton.call(this, params);
        };

        return actionManager;
    },
};

registry.category("services").add("action", patchedActionService, { force: true });
