/** @odoo-module **/
import {
    Component,
    useState,
    useRef,
    onMounted,
} from "@odoo/owl";
import {
    useService,
    useOwnedDialogs,
} from "@web/core/utils/hooks";
import {
    DomainSelectorDialog
} from "@web/core/domain_selector_dialog/domain_selector_dialog";
import {
 _t
 } from "@web/core/l10n/translation";
import {
 Dialog
 } from "@web/core/dialog/dialog";


export class ConstraintDialog extends Component {
    static template = "cyllo_studio.ConstraintDialog";
    static props = {
        fieldName: String,
        fieldLabel: {
            type: String,
            optional: true,
        },
        existingConstraints: {
            type: Array,
            optional: true,
        },
        model: {
            type: String,
            optional: true,
        },
        onConfirm: Function,
        onCancel: {
            type: Function,
            optional: true,
        },
        close: Function,
    };

    setup() {
        this.notification = useService("effect");
        this.dialogService = useService("dialog");
        this.addDialog = useOwnedDialogs();
        this.rpc = useService("rpc");

        this.state = useState({
            fieldName: this.props.fieldName,
            fieldLabel: this.props.fieldLabel || this.props.fieldName,
            constraintType: "unique",
            condition: "",
            errorMessage: "",
            constraintKey: "",
            // ⭐ NEW: Track NULL/empty data warnings
            nullWarning: {
                show: false,
                nullCount: 0,
                emptyCount: 0,
                totalRecords: 0,
                affectedPercentage: 0,
            },
            isLoadingDataCheck: false,
        });

        this.constraintTypes = [
            { value: "unique", label: "Unique (No Duplicates)" },
            { value: "not_null", label: "Not Null (Required)" },
            { value: "check", label: "Check (Condition)" },
        ];

        onMounted(() => {
            this.generateConstraintKey();
        });
    }

    generateConstraintKey() {
        const fieldLower = this.state.fieldName.toLowerCase().replace(/\s+/g, '_');
        const typeLower = this.state.constraintType.toLowerCase();
        this.state.constraintKey = `${fieldLower}_${typeLower}`;
    }

    // ⭐ NEW METHOD: Check for NULL/empty values in the field
    async checkFieldData() {
        // Only check for NOT NULL constraint
        if (this.state.constraintType !== "not_null") {
            this.state.nullWarning.show = false;
            return;
        }

        if (!this.props.model) {
            console.warn("Model not provided to ConstraintDialog");
            return;
        }

        this.state.isLoadingDataCheck = true;

        try {
            const result = await this.rpc("/cyllo_studio/check_field_data", {
                model: this.props.model,
                field_name: this.props.fieldName,
            });

            const nullCount = result.null_count || 0;
            const emptyCount = result.empty_count || 0;
            const totalRecords = result.total_records || 0;
            const invalidCount = nullCount + emptyCount;

            this.state.nullWarning = {
                show: invalidCount > 0,
                nullCount: nullCount,
                emptyCount: emptyCount,
                totalRecords: totalRecords,
                affectedPercentage: totalRecords > 0 ? Math.round((invalidCount / totalRecords) * 100) : 0,
            };

            if (this.state.nullWarning.show) {
                console.warn(
                    `Field "${this.props.fieldName}" has ${invalidCount} NULL/empty values ` +
                    `out of ${totalRecords} records (${this.state.nullWarning.affectedPercentage}%)`
                );
            }
        } catch (error) {
            console.error("Error checking field data:", error);
            this.state.nullWarning.show = false;
        } finally {
            this.state.isLoadingDataCheck = false;
        }
    }

    async onConstraintTypeChange(value) {
        this.state.constraintType = value;
        this.state.condition = "";
        this.generateConstraintKey();

        // ⭐ Check data when switching to NOT NULL
        if (value === "not_null") {
            await this.checkFieldData();
        } else {
            this.state.nullWarning.show = false;
        }
    }

    openConditionBuilder() {
        if (this.state.constraintType !== "check") {
            this.notification.add({
                title: _t("Info"),
                message: "Condition builder is only for CHECK constraints",
                type: "notification_panel",
                notificationType: "info",
            });
            return;
        }

        const conditionInput = document.getElementById('condition-input');
        if (conditionInput) {
            conditionInput.focus();
        }
    }

    validateConstraint() {
        if (!this.state.errorMessage || !this.state.errorMessage.trim()) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Error message is required",
                type: "notification_panel",
                notificationType: "warning",
            });
            return false;
        }

        if (this.state.constraintType === "check" && !this.state.condition.trim()) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Check condition is required for CHECK constraints",
                type: "notification_panel",
                notificationType: "warning",
            });
            return false;
        }

        // ⭐ NEW: Warn about NOT NULL constraint with existing NULL values
        if (this.state.constraintType === "not_null" && this.state.nullWarning.show) {
            const confirmApply = confirm(
                `WARNING: This field has ${this.state.nullWarning.nullCount + this.state.nullWarning.emptyCount} ` +
                `NULL/empty values (${this.state.nullWarning.affectedPercentage}% of records).\n\n` +
                `When you save this constraint, these values will be automatically converted to empty strings.\n\n` +
                `Do you want to continue?`
            );

            if (!confirmApply) {
                return false;
            }
        }

        return true;
    }

    buildSQLConstraint() {
        const fieldName = this.state.fieldName;
        let definition = "";

        switch (this.state.constraintType) {
            case "unique":
                definition = `UNIQUE(${fieldName})`;
                break;
            case "not_null":
                definition = `CHECK(${fieldName} IS NOT NULL)`;
                break;
            case "check":
                definition = `CHECK(${this.state.condition})`;
                break;
            case "foreign_key":
                definition = this.state.condition;
                break;
            default:
                definition = "";
        }

        return {
            key: this.state.constraintKey,
            definition: definition,
            message: this.state.errorMessage,
        };
    }

    confirm() {
        if (!this.validateConstraint()) {
            return;
        }

        const constraint = this.buildSQLConstraint();
        this.props.onConfirm(constraint);
        this.props.close();
    }

    cancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        this.props.close();
    }

    // ⭐ Helper method to get warning severity level
    getWarningSeverity() {
        if (!this.state.nullWarning.show) return null;
        const percentage = this.state.nullWarning.affectedPercentage;
        if (percentage > 50) return "danger";
        if (percentage > 25) return "warning";
        return "info";
    }
}

ConstraintDialog.components = {Dialog};