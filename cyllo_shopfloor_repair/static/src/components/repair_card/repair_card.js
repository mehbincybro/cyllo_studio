/** @odoo-module */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RepairCard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async startRepair() {
        if (this.props.activeEmployeeId) {
            await this.orm.write("repair.order", [this.props.record.id], {
                operator_ids: [[4, this.props.activeEmployeeId]]
            });
        }
        await this.orm.call("repair.order", "action_repair_start", [this.props.record.id]);
        this.props.onUpdate();
    }

    async stopRepair() {
        const result = await this.orm.call("repair.order", "action_repair_end", [this.props.record.id]);
        if (result && typeof result === "object" && result.type) {
            this.action.doAction(result, {
                onClose: () => {
                    this.props.onUpdate();
                }
            });
        } else {
            this.props.onUpdate();
        }
    }

    async editRepairLine() {
        this.action.doAction("cyllo_shopfloor_repair.action_edit_repair_line_wizard", {
            additionalContext: { default_repair_id: this.props.record.id },
            onClose: () => {
                this.props.onUpdate();
            },
        });
    }

    async editNotes() {
        const action = await this.orm.call("repair.order", "action_show_repair_notes", [this.props.record.id]);
        this.action.doAction(action, {
            onClose: () => {
                this.props.onUpdate();
            }
        });
    }

    openRepairOrder() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "repair.order",
            res_id: this.props.record.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

RepairCard.template = "repair_floor.RepairCard";
RepairCard.props = {
    record: Object,
    onUpdate: Function,
    activeEmployeeId: { type: Number, optional: true },
};