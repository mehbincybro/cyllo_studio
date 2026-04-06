/** @odoo-module */
const { useState, useRef, onMounted } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";

/**
 * LoopNode — modal configuration for the Loop node.
 *
 * Lets the user pick:
 *   1. Source type  → "Record Field" or "Variable"
 *   2. Collection   → field name (e.g. "order_line") OR a recordset variable
 *   3. Loop variable name → how each iteration item is called (e.g. "current_line")
 *
 * Generated code example:
 *   for current_line in current_record.order_line:
 */
export class LoopNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.labelInput = useRef("labelInput");
        this.loopVarInput = useRef("loopVarInput");

        // Extra reactive state on top of fieldState (provided by ConfigurationBase)
        this.loopState = useState({
            sourceType: 'field',       // 'field' | 'variable'
            collection: '',            // field name or variable id
            loopVariableName: '',      // iteration variable name
            labelError: false,
            collectionError: false,
            varNameError: false,
        });

        onMounted(() => {
            if (this.labelInput.el) this.labelInput.el.focus();
            // Pre-populate from already-saved fieldState (loaded by fetchData in base)
            this.loopState.sourceType = this.fieldState.loop_source_type || 'field';
            this.loopState.collection = this.fieldState.loop_collection || '';
            this.loopState.loopVariableName = this.fieldState.loop_variable_name || '';
        });
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    /** Recordset / record variables available when sourceType === 'variable' */
    get recordsetVariables() {
        return (this.props.variables || []).filter(
            v => v.variable_type === 'recordset' || v.variable_type === 'record'
        );
    }

    /** Resolves collection string for code generation. */
    get collectionExpression() {
        if (this.loopState.sourceType === 'variable') {
            const variable = (this.props.variables || []).find(
                v => v.id === this.loopState.collection
            );
            return variable ? variable.variable_name : this.loopState.collection;
        }
        // sourceType === 'field' — access the field on current_record
        return `current_record.${this.loopState.collection}`;
    }

    // ── Handlers ─────────────────────────────────────────────────────────────

    setSourceType(type) {
        this.loopState.sourceType = type;
        this.loopState.collection = '';
    }

    setCollection(value) {
        this.loopState.collection = value;
        this.loopState.collectionError = false;
    }

    setLoopVariableName(value) {
        this.loopState.loopVariableName = value;
        this.loopState.varNameError = false;
    }

    setLabel(value) {
        this.fieldState.label = value;
        const nodeId = this.props.id;
        if (this.labelInput.el?.classList.contains('invalid')) {
            this.labelInput.el.classList.remove('invalid');
        }
        this.env.bus.trigger("CHANGE-LABEL", { label: value, nodeId });
    }

    // ── Validation ───────────────────────────────────────────────────────────

    validateForm() {
        const errors = {};

        if (!this.fieldState.label || !this.fieldState.label.trim()) {
            this.loopState.labelError = true;
            errors.label = "Label is required.";
        }

        if (!this.loopState.collection || !this.loopState.collection.trim()) {
            this.loopState.collectionError = true;
            errors.collection = "Collection (field or variable) is required.";
        }

        const varName = (this.loopState.loopVariableName || '').trim();
        if (!varName) {
            this.loopState.varNameError = true;
            errors.varName = "Loop variable name is required.";
        } else if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(varName)) {
            this.loopState.varNameError = true;
            errors.varName = "Variable name must start with a letter/underscore and contain only alphanumeric characters.";
        }

        return { isValid: Object.keys(errors).length === 0, errors };
    }

    // ── Code Generation ──────────────────────────────────────────────────────

    generateCode() {
        const varName = this.loopState.loopVariableName.trim();
        const collection = this.collectionExpression;
        return `for ${varName} in ${collection}:`;
    }

    // ── Confirm ──────────────────────────────────────────────────────────────

    async onConfirm() {
        const { isValid, errors } = this.validateForm();
        if (!isValid) {
            this.env.services.effect.add({
                title: "Validation Error",
                message: "Unable to save Loop node.",
                description: Object.values(errors).join("\n"),
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }

        let modelId = null;
        let modelName = null;

        if (this.loopState.sourceType === 'variable') {
            const variable = (this.props.variables || []).find(v => String(v.id) === String(this.loopState.collection));
            modelId = variable?.modelId || variable?.model_id;
            modelName = variable?.modelName || variable?.model_name;
        } else {
            // sourceType === 'field' -> find the relation of this field
            const fieldName = this.loopState.collection.trim();
            const fields = await this.orm.searchRead(
                "ir.model.fields",
                [['model_id', '=', this.props.primaryModelId], ['name', '=', fieldName]],
                ['relation']
            );
            if (fields && fields.length > 0) {
                modelName = fields[0].relation;
                const models = await this.orm.searchRead(
                    "ir.model",
                    [['model', '=', modelName]],
                    ['id']
                );
                if (models && models.length > 0) {
                    modelId = models[0].id;
                }
            }
        }

        // Persist loop config into fieldState so save_data writes it to node.struct
        this.fieldState.loop_source_type = this.loopState.sourceType;
        this.fieldState.loop_collection = this.loopState.collection.trim();
        this.fieldState.loop_variable_name = this.loopState.loopVariableName.trim();

        const code = this.generateCode();
        this.state.used_variables = {};

        // Track variable usage if sourcing from a variable
        if (this.loopState.sourceType === 'variable' && this.loopState.collection) {
            this.updateUsedVariables(this.loopState.collection);
        }

        this.props.onConfirm(this.fieldState, code, this.state.used_variables, { modelId, modelName });
        this.props.close();
    }
}

LoopNode.template = "LoopNode";
LoopNode.components = { ...ConfigurationBase.components };
