
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useState } from "@odoo/owl";
import { WorkFlowAuto } from "@cyllo_workflow_automation/js/workflow_automation";

class WorkFlowAutoOverride extends WorkFlowAuto {

    setup() {
        super.setup();
        this.state = useState({
            // Base arrays expected by WorkFlowAuto
            nodeDetails: [],
            actions: [],

            // AI Chat state
            aiChatOpen: false,
            aiInput: "",
            aiMessages: [],
        });
    }

    settingModelState(data) {
    if (!data) return;
    this.state.modelState = data.modelState || [];
    }

    openAiChat() {
        this.state.aiChatOpen = !this.state.aiChatOpen;
        console.log('AI Chat Open:', this.state.aiChatOpen);
    }

    async sendAiMessage() {
        if (!this.state.aiInput) return;

        const userId = this.state.aiMessages.length;
        this.state.aiMessages.push({ from: 'user', text: this.state.aiInput, id: userId });

        const aiResponseId = userId + 1;
        let aiData;

        try {
            const result = await this.orm.call('chat.bot', 'my_python_method', [this.state.aiInput]);
            aiData = typeof result === 'string' ? JSON.parse(result) : result;
        } catch (e) {
            console.error('AI call failed:', e);
            this.state.aiMessages.push({ from: 'ai', text: 'AI call failed', id: aiResponseId });
            return;
        }

        if (!aiData?.object) {
            this.state.aiMessages.push({ from: 'ai', text: "No model returned by AI", id: aiResponseId });
            return;
        }

        const modelName = aiData.object.trim();
        const res = await this.orm.searchRead('ir.model', [['model', 'ilike', modelName]], ['id', 'display_name', 'model']);
        if (!res?.length) return;

        const modelId = res[0].id;
        const object = [{ id: modelId, display_name: res[0].display_name, model: res[0].model }];

        await this.onSelectPrimary(object || []);

        const action = aiData.trigger === 'On Create' ? '1' :
                       aiData.trigger === 'On Write'  ? '2' :
                       aiData.trigger === 'On Unlink' ? '3' : '';

        // Safe push: ensure nodeDetails exists
        this.state.nodeDetails = this.state.nodeDetails || [];
        await this.addNodeToDrawFlow(aiData.trigger || 'Trigger', 538, 340, res[0].display_name, modelId, action, 'trigger');

        if (aiData.conditions) {
            await this.addNodeToDrawFlow('Condition', 538, 400, res[0].display_name, modelId, null, null);
        }

        (aiData.actions || []).forEach((act, i) => {
            this.addNodeToDrawFlow(act?.type || 'Action', 800 + (i * 150), 400, res[0].display_name, modelId, null, null);
        });

        this.state.aiMessages.push({ from: 'ai', text: aiData.response || 'result', id: aiResponseId });
    }
}

WorkFlowAutoOverride.template = "client_action.automation_view";

registry.category("actions").add("automation_view", WorkFlowAutoOverride, { force: true });

