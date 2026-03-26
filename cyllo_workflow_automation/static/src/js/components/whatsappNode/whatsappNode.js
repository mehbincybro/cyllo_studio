/** @odoo-module */
const { useState, onWillStart } = owl;
import { _t } from "@web/core/l10n/translation";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { TypeToggler } from "../Assists/typeToggler/TypeToggler";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";

export class WhatsAppNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.waState = useState({
            isInstalled: false,
            checking: true,
        });

        onWillStart(async () => {
            await this._checkWhatsAppInstalled();
        });
    }

    async _checkWhatsAppInstalled() {
        try {
            const count = await this.orm.searchCount('ir.module.module', [
                ['name', '=', 'cyllo_whatsapp'],
                ['state', '=', 'installed'],
            ]);
            this.waState.isInstalled = count > 0;
        } catch {
            this.waState.isInstalled = false;
        } finally {
            this.waState.checking = false;
        }
    }

    get getLabel() {
        return this.fieldState.label || "";
    }

    setLabel(ev) {
        const label = ev.target ? ev.target.value : ev;
        this.fieldState.label = label;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId: this.props.id });
    }

    get getTogglerOptions() {
        return [
            { label: "Template", value: true },
            { label: "Free-form", value: false },
        ];
    }

    get isTemplateMode() {
        return this.fieldState.wa_is_template !== false;
    }

    updateMode(option) {
        this.fieldState.wa_is_template = option.value;
    }

    get getRecordVariables() {
        return (this.props.variables || [])
            .filter((v) => v.variable_type === 'record' && v.modelId)
            .map((v) => ({ value: v.id, label: v.variable_name }));
    }

    get getSelectedRecord() {
        return this.fieldState.wa_record?.value || "";
    }

    async updateRecord(variableId) {
        this.fieldState.wa_record = { value: variableId };
        this.fieldState.wa_partner_source = this.fieldState.wa_partner_source || 'customer';
        this.fieldState.wa_partner_path = variableId ? {
            record: variableId,
            path: 'partner_id',
            pathValue: 'partner_id.id',
        } : null;
    }

    get getPartnerSourceOptions() {
        return [
            { label: "Customer", value: 'customer' },
            { label: "Other", value: 'other' },
        ];
    }

    get getPartnerSource() {
        return this.fieldState.wa_partner_source || 'customer';
    }

    updatePartnerSource(value) {
        this.fieldState.wa_partner_source = value;
        if (value === 'customer') {
            this.fieldState.wa_other_partner = null;
        }
    }

    get getOtherPartnerName() {
        return this.fieldState.wa_other_partner?.name || "";
    }

    getOtherPartnerDomain() {
        return [
            ['whatsapp_number', '!=', false],
            ['whatsapp_number', '!=', ''],
        ];
    }

    onSelectOtherPartner(selection) {
        this.fieldState.wa_other_partner = {
            id: selection[0]?.id || false,
            name: selection[0]?.display_name || "",
        };
    }

    get getTemplateName() {
        return this.fieldState.wa_template?.name || "";
    }

    getTemplateDomain() {
        return [['state', '=', 'approved']];
    }

    onSelectTemplate(selection) {
        this.fieldState.wa_template = {
            id: selection[0]?.id || false,
            name: selection[0]?.display_name || "",
        };
    }

    get getFreeMessage() {
        return this.fieldState.wa_free_message || "";
    }

    setFreeMessage(ev) {
        this.fieldState.wa_free_message = ev.target ? ev.target.value : ev;
    }

    generateCode() {
        const {
            wa_record,
            wa_is_template,
            wa_template,
            wa_partner_source,
            wa_other_partner,
            wa_free_message,
        } = this.fieldState;

        if (!wa_record?.value) {
            return "# WhatsApp node: no record variable selected";
        }

        const variable = (this.props.variables || []).find((v) => v.id === wa_record.value);
        if (!variable) {
            return "# WhatsApp node: record variable not found";
        }

        this.updateUsedVariables(wa_record.value);
        const recordVarName = variable.variable_name;
        const templateId = wa_is_template !== false && wa_template?.id ? wa_template.id : 'None';
        const freeMsg = JSON.stringify(wa_free_message || "");
        const partnerPath = wa_partner_source === 'other' ? 'None' : JSON.stringify('partner_id');
        const partnerId = wa_partner_source === 'other' && wa_other_partner?.id ? wa_other_partner.id : 'None';

        return [
            `env['wa.workflow.executor'].send_workflow_whatsapp(`,
            `    ${recordVarName},`,
            `    ${partnerPath},`,
            `    template_id=${templateId},`,
            `    free_message=${templateId === 'None' ? freeMsg : 'None'},`,
            `    partner_id=${partnerId},`,
            `)`,
        ].join('\n');
    }

    validateForm() {
        const {
            wa_record,
            wa_is_template,
            wa_template,
            wa_partner_source,
            wa_other_partner,
            wa_free_message,
            label,
        } = this.fieldState;
        const errors = {};

        if (!label?.trim()) {
            errors.label = _t("Label is required.");
        }
        if (!wa_record?.value) {
            errors.wa_record = _t("Please select a record variable.");
        }
        if (wa_partner_source === 'other' && !wa_other_partner?.id) {
            errors.wa_other_partner = _t("Please select a contact with a WhatsApp number.");
        }
        if (wa_is_template !== false) {
            if (!wa_template?.id) {
                errors.wa_template = _t("Please select a WhatsApp template.");
            }
        } else if (!wa_free_message?.trim()) {
            errors.wa_free_message = _t("Please enter a message text.");
        }

        return Object.keys(errors).length
            ? { isValid: false, errors }
            : { isValid: true };
    }
}

WhatsAppNode.template = "WhatsAppNode";
WhatsAppNode.components = {
    ...ConfigurationBase.components,
    Many2XAutocomplete,
    TypeToggler,
    CustomDropdown,
};
