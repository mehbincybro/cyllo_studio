/** @odoo-module **/
import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";

/**
 * MultiSelectDropDown
 *
 * Custom multi-select dropdown component that allows users to:
 * - Select multiple values from a provided list
 * - Display selected values as tags
 * - Remove tags to update the selection
 *
 * Uses Odoo's `TagsList` and `Dropdown` components for UI rendering,
 * and provides selection updates via the `onUpdate` callback.
 */
export class MultiSelectDropDown extends Component {
    static template = "cyllo_studio.MultiSelectDropDown";
    static components = {
        TagsList,
        Dropdown,
        DropdownItem,
    };
    static props = {
        selectedValues: { type: Array, optional: true },
        allValues: { type: Object, optional: false },
        onUpdate: { type: Function, optional: false },
        class: { type: String, optional: true },
        style: { type: String, optional: true },
    };
    setup() {
        this.state = useState({
            selectedValues: this.props.selectedValues,
            allValues: this.props.allValues
        })
        onWillUpdateProps((nextProps)=> {
            this.state.allValues = nextProps.allValues
            this.state.selectedValues = nextProps.selectedValues
        })
    }

    /**
     * Handle selection of a new value.
     *
     * Adds the selected value to the current list
     * and notifies the parent via `onUpdate`.
     *
     * @param {string|number} value - The selected value to add
     */
    onSelected(value) {
       this.props.onUpdate([...this.state.selectedValues, value])
    }

    /**
     * Construct tag props for rendering a tag.
     *
     * @param {string|number} rec - The record ID or key
     * @returns {Object} Tag configuration (id, text, delete handler)
     */
    getTagProps(rec) {
        return {
            id: rec,
            text: this.state.allValues[rec],
            onDelete: () => this.deleteTag(rec),
        };
    }

    deleteTag(rec) {
        this.props.onUpdate(this.state.selectedValues.filter(item => item !== rec))
    }

    /**
     * Compute tag list for display.
     *
     * @returns {Array<Object>} List of tag props
     */
    get tags() {
        let vals = this.state.selectedValues.map((rec, index) => {
            return this.getTagProps(rec)
        })
        return vals || {}
    }
}
