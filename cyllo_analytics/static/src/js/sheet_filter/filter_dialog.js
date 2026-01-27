/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, useRef, useEffect, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { FieldAutoComplete } from "./field_auto_complete"

/**
 * FilterDialog class for managing filter dialogs in a component.
 * @class
 * @extends {Component}
 */
export class FilterDialog extends Component {
    /**
     * Initializes the FilterDialog class.
     * @function
     */
    setup(){
        this.notification = useService("notification")
        this.fields = this.props.fields
        this.orm = useService("orm")
        this.state = useState({
            domain: [],
            name: '',
            active: false,
        })
        onWillStart(() => {
            if (this.props.filterData) {
                this.state.name = this.props.filterData.name
                this.state.active = this.props.filterData.active
            }
        })
    }
    /**
     * Adds a value to the domain at a specific index.
     * @param {string} val - The value to be added to the domain.
     * @param {number} index - The index where the value should be added.
     * @function
     */
    addToDomain(val, index){
        this.state.domain[index] = val
    }
    /**
     * Handles the click event on the confirm button.
     * @function
     */
    onClickConfirm(){
        var domain = this.state.domain.join(' OR ')
        if(this.state.name && this.state.domain.length != 0){
            this.props.confirm({
                domain,
                name: this.state.name,
                active: this.state.active,
                edit: this.props.edit,
                id: this.props?.filterData.id || false
            })
            this.props.close()
        }  else {
            this.showMessage('Please Complete both the fields', 'danger')
        }
    }
    showMessage(message, type){
        this.notification.add(message, { type })
    }
    onClickRemove(props) {
        if (this.props.filterDomain) {
            var filterDomain = this.props.filterDomain.filter(item => item.id !== props.index)
            var whereQuery = []
            filterDomain.forEach((item, index) => {
                whereQuery.push(`${item.table}.${item.field} ${item.operator} ${item.rhs}`)
            })
            this.state.domain = whereQuery
        }
    }
}
FilterDialog.template = "FilterDialog"
FilterDialog.components = { Dialog, FieldAutoComplete }
FilterDialog.defaultProps = {
    filterData: false,
    filterDomain: false,
    edit: false
}