/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
const { useState, onWillStart, Component, onWillUpdateProps } = owl;
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { Select } from "@web/core/tree_editor/tree_editor_components";

export class RecordPathSelector extends Component {
    /**
     * RecordPathSelector is a component that allows the selection of records
     * and paths based on defined variables and their properties.
     */
    static defaultProps = {
        operator: "="
    }
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            selectedRecord: false,
            model: undefined,
            path: "",
        });
        onWillStart(async () => {
            this.props.value?.record && await  this.setState(this.props);
        })
        onWillUpdateProps(async (p) => {
            if (typeof p.value === "object" && "record" in p.value) {
                this.setState(p);
            }
            else {
                this.state.selectedRecord = false;
                this.state.model = undefined;
                this.state.path = "";
            }
        })
    }

    async setState(props) {
        const selectedVariable = this.props.variables.find(item => item.id === props.value.record);
        if (selectedVariable) {
            const model = await this.orm.read("ir.model", [selectedVariable.modelId], []);
            this.state.model = model? model[0] : undefined;
            this.state.selectedRecord = props.value.record;
            this.state.path = props.value.path;
        }
    }

    get options() {
        return [[false, ""], ...this.props.variables.map(variable => [variable.id, variable.variable_name])];
    }
     /**
     * Handles the update of the selected record based on the user's choice.
     * @param {String|Boolean} value - The selected variable's ID or false if none is selected.
     */
    async handleUpdateRecord(value) {
        if (value) {
            const selectedVariable = this.props.variables.find(item => item.id === value);
            const model = await this.orm.read("ir.model", [selectedVariable.modelId], []);
            this.state.model = model? model[0] : undefined;
            this.state.selectedRecord = value;
        } else {
            this.state.selectedRecord = value;
            this.state.model = undefined;
        }
    }

    updatePath(path, info) {
        this.state.path = path;
        this.props.update({ record: this.state.selectedRecord, path: path, pathValue: this.generatePathValue(path, info.fieldDef.type), info });
    }

    /**
     * Generates the path value based on the type of field and the operator.
     * @param {String} path - The current path.
     * @param {String} type - The type of field (e.g., many2one, one2many).
     * @returns {String} - The generated path value.
     */
    generatePathValue(path, type) {
        const { operator } = this.props;
        let pathVal = path;
        switch (type) {
            case "many2one":
                if (["=", "!="].includes(operator)) pathVal += ".id";
                else if (["in", "not in"].includes(operator)) pathVal += ".ids";
                break;
            case "many2many":
            case "one2many":
                pathVal += ".ids"
                break;
        }
        return pathVal;
    }

     /**
     * Filters fields based on the provided definitions and current path.
     * @param {Object} defs - The field definitions to filter.
     * @param {String} path - The current path used for filtering.
     * @returns {Boolean} - True if the field matches the criteria, false otherwise.
     */
    filterFields(defs, path) {
        if (!this.props.fieldInfo) return true;
        const { fieldInfo: { fieldDef, resModel }, operator } = this.props
        if (["ilike", "not ilike"].includes(operator)) return defs.type === "char"
        if (defs.name === "id") return true
        else if (fieldDef.type === "many2one" || fieldDef.type === "many2many" || fieldDef.type === "one2many"  ) {
            if (["in", "not in"].includes(operator) && fieldDef.type === "many2one") return fieldDef.relation === defs.relation
            return  fieldDef.type === defs.type && fieldDef.relation === defs.relation
        } else if (fieldDef.type === "binary") {
            return false
        } else if (fieldDef.type === "selection") {
            return fieldDef.type === defs.type && resModel === this.state.model.model && fieldDef.name === defs.name
        } else {
            if (fieldDef.type === "record") {
                return fieldDef.relation === defs.relation
            }
            return fieldDef.type === defs.type
        }
    }
}

RecordPathSelector.template = "RecordPathSelector";
RecordPathSelector.components = { Select, ModelFieldSelector  };
