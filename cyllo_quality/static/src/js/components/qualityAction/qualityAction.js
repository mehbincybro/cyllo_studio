/** @odoo-module **/
import { useService  } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, markup, useState, onWillStart } from  "@odoo/owl";
import { ValidateQualityAction } from "@cyllo_quality/js/components/validateQualityAction/validateQualityAction";

export class QualityAction extends Component {
    static components = { ValidateQualityAction }
    setup() {
        this.dialog = useService("dialog");
        console.log('QualityAction',this)
        this.state = useState({
            addNote: false,
            isPass: undefined,
        })
        onWillStart(() => {
            const {status} = this.props.action
            this.setQcStatus(status)
        })
    }

    setQcStatus(status) {
        if (["fail", "pass"].includes(status)) {
            this.state.isPass = status === "pass"
        }
    }

    async onClickQualityAction(){
    console.log(this.props.action.inspection_action_id[1],'eeeeeee')
       this.props.handleModalToggle(true)
       if (this.state.isPass === undefined) {

           await this.dialog.add(ValidateQualityAction, {
                 title: this.props.quality_check.control_type == 'quantity'
                        ? _t(`Quality Check of ${this.props.quality_check.product_id[1]} for ${this.props.action.inspection_action_id[1]} - ${this.props.quality_check.quantity} Units`)
                        : this.props.quality_check.product_id
                        ? _t(`Quality Check of ${this.props.quality_check.product_id[1]} for ${this.props.action.inspection_action_id[1]} `)
                        : _t(`Quality Check for ${this.props.action.inspection_action_id[1]}`),
                 quality_check: this.props.quality_check,
                 quality_check_action : this.props.action,
                 handleModalClose: this.handleModalClose.bind(this),
           })
       }
    }

    handleModalClose(response){
        this.props.handleModalToggle(false)
        this.setQcStatus(response.status)
    }

}
QualityAction.template = "QualityAction";
