/** @odoo-module */
const { useState, onWillStart, useRef } = owl;
import { _t } from "@web/core/l10n/translation";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { TypeToggler } from "../Assists/typeToggler/TypeToggler";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";
import { useService } from "@web/core/utils/hooks";

export class WhatsAppNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.waState = useState({
            isInstalled: false,
            checking: true,
            uploadingFile: false,
        });
        this.fileInputRef = useRef("wa_file_input");

        onWillStart(async () => {
            await this._checkWhatsAppInstalled();
        });
    }

    async fetchData() {
        await super.fetchData();
        await this._normalizeAttachmentState();
    }

    async _normalizeAttachmentState() {
        const attachmentIds = this.fieldState.wa_static_attachment_ids || [];
        if (attachmentIds.length && typeof attachmentIds[0] !== "object") {
            const attachments = await this.orm.read("ir.attachment", attachmentIds, ["name"]);
            this.fieldState.wa_static_attachment_ids = attachments.map((attachment) => ({
                id: attachment.id,
                name: attachment.name,
            }));
        }

        const reportId = this.fieldState.wa_auto_report_id;
        if (typeof reportId === "number") {
            const [report] = await this.orm.read("ir.actions.report", [reportId], ["name"]);
            this.fieldState.wa_auto_report_id = report ? { id: report.id, name: report.name } : null;
        }
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
        const previousRecordId = this.fieldState.wa_record?.value;
        this.fieldState.wa_record = { value: variableId };
        this.fieldState.wa_partner_source = this.fieldState.wa_partner_source || 'customer';
        this.fieldState.wa_partner_path = variableId ? {
            record: variableId,
            path: 'partner_id',
            pathValue: 'partner_id.id',
        } : null;
        if (previousRecordId !== variableId) {
            this.fieldState.wa_auto_report_id = null;
        }
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

    get getAttachmentModeOptions() {
        return [
            { label: "No Attachment", value: 'none' },
            { label: "Static File(s)", value: 'static' },
            { label: "Auto-generate from Record", value: 'auto' },
        ];
    }

    get getAttachmentMode() {
        return this.fieldState.wa_attachment_mode || 'none';
    }

    updateAttachmentMode(value) {
        this.fieldState.wa_attachment_mode = value || 'none';
        if (value !== 'static') {
            this.fieldState.wa_static_attachment_ids = this.fieldState.wa_static_attachment_ids || [];
        }
        if (value !== 'auto') {
            this.fieldState.wa_auto_report_id = null;
        }
    }

    get getStaticAttachments() {
        return (this.fieldState.wa_static_attachment_ids || []).map((attachment) => {
            if (Array.isArray(attachment)) {
                return { id: attachment[0], name: attachment[1] };
            }
            if (typeof attachment === "number") {
                return { id: attachment, name: `Attachment ${attachment}` };
            }
            return attachment;
        });
    }

    async onFileInputChange(ev) {
        const file = ev.target.files?.[0];
        if (!file) {
            return;
        }

        this.waState.uploadingFile = true;
        const reader = new FileReader();
        reader.onload = async (loadEvent) => {
            const base64Data = loadEvent.target?.result?.split(",")[1];
            if (!base64Data) {
                this.waState.uploadingFile = false;
                return;
            }
            try {
                const result = await this.rpc("/cyllo_workflow/upload_wa_attachment", {
                    name: file.name,
                    data: base64Data,
                    mimetype: file.type || 'application/octet-stream',
                    node_struct_id: this.props.nodeId || null,
                });
                this.fieldState.wa_static_attachment_ids = [
                    ...(this.fieldState.wa_static_attachment_ids || []),
                    { id: result.id, name: result.name },
                ];
            } catch (error) {
                console.error("WA attachment upload failed", error);
            } finally {
                this.waState.uploadingFile = false;
                if (this.fileInputRef.el) {
                    this.fileInputRef.el.value = "";
                }
            }
        };
        reader.readAsDataURL(file);
    }

    openFilePicker() {
        this.fileInputRef.el?.click();
    }

    removeStaticAttachment(attachmentId) {
        this.fieldState.wa_static_attachment_ids = this.getStaticAttachments.filter(
            (attachment) => attachment.id !== attachmentId
        );
    }

    get getAutoReportName() {
        return this.fieldState.wa_auto_report_id?.name || "";
    }

    getAutoReportDomain() {
        const variableId = this.fieldState.wa_record?.value;
        if (!variableId) {
            return [];
        }
        const variable = (this.props.variables || []).find((item) => item.id === variableId);
        if (!variable?.modelName) {
            return [];
        }
        return [
            ['model', '=', variable.modelName],
            ['report_type', '=', 'qweb-pdf'],
        ];
    }

    onSelectAutoReport(selection) {
        this.fieldState.wa_auto_report_id = selection[0] ? {
            id: selection[0].id,
            name: selection[0].display_name || selection[0].name || "",
        } : null;
    }

    generateCode() {
        const {
            wa_record,
            wa_is_template,
            wa_template,
            wa_partner_source,
            wa_other_partner,
            wa_free_message,
            wa_attachment_mode,
            wa_static_attachment_ids,
            wa_auto_report_id,
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
        const attachmentMode = JSON.stringify(wa_attachment_mode || 'none');
        const staticAttachmentIds = (wa_static_attachment_ids || [])
            .map((attachment) => Array.isArray(attachment) ? attachment[0] : attachment?.id || attachment)
            .filter(Boolean);
        const staticAttachmentIdsCode = staticAttachmentIds.length
            ? JSON.stringify(staticAttachmentIds)
            : 'None';
        const autoReportId = wa_auto_report_id?.id || 'None';

        return [
            `env['wa.workflow.executor'].send_workflow_whatsapp(`,
            `    ${recordVarName},`,
            `    ${partnerPath},`,
            `    template_id=${templateId},`,
            `    free_message=${templateId === 'None' ? freeMsg : 'None'},`,
            `    partner_id=${partnerId},`,
            `    attachment_mode=${attachmentMode},`,
            `    static_attachment_ids=${staticAttachmentIdsCode},`,
            `    auto_report_id=${autoReportId},`,
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
            wa_attachment_mode,
            wa_auto_report_id,
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
        if (wa_attachment_mode === 'auto') {
            if (!wa_record?.value) {
                errors.wa_auto_report_id = _t("Please select a record variable first.");
            } else if (!wa_auto_report_id?.id) {
                errors.wa_auto_report_id = _t("Please select a report to auto-generate.");
            }
        }
        if (wa_attachment_mode === 'static' && !(this.fieldState.wa_static_attachment_ids || []).length) {
            errors.wa_static_attachment_ids = _t("Please upload at least one attachment.");
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
