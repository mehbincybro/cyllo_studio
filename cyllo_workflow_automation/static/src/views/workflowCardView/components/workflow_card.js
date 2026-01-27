/* @odoo-module */
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Component, onWillStart} from "@odoo/owl";
import {
    getImageSrcFromRecordInfo,
} from "@web/views/kanban/kanban_record";

export class WorkflowCard extends Component {
    setup() {
        this.state = {
            img: "",
            icon: ""
        }
        this.action = useService('action')
        this.orm = useService("orm");
        this.dialogService = useService('dialog')
        this.id = this.props.value.evalContext.id

        onWillStart(async () => {
            if (this.props.value.data.function_id) {
                this.state.icon = await this.orm.read('work.function', [this.props.value.data.function_id[0]], ['icon'])
            }
        });
    }

    get Image() {
        const {
            value: record,
            model
        } = this.props
        return getImageSrcFromRecordInfo(record, model, "image_1920", this.id) //Todo: Make image_1920 dynamic field
    }

    get WorkflowCard() {
        return this.props.value.data;
    }

    async openView() {
        if (this.props.model == "work.auto") {
            this.action.doAction({
                target: "current",
                tag: "automation_view",
                type: "ir.actions.client",
                context: {
                    rec_id: this.id
                }
            })
        }
    }

    onClickDelete() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Do you really want to Delete the record?"),
            confirm: (async () => {
                const domain = [['id', '!=', this.id]];
                this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "work.auto",
                    views: [[false, "workflowCard"], [false, "list"], [false, "form"]],
                    target: "main",
                    name: "Workflow Automation",
                    domain,
                    context: {delete_node_id: this.id}
                })
                await this.orm.unlink("work.auto", [this.id],)
            }),
        });
    }
}

WorkflowCard.template = `WorkflowCard`;