/** @odoo-module **/
import { registry } from "@web/core/registry";

/**
 * Studio Reload Action
 * Triggers a soft reload of the Odoo Studio environment.
 * Clears relevant caches and reloads actions without a full page refresh.
 *
 * @param {Object} env - The Owl environment object containing services and bus
 * @param {Object} action - The action payload (not used in this function)
 */
async function studioReload(env, action) {
     // Clear any cached data in the environment
     env.bus.trigger("CLEAR-CACHES");

     // Perform a soft reload of the web client
     env.services.action.doAction('soft_reload')
}
// Register the action in Odoo registry
registry.category("actions").add("studio_reload", studioReload);
