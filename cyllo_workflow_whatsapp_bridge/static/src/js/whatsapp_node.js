/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { icons } from "@cyllo_workflow_automation/js/icons";
import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";
import { ModelComponent } from "@cyllo_workflow_automation/js/workflow_nodes";

icons.WhatsApp = "cyllo_whatsapp/static/description/whatsapp_icon.svg";

const originalOpenConfigModal = ModelComponent.prototype.openConfigModal;
const originalAddNodeToDrawFlow = WorkFlowAuto.prototype.addNodeToDrawFlow;

const whatsappFields = [
    "label",
    "model_id",
    "whatsapp_record",
    "whatsapp_template",
    "whatsapp_partner_ids",
    "whatsapp_isTemplate",
    "whatsapp_message",
];

export class WhatsAppNodeDialog extends Component {
    static template = "cyllo_workflow_whatsapp_bridge.WhatsAppNodeDialog";
    static components = { Dialog, Many2XAutocomplete };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            label: "",
            whatsapp_record: null,
            whatsapp_template: { id: false, name: "" },
            whatsapp_partner_ids: { id: false, name: "" },
            whatsapp_isTemplate: true,
            whatsapp_message: "",
            model_id: false,
        });

        onWillStart(async () => {
            const [nodeData] = await this.orm.read("node.struct", [this.props.id], whatsappFields);
            if (!nodeData) {
                return;
            }
            this.state.label = nodeData.label || "";
            this.state.model_id = nodeData.model_id ? nodeData.model_id[0] : false;
            this.state.whatsapp_record = nodeData.whatsapp_record || null;
            this.state.whatsapp_template = nodeData.whatsapp_template || { id: false, name: "" };
            this.state.whatsapp_partner_ids = nodeData.whatsapp_partner_ids || { id: false, name: "" };
            this.state.whatsapp_isTemplate =
                nodeData.whatsapp_isTemplate === false ? false : true;
            this.state.whatsapp_message = nodeData.whatsapp_message || "";
        });
    }

    get recordOptions() {
        return (this.props.variables || []).filter(
            (variable) => variable.variable_type === "record" && variable.modelId
        );
    }

    get selectedRecordValue() {
        return this.state.whatsapp_record?.value || "";
    }

    get templateDomain() {
        const selected = this.recordOptions.find(
            (variable) => variable.id === this.state.whatsapp_record?.value
        );
        return selected?.modelId ? [["model_id", "=", selected.modelId]] : [];
    }

    getPartnerDomain() {
        return [];
    }

    getTemplateDomain() {
        return this.templateDomain;
    }

    get selectedTemplateName() {
        return this.state.whatsapp_template?.name || "";
    }

    get selectedPartnerName() {
        return this.state.whatsapp_partner_ids?.name || "";
    }
    onChangeMode(ev) {
        this.state.whatsapp_isTemplate = ev.target.value === "template";
    }

    onChangeLabel(ev) {
        this.state.label = ev.target.value;
    }

    onChangeMessage(ev) {
        this.state.whatsapp_message = ev.target.value;
    }

    onChangeRecord(ev) {
        const selected = this.recordOptions.find((variable) => variable.id === ev.target.value);
        this.state.whatsapp_record = selected
            ? { value: selected.id, label: selected.variable_name }
            : null;
        this.state.whatsapp_template = { id: false, name: "" };
    }

    onSelectTemplate(records) {
        const record = records?.[0];
        this.state.whatsapp_template = {
            id: record?.id || false,
            name: record?.display_name || "",
        };
    }

    onSelectPartner(records) {
        const record = records?.[0];
        this.state.whatsapp_partner_ids = {
            id: record?.id || false,
            name: record?.display_name || "",
        };
    }

    get selectedRecordVariable() {
        return this.recordOptions.find(
            (variable) => variable.id === this.state.whatsapp_record?.value
        );
    }

    generateCode() {
        const recordVariable = this.selectedRecordVariable;
        const partnerId = this.state.whatsapp_partner_ids?.id;
        if (!recordVariable || !partnerId) {
            return "";
        }

        if (this.state.whatsapp_isTemplate) {
            return [
                `template = env["whatsapp.template"].browse(${this.state.whatsapp_template.id})`,
                `partner = env["res.partner"].browse(${partnerId})`,
                `if partner.whatsapp_number:`,
                `\ttemplate.action_send_template(${recordVariable.variable_name}, False, partner)`,
            ].join("\n");
        }

        const message = JSON.stringify(this.state.whatsapp_message || "");
        return [
            `partner = env["res.partner"].browse(${partnerId})`,
            `if partner.whatsapp_number:`,
            `\tchannel = env["whatsapp.channel"].search([("sender_id", "=", env.user.partner_id.id), ("partner_id", "=", partner.id)], limit=1)`,
            `\tif not channel:`,
            `\t\tchannel = env["whatsapp.channel"].create({"name": partner.name, "partner_id": partner.id, "sender_id": env.user.partner_id.id, "user_id": env.user.id})`,
            `\tenv["whatsapp.message"].send_whatsapp_message({"channel": {"id": channel.id}, "message": ${message}, "attachment": False, "image": False, "video": False})`,
        ].join("\n");
    }

    async onConfirm() {
        const errors = [];
        if (!this.state.label) {
            errors.push("Label is required.");
        }
        if (!this.state.whatsapp_record?.value) {
            errors.push("Record is required.");
        }
        if (!this.state.whatsapp_partner_ids?.id) {
            errors.push("Recipient is required.");
        }
        if (this.state.whatsapp_isTemplate && !this.state.whatsapp_template?.id) {
            errors.push("Template is required.");
        }
        if (!this.state.whatsapp_isTemplate && !this.state.whatsapp_message) {
            errors.push("Message is required.");
        }
        if (errors.length) {
            throw new Error(errors.join(" "));
        }

        const fieldState = {
            label: this.state.label,
            whatsapp_record: this.state.whatsapp_record,
            whatsapp_template: this.state.whatsapp_template,
            whatsapp_partner_ids: this.state.whatsapp_partner_ids,
            whatsapp_isTemplate: this.state.whatsapp_isTemplate,
            whatsapp_message: this.state.whatsapp_message,
        };
        await this.props.onConfirm(fieldState, this.generateCode(), {});
        this.props.close();
    }
}

patch(ModelComponent.prototype, {
    async openConfigModal() {
        if (this.props.name !== "WhatsApp") {
            return originalOpenConfigModal.call(this, ...arguments);
        }

        return this.dialogService.add(WhatsAppNodeDialog, {
            id: this.props.nodeId,
            name: this.props.name,
            variables: this.getVariables,
            onConfirm: this.onConfirm.bind(this),
        });
    },
});

patch(WorkFlowAuto.prototype, {
    async addNodeToDrawFlow(name, pos_x, pos_y, selectedValue, record, action, type, trigger_type) {
        if (name !== "WhatsApp") {
            return originalAddNodeToDrawFlow.call(
                this,
                name,
                pos_x,
                pos_y,
                selectedValue,
                record,
                action,
                type,
                trigger_type
            );
        }

        pos_x =
            pos_x * (this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom)) -
            (this.editor.precanvas.getBoundingClientRect().x *
                (this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom)));
        pos_y =
            pos_y * (this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom)) -
            (this.editor.precanvas.getBoundingClientRect().y *
                (this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom)));

        const nodeId = await this.createNodeInBackend(name, "action_to_do", trigger_type);
        const nodeData = {
            name,
            nodeId,
            model: [],
            primary_model_id: this.state.model_id,
            primary_model_name: this.state.model_name,
            updateImports: this.updateImportStatements.bind(this),
            work_auto_id: this.id,
            type: "action_to_do",
        };

        this.env.bus.trigger("UPDT-PRIMARY", { model_id: this.state.model_id });
        const uniqueIdentifier = `${name}__${nodeId}`;
        this.editor.registerNode(uniqueIdentifier, ModelComponent, nodeData, {});
        await this.editor.addNode(name, 1, 1, pos_x, pos_y, name, nodeData, uniqueIdentifier, 3);

        let { component, ref, props } = this.data;
        props = { ...props, ...nodeData };
        this.mountComponent(component, ref, props);
    },
});
