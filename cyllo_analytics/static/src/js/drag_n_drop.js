/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
const { Component, useState, useRef, useEffect, onWillUpdateProps } = owl

export class DragItem extends Component {
    /** Class for draggable item */
    setup(){
        this.state = useState({
            isDragging: false
        })
        this.types = {
            "dimension": "measure",
            "measure": "dimension",
        }
        this.options = []
        this.mode = false
        this.setOptions()
    }
    /**
     * Set options based on the item's type.
     */
    setOptions(){
        if(this.props.type == "measure"){
            this.options = ["MIN", "MAX", "AVG", "SUM", "COUNT"]
            this.mode = "AGG"
        }
    }
    /**
     * Set the dragging state.
     * @param {Event} e - The drag event.
     * @param {boolean} val - The new dragging state.
     */
    setDragging(e, val){
        this.state.isDragging = val
        var { type, is_json } = this.props
        if(val){
            e.dataTransfer.setData("type", type)
            e.dataTransfer.setData("is_json", is_json)
        }
        var highlight = val ? 'highlight': ''
        var avoidTypes = val ? [this.types[type]]: []
        this.env.bus.trigger("CY:DROPZONE_HIGHLIGHT", { highlight, avoidTypes })
    }
}
// Define the template and components for the DragItem component
DragItem.template = "DragItem"
DragItem.components = { Dropdown, DropdownItem }

export class DropZone extends Component {
    /** Class for drop zone */

    setup(){
        this.types = {
            "dimension": "measure",
            "measure": "dimension",
        }
        this.state = useState({
            type: this.props.type,
            limit: this.props.limit,
            children: this.props.children,
            highlight: ''
        })
        this.ref = useRef('drop')
        this.env.bus.addEventListener("CY:DROPZONE_CHANGE_TYPE", (ev) => {
            var { category, type } = ev.detail
            this.changeType(category, type)
        });
        this.env.bus.addEventListener("CY:DROPZONE_IS_EMPTY", (ev) => {
            var { category, type } = ev.detail
            if(!this.state.children.length && this.props.category == category && this.state.type == type){
                this.state.type = 'both';
                this.env.bus.trigger("CY:DROPZONE_IS_EMPTY_CONFIRM", {category, type: this.types[type]})
            }
        });
        this.env.bus.addEventListener("CY:DROPZONE_IS_EMPTY_CONFIRM", (ev) => {
            var { category, type } = ev.detail
            if(this.props.category == category && this.state.type == type){
                this.state.type = 'both';
            }
        })
        this.env.bus.addEventListener("CY:DROPZONE_HIGHLIGHT", (ev) => {
            var { highlight, avoidTypes } = ev.detail
            if(avoidTypes && avoidTypes.includes(this.state.type)) return
            this.state.highlight = highlight
        })
        onWillUpdateProps(nextProps => {
            this.state.type = nextProps.type
            this.state.limit = nextProps.limit
            if(nextProps.children.length){
                this.state.children = nextProps.children
            }
        })
    }
    /**
     * Handle the drag-over event.
     * @param {Event} e - The drag-over event.
     */
    onDragOver(e){
        e.preventDefault();
        this.ref.el.classList.add('can-drop');
    }
    /**
     * Handle item drop event.
     * @param {Event} e - The drop event.
     */
    onItemDrop(e){
        e.preventDefault();
        var type = e.dataTransfer.getData("type")
        var is_json = e.dataTransfer.getData("is_json")
        if(this.state.type == "both" && this.props.axis){
            var axis = {
                "dimension": this.props.axis,
                "measure": this.props.axis == 'x' ? 'y' : 'x',
            }
            var data = axis[type]
            this.env.bus.trigger("CY:UPDATE_QUERY", {type: 'dimension_axis', data})
        }
        var is_core = Object.keys(this.types).includes(this.state.type) || this.state.type == "both"
        if(is_core){
            var category = this.props.category
            this.changeType(category, type)
            this.env.bus.trigger("CY:DROPZONE_CHANGE_TYPE", {category, type: this.types[type]})
        }
        const item = document.querySelector('.dragging');
        if((type == this.state.type || !is_core) && this.state.children.length < this.state.limit) {
            var column = item.dataset.column
            var to_char = ''
            if(is_json == 'true'){
                to_char = "->>'en_US'"
            }
            var alias = column.replace('.', '_')
            var query = column + ' ' + to_char + ' AS ' + alias
            this.state.children.push({
                type: item.dataset.type,
                value: item.textContent,
                alias,
                query,
                column
            });
            var data = this.state.children
            var new_type = this.state.type == "both" ? type : this.state.type
            this.env.bus.trigger("CY:UPDATE_QUERY", {type: new_type, data})
        }
        this.ref.el.classList.remove('can-drop');
    }
    /**
     * Change the category and type.
     * @param {string} category - The category to change to.
     * @param {string} type - The type to change to.
     */
    changeType(category, type){
        if(this.state.type == "both" && category == this.props.category){
            this.state.type = type
            if(type == "dimension"){
                this.state.limit = 1
            }
            if(type == "measure"){
                this.state.limit = 5
            }
        }
    }
    /**
     * Handle item removal.
     * @param {number} index - The index of the item to remove.
     * @param {string} type - The item type.
     */
    onItemRemove(index, type){
        let elem = this.state.children[index]
        this.state.children.splice(index, 1)
        this.env.bus.trigger("CY:UPDATE_QUERY", {type, data: this.state.children})
        if(elem.id){
            this.env.bus.trigger("CY:UPDATE_UNLINKS", {type: 'axis', id: elem.id})
        }
        if(!this.state.children.length){
            var category = this.props.category
            this.env.bus.trigger("CY:DROPZONE_IS_EMPTY", {category, type: this.types[type]})
        }
    }
    /**
     * Set functions for items.
     * @param {string} val - The new value.
     * @param {string} mode - The mode to set (e.g., "SUM").
     * @param {number} index - The index of the item.
     */
    setFunctions(val, mode, index){
        if(!this.state.children[index][mode]){
            this.state.children[index][mode] = val
            var column = this.state.children[index].column
            var new_column = `${val}(${column})`
            var alias = `${column.replace('.', '_')}_${val.toLowerCase()}`
            this.state.children[index] = {
                query: `${new_column} AS ${alias}`,
                alias,
                column,
                id: this.state.children[index].id,
                value: new_column,
                type: this.state.type
            }
            this.env.bus.trigger("CY:UPDATE_QUERY", {type: this.state.type, data: this.state.children})
        } else {
            var cur_child = this.state.children[index]
            var column = cur_child.column
            var new_column = column.replace(cur_child[mode], val)
            var match = column.match(/\(([^)]+)\)/)
            var alias = match ? match[1] : column
            alias = `${alias.replace('.', '_')}_${val.toLowerCase()}`
            var query = `${new_column} AS ${alias}`
            cur_child[mode] = val
            this.state.children[index] = {
                query,
                alias,
                column,
                id: this.state.children[index].id,
                value: new_column,
                type: this.state.type
            }
            this.state.children[index][mode] = val
            this.env.bus.trigger("CY:UPDATE_QUERY", {type: this.state.type, data: this.state.children})
        }
    }
}
// Define the template and components for the DropZone component
DropZone.template = "DropZone"

DropZone.defaultProps = {
    show: true,
    info: {
        condition: false,
        message: "",
        className: ""
    }
}
DropZone.components = { DragItem }
