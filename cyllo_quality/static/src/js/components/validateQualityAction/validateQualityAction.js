/** @odoo-module */
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState, Component, markup, xml, useRef, onMounted, status } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class ValidateQualityAction extends Component {
    static components = { Dialog }
    static defaultProps = {
        handleModalClose: () => { },
    };
    setup() {

        this.orm = useService("orm");
        this.action = useService("action")
        this.qcInstruction = useRef('qcInstruction')
        this.notification = useService("notification");
        this.state = useState({
            addNote: false,
            qualityCheckNote: false,
            qcStatus: false,
            qcValue: false,
            checkValue: false,
            imageSrc: false
        })

        onMounted(() => {
            if (this.props.quality_check_action.instruction) {
                this.qcInstruction.el.addEventListener("click", (ev) => {
                    this.action.doAction({
                        type: 'ir.actions.client',
                        tag: 'quality_instruction_action',
                        target: 'new',
                        params: {
                            instruction: this.props.quality_check_action.instruction,
                        }
                    });
                });
            }
        })
    }

    addNote() {
        this.state.addNote = true
    }

    onImageChange(event) {
        const file = event.target.files[0];
        if (file) {
            const validImageTypes = ['image/jpeg', 'image/png', 'image/gif'];
            if (validImageTypes.includes(file.type)) {
                const reader = new FileReader();

                // Set the image preview once the file is read
                reader.onload = (e) => {
                    this.state.imageSrc = e.target.result;
                };

                // Read the image file as a data URL
                reader.readAsDataURL(file);
            } else {
                alert('Please upload a valid image file.');
            }
        } else {
            alert('No file selected.');
        }
    }

    get getInstruction() {
        return markup(this.props.quality_check_action.instruction.replace(/<img/g, '<img class="instruction-img"'))
    }

    passCheck() {
        this.state.checkValue = 'pass'
        this.validateQualityCheck()
    }

    failCheck() {
        this.state.checkValue = 'fail'
        this.validateQualityCheck()
    }

    async validateQualityCheck() {
        if ((this.props.quality_check_action.inspection_action_id[1] === 'Take a picture' || this.props.quality_check_action.inspection_type_id[1] === 'Measure')
            && this.state.qcValue === false) {
            this.notification.add(_t(`The value for the inspection action ${this.props.quality_check_action.inspection_action_id[1]} is not added.`), {
                type: "danger",
            });
        } else {
            if (this.props.quality_check_action.inspection_action_id[1] != 'Take a picture' || this.props.quality_check_action.inspection_type_id[1] != 'Measure') {
                this.state.qcValue = this.state.checkValue
            }
            this.state.qcStatus = await this.orm.call("quality.check.line", "validate_quality_actions", [this.props.quality_check_action.id, this.state.qcValue, this.state.qualityCheckNote])
            if (status(this) !== "destroyed") {
                this.env.bus.trigger("RELOAD_QC_DATA")
                this.handleModalClose()
            }
        }
    }

    handleModalClose() {
        this.props.close()
        this.props.handleModalClose({
            status: this.state.qcStatus
        })
    }
}
ValidateQualityAction.template = 'ValidateQualityAction';
registry.category("actions").add("validate_quality_action", ValidateQualityAction);