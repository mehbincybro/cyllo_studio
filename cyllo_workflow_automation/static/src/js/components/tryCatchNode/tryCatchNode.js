/** @odoo-module */

const { useState, onWillStart } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";

/**
 * TryCatchNode — Scope node that wraps workflow branches in a Python try/except.
 *
 * Provides:
 *   - Settings tab: error handling mode + exception filter checkboxes
 *   - TRY tab: info panel explaining the TRY port + available error variables
 *   - CATCH tab: table of injected error context variables
 *
 * Code generation is handled server-side in WorkAuto._generate_try_catch_code().
 * This component simply saves the configuration (mode, filters) to node.struct.
 */
export class TryCatchNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.uiState = useState({
            activeTab: 'settings',
        });
    }

    // ── Dropdown options ─────────────────────────────────────────────────────

    get errorHandlingOptions() {
        return [
            { value: 'catch',               label: 'Execute Catch Branch' },
            { value: 'catch_then_continue', label: 'Execute Catch Branch Then Continue' },
            { value: 'continue',            label: 'Continue Workflow (silent)' },
            { value: 'stop',                label: 'Stop Workflow (re-raise error)' },
        ];
    }

    get catchFilterOptions() {
        return [
            { value: 'ValidationError', label: '🔴 ValidationError' },
            { value: 'AccessError',     label: '🔒 AccessError' },
            { value: 'UserError',       label: '⚠️ UserError' },
            { value: 'MissingError',    label: '❓ MissingError' },
            { value: 'Exception',       label: '🌐 Any Other Exception' },
        ];
    }

    // ── Error filter helpers ──────────────────────────────────────────────────

    get activeFilters() {
        return Array.isArray(this.fieldState.tc_catch_filters)
            ? this.fieldState.tc_catch_filters
            : [];
    }

    isCatchFilterSelected(value) {
        return this.activeFilters.includes(value);
    }

    toggleCatchFilter(value) {
        const current = this.activeFilters;
        this.fieldState.tc_catch_filters = current.includes(value)
            ? current.filter(v => v !== value)
            : [...current, value];
    }

    get filterSummary() {
        const f = this.activeFilters;
        if (!f.length) return 'All exceptions (catch-all)';
        return f.join(', ');
    }

    // ── Code generation (empty — server-side generates the real code) ─────────

    generateCode() {
        // The Python try/except block is built dynamically by the workflow parser
        // in workflow_automation.js (buildFlowLines). We return a dummy string
        // here so the node passes frontend "is configured" validation.
        return '# Try/Catch Scope';
    }

    // ── Validation ────────────────────────────────────────────────────────────

    validateForm() {
        if (!this.fieldState.label) {
            return { isValid: false, errors: { label: 'Label is required.' } };
        }
        return { isValid: true };
    }
}

TryCatchNode.template = "TryCatchNode";
TryCatchNode.components = { ...ConfigurationBase.components };
