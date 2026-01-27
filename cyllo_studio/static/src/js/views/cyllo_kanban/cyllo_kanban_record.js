/** @odoo-module **/

/**
 * CylloKanbanRecord
 *
 * Extends Odoo's KanbanRecord component to provide advanced functionality
 * for Cyllo Studio's Kanban view editor.
 *
 * Features:
 * 1. Dynamic Scaling: Responds to 'KanbanScale' events to scale Kanban cards
 *    according to user-selected percentages (50%, 100%, 150%, etc.) and
 *    automatically fits cards to the screen width.
 *
 * 2. Drag-and-Drop Editing:
 *    - Supports rearranging Kanban elements and cards via drag-and-drop.
 *    - Integrates with Trash for removing elements.
 *    - Enforces restrictions on fields with 't-if', 't-elif', 't-else', or
 *      'data-restrict' attributes.
 *    - Supports Undo/Redo functionality using sessionStorage.
 *
 * 3. Ribbon Management:
 *    - Handles ribbon click events to open detailed RibbonDialog for editing.
 *    - Detects all ribbons within a record or within the root container.
 *
 * 4. Field & Span Interaction:
 *    - Captures clicks on fields or spans within Kanban cards.
 *    - Triggers detailed events with properties such as name, path, styling,
 *      invisibility, and restrictions.
 *    - Provides formatted display of field values using Odoo utilities.
 *
 * 5. Color Management:
 *    - Determines card classes based on colors or a cardColorField.
 *    - Includes a mapping function to assign consistent colors for string or
 *      numeric values.
 *
 * 6. Integration with Odoo Services:
 *    - Uses rpc, action, dialog, and notification services.
 *    - Communicates with bus events for property updates, field selection,
 *      and scaling.
 *
 * 7. Components & Compiler:
 *    - Uses CylloKanbanCompiler for compiling custom Kanban cards.
 *    - Supports CylloField component for rendering custom fields inside cards.
 *
 * This component is primarily designed for use in Cyllo Studio, where
 * developers and users can visually edit Kanban views, manipulate fields,
 * ribbons, and spans, and preview dynamic behaviors in real-time.
 */
import { KanbanRecord } from "@web/views/kanban/kanban_record";
const {useState, onMounted, useRef} = owl;
import {CylloKanbanCompiler} from "./cyllo_kanban_compiler";
import { useService } from "@web/core/utils/hooks";
import { getFormattedValue } from "@web/views/utils";
import {ColorList} from "@web/core/colorlist/colorlist";
import { CylloField } from "@cyllo_studio/js/view_editor/fields/field";
import {_t} from "@web/core/l10n/translation";
import { RibbonDialog } from "@cyllo_studio/js/view_editor/kanban/ribbon_dialog";


export const scaleMapping = {
    '50%': 0.5,
    '100%': 1,
    '150%': 1.5,
    '200%': 2,
    '250%': 2.5,
    '300%': 3,
};

const { COLORS } = ColorList;

/**
 * Returns the class name of a record according to its color.
 */
function getColorClass(value) {
    return `oe_kanban_color_${getColorIndex(value)}`;
}

/**
 * Returns the index of a color determined by a given record.
 */
function getColorIndex(value) {
    if (typeof value === "number") {
        return Math.round(value) % COLORS.length;
    } else if (typeof value === "string") {
        const charCodeSum = [...value].reduce((acc, _, i) => acc + value.charCodeAt(i), 0);
        return charCodeSum % COLORS.length;
    } else {
        return 0;
    }
}

export class CylloKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.dialogService = useService('dialog');
        this.notification = useService("effect")
        this.trashRef = useRef("kanbanTrash")
        this.state = useState({
            ...this.state,
            scale: 1,
        })
        this.env.bus.addEventListener('KanbanScale', ({ detail }) => {
            this.state.scale = scaleMapping[detail.scale] || (() => {
                //@Fixme:- Fit screen not correctly fit all kanban view correctly
                //@Todo: debug the scale calculation formula
                const kanbanRenderer = document.querySelector('.o_kanban_renderer');
                const kanbanRendererComputedStyle = window.getComputedStyle(kanbanRenderer);
                if(!this.rootRef.el){
                  return 1
                }
                let width = this.rootRef.el.offsetWidth
                const kanbanRecordComputedStyle = window.getComputedStyle(this.rootRef.el);
                let marginLeft = parseFloat(kanbanRecordComputedStyle.marginLeft);
                let marginRight = parseFloat(kanbanRecordComputedStyle.marginRight);
                width = marginLeft + width + marginRight
                return parseFloat(kanbanRendererComputedStyle.width) / width;

            })();
        })
        onMounted(()=>{
            const self = this
            // Fallback: enforce selected ribbon visibility from session after Studio reload
            try {
                const selectedXPath = sessionStorage.getItem('SelectedRibbonXPath');
                if (selectedXPath && this.rootRef?.el) {
                    const ribbons = this.rootRef.el.querySelectorAll('[data-ribbon], .ribbon');
                    ribbons.forEach((rb) => {
                        const rbXPath = rb.getAttribute('cy-xpath');
                        if (rbXPath === selectedXPath) {
                            rb.style.display = '';
                        } else {
                            rb.style.display = 'none';
                        }
                    });
                }
            } catch(e) { /* noop */ }
            this.rootRef.el.addEventListener("mousemove", (el)=> {
                const elements = this.rootRef.el.querySelectorAll(".cy-studio-kanban-border");
                elements.forEach((e) => {
                  e.classList.remove("cy-studio-kanban-border");
                });
                el.target.closest('[cy-xpath]')?.classList.add('cy-studio-kanban-border')
            });
            const divElements = Array.from(this.rootRef.el.querySelectorAll('[data-drag="1"]'));
            //@Todo:- Merge both foreach together after completing the functionality
            divElements.forEach(div => {
               div.addEventListener('click', (event) => {
                    if (event.target === div) {
                        const elements = document.querySelectorAll('.border-class');
                        elements.forEach(e => {
                            e.classList.remove('border-class');
                        });
                        div.classList.add('border-class')
                        const path = div.getAttribute('cy-xpath')
                        this.env.bus.trigger("KANBAN_DIV", {
                            view_id: this.env.config.viewId,
                            type: "KanbanDivProperties",
                            view_type: this.env.config.viewType,
                            model: this.action.currentController.props.resModel,
                            path,
                            div,
                        })
                    }
              });
            });
            divElements.forEach((element, index) => {
                 var children = Array.from(element.children);
                 var nonChildDivs = divElements.filter((otherDiv) => {
                    return otherDiv !== element && !children.includes(otherDiv);
                });
                dragula([...nonChildDivs, this.trashRef.el], {
                    revertOnSpill: true,
                     moves: (el, container, handle) => {
                            const elementPath = el.getAttribute('cy-xpath')
                            const isDrag = el.getAttribute('data-drag') || false
                            const handlePath = handle.getAttribute('cy-xpath')
                            if(el.tagName.toUpperCase() === 'DIV' && isDrag && elementPath === handlePath && el.getAttribute('data-restrict')){
                                this.triggerWarning("Elements with 't-if', 't-elif', or 't-else' attributes cannot be moved.")
                                return false
                            }
                            return el.tagName.toUpperCase() === 'DIV' && isDrag && elementPath === handlePath;
                    },
                     accepts: (el, target, source, sibling) => {
                       return !el.contains(target)
                    },
                }).on('drag', (el)=> {
                     self.trashRef.el.classList.replace("opacity-0", "opacity-100");
                     nonChildDivs.forEach((e) => {
                        if(!el.contains(e)){
                            e.classList.add('cy-studio-kanban-container');
                        }
                    });
                }).on('shadow', (el, container, source)=>{
                if(container === self.trashRef.el){
                    el.classList.add('d-none')
                    self.trashRef.el.classList.replace("opacity-75", "opacity-100");
                    self.trashRef.el.style.backgroundImage = "radial-gradient(white, #fde0e0, #feaaaa)"
                } else {
                    self.trashRef.el.classList.replace("opacity-100", "opacity-75");
                    self.trashRef.el.style.backgroundImage = ""
                    el.classList.remove('d-none')
                }
                }).on('dragend', ()=>{
                    self.trashRef.el?.classList.remove("opacity-75", "opacity-100");
                self.trashRef.el.classList.add("opacity-0");
                     nonChildDivs.forEach((e) => {
                        e.classList.remove('cy-studio-kanban-container');
                    });
                }).on('drop', async(el, target, source, sibling)=>{
                    const path = el.getAttribute('cy-xpath')
                    const siblingPath = sibling?.getAttribute('cy-xpath');
                    const targetPath = target.getAttribute('cy-xpath');
                    const sibling_path = siblingPath || targetPath;
                    const position = siblingPath ? 'before' : 'inside';
                    try{
                        if(target == self.trashRef.el){
                           const response =  await self.rpc("cyllo_studio/kanban/remove", {
                                view_id: self.env.config.viewId,
                                view_type: self.env.config.viewType,
                                model: self.action.currentController.props.resModel,
                                path,
                                field_name: "",
                            })
                            if(response){
                                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                                storedArray.push(cleanedStr);
                                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                                sessionStorage.setItem('ReDO', JSON.stringify([]));
                            }
                        } else {
                            self.env.services.ui.block();
                                const response = await self.rpc("cyllo_studio/kanban/move", {
                                view_type: self.env.config.viewType,
                                model: self.action.currentController.props.resModel,
                                view_id: self.env.config.viewId,
                                path,
                                position,
                                sibling_path,
                            })
                            if(response){
                                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                                storedArray.push(cleanedStr);
                                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                                sessionStorage.setItem('ReDO', JSON.stringify([]));
                            }
                        }
                    } finally {
                        self.env.services.ui.unblock();
                    }
                    this.env.bus.trigger('resetProperties');
                    self.action.doAction('studio_reload')
                })
            });
             var drake = dragula([...divElements, this.trashRef.el], {
                revertOnSpill: true,
                moves: (el, container, handle) => {
                    if((handle.tagName === 'BUTTON' || handle.closest('button')) && el.getAttribute('data-restrict')){
                        return false;
                    }
                    return !el.getAttribute('data-restrict');
                },
                accepts: (el, target, source, sibling) => {
                   return !el.contains(target)
                },
            })
            drake.on('drag', (el)=>{
            if(el.getAttribute('data-restrict')){
                    this.triggerWarning("Elements with 't-if', 't-elif', or 't-else' attributes cannot be moved.")
                    drake.cancel(true);
                    return;
                }

                self.trashRef.el.classList.replace("opacity-0", "opacity-100");
                divElements.forEach((element) => {
                    element.classList.add('cy-studio-kanban-container');
                });
            }).on('shadow', (el, container, source)=>{
                if(container === self.trashRef.el){
                    el.classList.add('d-none')
                    self.trashRef.el.classList.replace("opacity-75", "opacity-100");
                    self.trashRef.el.style.backgroundImage = "radial-gradient(white, #fde0e0, #feaaaa)"
                } else {
                    self.trashRef.el.classList.replace("opacity-100", "opacity-75");
                    self.trashRef.el.style.backgroundImage = ""
                    el.classList.remove('d-none')
                }
            }).on('dragend', ()=> {
                self.trashRef.el?.classList.remove("opacity-75", "opacity-100");
                self.trashRef.el.classList.add("opacity-0");
                divElements.forEach((element) => {
                    element.classList.remove('cy-studio-kanban-container');
                });
            }).on('drop', async(el, target, source, sibling)=>{
                const path = el.getAttribute('cy-xpath')
                const fieldName = el.getAttribute('name')
                const regex = /field(\[\d+\])?$/;
                const isField = regex.test(path);
                const siblingPath = sibling?.getAttribute('cy-xpath');
                const targetPath = target?.getAttribute('cy-xpath');

                const sibling_path = siblingPath || targetPath;
                const position = siblingPath ? 'before' : 'inside';
                try{
                    self.env.services.ui.block();
                    if(target == self.trashRef.el){
                        let field = ""
                        if(isField){
                            const fieldNodes = self.props.archInfo.fieldNodes;
                            const nameExists = Object.keys(fieldNodes).filter(element => element.startsWith(fieldName));
                            let isPathIncluded = nameExists.some(name => fieldNodes[name].MainPath.includes('/kanban/field'));
                            field = isPathIncluded ? "" : fieldName
                        }

                        const response = await self.rpc("cyllo_studio/kanban/remove", {
                            view_id: self.env.config.viewId,
                            view_type: self.env.config.viewType,
                            model: self.action.currentController.props.resModel,
                            path,
                            field_name: field,
                        })
                        if(response){
                            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                            let cleanedStr = response.replace(/\s+/g, ' ').trim();
                            storedArray.push(cleanedStr);
                            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                            sessionStorage.setItem('ReDO', JSON.stringify([]));
                        }
                    } else {
                        const response = await self.rpc("cyllo_studio/kanban/move", {
                            view_type: self.env.config.viewType,
                            model: self.action.currentController.props.resModel,
                            view_id: self.env.config.viewId,
                            path,
                            position,
                            sibling_path
                        })
                        if(response){
                            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                            let cleanedStr = response.replace(/\s+/g, ' ').trim();
                            storedArray.push(cleanedStr);
                            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                            sessionStorage.setItem('ReDO', JSON.stringify([]));
                        }
                    }
                } finally {
                    self.env.services.ui.unblock();
                }
                this.env.bus.trigger('resetProperties');
                self.action.doAction('studio_reload')

             }).on('cancel', (el, container, source)=> {
                self.action.doAction('studio_reload')
            })
        })
    }

    /**
     * Displays a warning notification to the user.
     * @param {string} message - The message to display.
     */
    triggerWarning(message){
        this.notification.add({
            title: _t("Validation Error"),
            message,
            type: "notification_panel",
            notificationType: "warning",
            time: 5000
        });
    }

    /**
     * Computes and returns the CSS classes to be applied to this Kanban card.
     * Includes color classes, draggable state, and global click settings.
     * @returns {string} Space-separated list of CSS class names.
     */
    getRecordClasses() {
        const { archInfo, canResequence, forceGlobalClick, record, progressBarState } = this.props;
        const classes = ["o_kanban_record d-flex","o_kanban_record_headings"];
        if (canResequence) {
            classes.push("o_draggable");
        }
        if (forceGlobalClick || archInfo.openAction) {
            classes.push("oe_kanban_global_click");
        }
        if (progressBarState) {
            const { fieldName, colors } = progressBarState.progressAttributes;
            const value = record.data[fieldName];
            const color = colors[value];
            classes.push(`oe_kanban_card_${color}`);
        }
        if (archInfo.cardColorField) {
            const value = record.data[archInfo.cardColorField];
            classes.push(getColorClass(value));
        }
        return classes.join(" ");
    }

     /**
     * Handles a click on a field within the Kanban card.
     * Triggers the 'KANBAN_FIELD_DETAILS' event with detailed field information.
     * @param {Event} el - The click event object.
     */
    handleSelectField(el) {
        const getRestrictAttribute = (el, level = 0) => {
            if (level > 5 || !el) {
                return false; // Stop the recursion if level exceeds 5 or no element is found
            }
            const isRestricted = el.getAttribute('data-restrict');
            if (isRestricted) {
                return !!isRestricted;
            }
            return getRestrictAttribute(el.parentElement, level + 1);
        }
        const name = el.target.getAttribute("name") || el.srcElement.parentElement.getAttribute('name')
        if ( name ) {
            this.env.bus.trigger('KANBAN_FIELD_DETAILS', {
                view_id: this.env.config.viewId,
                view_type: this.env.config.viewType,
                active_fields: this.props.list.activeFields,
                model: this.action.currentController.props.resModel,
                name: name,
                path: el.target.getAttribute("cy-xpath") || el.target.parentElement.getAttribute('cy-xpath'),
                invisible: el.target.getAttribute("invisible"),
                isRestricted: getRestrictAttribute(el.target) ,
                isFieldTag: !!el.target.getAttribute("field-tag"),
                type: "KanbanFieldProperties",
                allfields: this.props.record.fields,
            });
        }
    }
    /**
     * Handles click events on a ribbon element in the Kanban card.
     * Opens the RibbonDialog with all ribbons found within the record or root container.
     * @param {Event} ev - The click event object.
     */
    handleRibbonClick(ev) {
        ev.stopPropagation();
        const ribbonEl = ev.currentTarget;
        const kanbanRecord = ribbonEl.closest(
            '.oe_kanban_record, .o_kanban_record, [data-id], .kanban-record'
        );
        let allRibbons = [];
        if (kanbanRecord) {
            // Ribbons within the specific kanban record
            allRibbons = kanbanRecord.querySelectorAll('[data-ribbon], .ribbon');
        } else {
            // Fallback: try the component's root element
            const rootElement =
                this.rootRef?.el ||
                this.owl?.bdom?.el ||
                ribbonEl.closest('.cy-studio-kanban-border')?.parentElement;
            if (rootElement) {
                allRibbons = rootElement.querySelectorAll(
                    '[data-ribbon], .ribbon, [cy-xpath*="ribbon"]'
                );
            }
        }
        if (allRibbons.length) {
            this.openRibbonDialog(Array.from(allRibbons));
        }
    }

    /**
     * Opens a RibbonDialog for the provided ribbon elements.
     * @param {HTMLElement[]} ribbonElements - List of ribbon DOM elements to edit.
     */
    openRibbonDialog(ribbonElements) {
    this.dialogService.add(RibbonDialog, {
        fields: this.kanbanFields,
        ribbonElement: ribbonElements,
        viewDetails: {
            viewId: this.env?.config?.viewId,
            viewType: this.env?.config?.viewType || this.props.viewType || "kanban",
            model: this.action.currentController.props.resModel,
            active_fields: this.props.record.fields,
        },
    })
    }

    /**
     * Handles a click on a span (text) element inside the Kanban card.
     * Triggers the 'kanbanSpanDetails' event with formatting and content info.
     * @param {Event} el - The click event object.
     */
    handleSelectSpan(el){
        this.env.bus.trigger('kanbanSpanDetails', {
            string : el.target.textContent,
            bold: el.target.classList.contains("fw-bold"),
            italic : el.target.classList.contains("fst-italic"),
            underline: el.target.classList.contains("text-decoration-underline"),
            is_edit :true ,
            element: el.target,
            view_id: this.env.config.viewId,
            model: this.action.currentController.props.resModel,
            view_type: this.env.config.viewType,
            type: "text",
        });
    }

    /**
     * Returns a formatted value for a field using Odoo utilities.
     * @param {string} fieldId - The ID of the field node.
     * @returns {string} Formatted string value for the field.
     */
    getFormattedValue(fieldId) {
        const {
            archInfo,
            record
        } = this.props;
        const {
            attrs,
            name,
            string
        } = archInfo.fieldNodes[fieldId];
        return getFormattedValue(record, name, attrs) || string;
    }

}

CylloKanbanRecord.components = {
  ...KanbanRecord.components,
  Field: CylloField
};
CylloKanbanRecord.Compiler = CylloKanbanCompiler;
CylloKanbanRecord.template = "cyllo_studio.KanbanRecord";
