/** @odoo-module **/
/** @odoo-module **/

/**
 * GraphOverall Component
 *
 * This component provides an interactive interface for managing graph settings
 * in Cyllo Studio. It extends Odoo's Owl Component system and integrates
 * with the Cyllo Studio graph editor to enable dynamic graph configuration.
 *
 * Key Features:
 * 1. Handles graph types, measures, group-by fields, and sort order.
 * 2. Supports paginated graph type selection and icon-based switching.
 * 3. Provides interactive methods to update, remove, or add graph elements
 *    via RPC calls to the backend.
 * 4. Uses Owl hooks like `onMounted` and `onWillUpdateProps` to maintain
 *    reactive state updates.
 * 5. Integrates dropdowns, accordions, and custom Cyllo Studio UI components.
 *
 * Dependencies:
 * - `CylloStudioDropdown`, `Dropdown`, `DropdownItem`, `AccordionItem`
 * - Owl hooks and state management (`useState`, `onMounted`, `onWillUpdateProps`)
 * - Cyllo Studio utilities (`validateField`, `handleUndoRedo`)
 */

import {
    Component,
    useState,
    onMounted,
    onWillUpdateProps
} from "@odoo/owl";
import {
    useBus,
    useService
} from "@web/core/utils/hooks";
import {
    handleUndoRedo
} from "@cyllo_studio/js/utils/undo_redo_utils";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    validateField
} from "@cyllo_studio/js/actions/utils";
import {
    sortBy
} from "@web/core/utils/arrays";
import {
    DropdownItem
} from "@web/core/dropdown/dropdown_item";
import {
    Dropdown
} from "@web/core/dropdown/dropdown";
import {
    AccordionItem
} from "@web/core/dropdown/accordion_item";


export class GraphOverall extends Component {
    static template = "cyllo_studio.GraphOverall";
    setup() {
        this.action = useService("action");
        this.notification = useService("effect");
        this.rpc = useService("rpc");
        const fields = [];
        for (const [fieldName, field] of Object.entries(this.props.allFields || {})) {
            if (validateField(fieldName, field)) {
                fields.push(Object.assign({
                    name: fieldName
                }, field));
            }
        }
        const sortedFields = sortBy(fields, "string");
        const measures = this.props.MetaData.metaData.measures || {
            __count: {
                string: "Count"
            }
        };

        this.state = useState({
            New: true,
            stacked: this.props.MetaData.metaData.stacked,
            link: this.props.MetaData.metaData.disableLinking ?
                this.props.MetaData.metaData.disableLinking :
                false,
            groupBy: this.props.MetaData.metaData.groupBy,
            fields: sortedFields,
            graphTypes: ["line", "bar", "pie", "doughnut", "scatter", "bubble", "polarArea", "radar"],
            activeGraphs: this.props.mode.modes,
            enabledGraphs: [],
            currentPage: 0,
            itemsPerPage: 4,
            currentOrder: this.props.mode.order|| "ASC",
            currentType: this.props.mode.mode,
            displayedGraphType: this.props.mode.mode, // Currently displayed graph type
            measure: this.props.MetaData.metaData.measure || "__count__",
            measures: measures,
        });
        onWillUpdateProps(async (nextProps) => {
            this.state.measure = nextProps.MetaData.metaData.measure || "__count__"
            this.state.groupBy = nextProps.MetaData.metaData.groupBy
        });
    }

    capitalizeFirstLetter(text) {
        if (!text || typeof text !== 'string') return '';
        return text.charAt(0).toUpperCase() + text.slice(1);
    }

    get sortGraph() {
        const values = ["ASC", "DESC"];
        const labels = ["Ascending", "Descending"];
        return values.map((value, index) => ({
            value: value,
            label: labels[index],
        }));
    }

    get visibleGraphTypes() {
        const start = this.state.currentPage * this.state.itemsPerPage;
        const end = start + this.state.itemsPerPage;
        return this.state.activeGraphs.slice(start, end);
    }

    get chartTypes() {
        const types = this.visibleGraphTypes;
        return types.map(type => ({
            value: type,
            label: type.charAt(0).toUpperCase() + type.slice(1),
            pinned: type === this.state.currentType,
        }));
    }

    get graphIcons() {
        const ICONCLASS = {
            bar: "ri-bar-chart-fill",
            line: "ri-line-chart-line",
            pie: "ri-pie-chart-fill",
            doughnut: "ri-donut-chart-fill",
            scatter: "ri-bubble-chart-line",
            bubble: "ri-bubble-chart-fill",
            polarArea: "ri-pie-chart-line",
            radar: "ri-flow-chart",
        };
        return ICONCLASS;
    }

    onClickGraphIcon(event, type) {
        const index = this.state.activeGraphs.indexOf(type);
        if (index !== -1) {
            const itemsPerPage = this.state.itemsPerPage;
            const startIndex = Math.max(0, index - (itemsPerPage - 1));
            this.state.displayedGraphType = type;
            this.props.MetaData.updateMetaData({
                mode: type
            });
        }
    }

    prevPage() {
        const totalItems = this.state.activeGraphs.length;
        const totalPages = Math.ceil(totalItems / this.state.itemsPerPage);
        this.state.currentPage = (this.state.currentPage - 1 + totalPages) % totalPages;
    }

    nextPage() {
        const totalItems = this.state.activeGraphs.length;
        const totalPages = Math.ceil(totalItems / this.state.itemsPerPage);
        this.state.currentPage = (this.state.currentPage + 1) % totalPages;
    }

    toggleRotation() {
        this.state.isRotated = !this.state.isRotated;
    }


    get measureValue() {
        const arr = [];
        for (let measure in this.state.measures) {
            if (measure !== '__count') {
                const obj = {
                    value: measure,
                    label: this.state.measures[measure].string
                };
                arr.push(obj);
            }
        }
        return arr;
    }

    get groupByFields() {
        const fields = this.state.fields.map(field => ({
            value: field.name,
            label: field.string || field.name,
        }));
        if (fields.length === 0) {
            return [{
                value: "",
                label: "No fields available"
            }];
        }
        return fields;
    }

    async updateGraphElement({
        type,
        position,
        name,
        item_type,
        interval = ""
    }) {
        this.env.services.ui.block();
        try {
            if (type === "modes") {
                const updatedGraphs = [...this.state.activeGraphs];
                const index = updatedGraphs.indexOf(item_type);
                if (index === -1) {
                    updatedGraphs.push(item_type);
                } else {
                    updatedGraphs.splice(index, 1);
                    if (this.state.displayedGraphType === item_type) {
                        this.state.currentType = null;
                    }
                }
                this.state.activeGraphs = updatedGraphs;
                item_type = updatedGraphs;
            } else if (type === "order") {
                this.state.currentOrder = item_type;
                this.props.MetaData.updateMetaData({
                    order: item_type
                });
            } else if (type === "stacked") {
                const {
                    stacked
                } = this.props.MetaData.metaData;
                this.state.stacked = !stacked;
                this.props.MetaData.updateMetaData({
                    stacked: !stacked
                });
                item_type = !stacked;
            } else if (type === "default_type") {
                this.state.currentType = item_type;
                this.state.options = false;
                this.props.MetaData.updateMetaData({ mode: item_type });
            } else if (type === "measure") {
              this.state.measure = name;
                this.state.measureOptions = false;
                this.props.MetaData.updateMetaData({
                    measure: name
                });
            } else if (type === "dimension") {

            }

            // RPC call should be here inside try
            const response = await this.rpc("cyllo_studio/graph/edit_element", {
                model: this.props.model,
                view_type: this.props.viewType,
                view_id: this.props.viewId,
                position,
                name,
                item_type,
                interval,
            });
            this.state.New = true;
//            double reload happens
//            this.action.doAction("studio_reload");
            return response;

        } finally {
            this.env.services.ui.unblock();
        }
    }

    async removeGroupBy(measure, field) {
        if (!field) {
            this.state.New = true;
            return;
        }
        this.env.services.ui.block();
        try {
            const response = await this.rpc("cyllo_studio/graph/remove_element", {
                model: this.props.model,
                view_type: this.props.viewType,
                view_id: this.props.viewId,
                field,
            });
            this.state.groupBy = this.state.groupBy.filter(item => item !== field);
        } finally {
            this.env.services.ui.unblock();
        }
        this.state.New = true;
        this.action.doAction("studio_reload");

    }

    handleGroupBy() {
        this.state.New = false;
    }

    async onGroupBySelect(value, interval = "") {
        await this.updateGraphElement({
            type: "dimension",
            position: "inside",
            name: value,
            item_type: false,
            interval,
        });
        this.action.doAction("studio_reload");
    }
}

GraphOverall.components = {
    CylloStudioDropdown,
    Dropdown,
    DropdownItem,
    AccordionItem,
};