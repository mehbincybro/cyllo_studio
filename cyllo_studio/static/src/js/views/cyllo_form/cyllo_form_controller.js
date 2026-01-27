/** @odoo-module **/
/**
 * CylloFormController
 *
 * Extends Odoo's FormController to provide drag-and-drop field management
 * in Odoo Studio forms, including support for One2many and Many2many fields.
 * Handles field positioning, undo/redo, and x2many record details.
 *
 * Features:
 *   - Drag-and-drop fields within groups.
 *   - Handle multi-path fields (buttons or complex widgets).
 *   - Supports X2Many (One2many/Many2many) inline editing.
 *   - Tracks field movement direction for proper RPC update.
 *   - Integrates with undo/redo functionality via sessionStorage.
 *   - Reloads the view and clears menus after updates.
 *
 * State:
 *   - fieldMove: Tracks field drag toggle state.
 *   - isX2Many: Boolean indicating if currently editing a X2Many field.
 *   - x2ManyDetails: Stores details about the X2Many view being edited.
 *
 * Services:
 *   - rpc: For server-side RPC calls.
 *   - action: For performing Odoo actions.
 */
import {
    FormController
} from "@web/views/form/form_controller";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { CylloListRenderer } from "@cyllo_studio/js/views/cyllo_list/cyllo_list_renderer";
import { CylloKanbanRenderer } from "@cyllo_studio/js/views/cyllo_kanban/cyllo_kanban_renderer";
import { serializeXML } from "@web/core/utils/xml";
const { useState, useEffect, onWillStart } = owl;

export class CylloFormController extends FormController {
    async setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.fieldMove = useState({
            toggle: false,
            firstReload: true,
        });
        this.state = useState({
            isX2Many: false,
            CyX2Many: false,
            x2ManyDetails: {}
        })
        const storedPages = sessionStorage.getItem("cy_studio_active_notebook");
            if (storedPages) {
                try {
                    const parsedPages = JSON.parse(storedPages);
                    // Ensure the state object exists before trying to merge
                    if (this.props.state && this.props.state.activeNotebookPages) {
                        Object.assign(this.props.state.activeNotebookPages, parsedPages);
                    }
                } catch (e) {
                    console.error("Error restoring notebook pages:", e);
                }
            }

        onWillStart(async ()=>{
            this.env.bus.trigger("Studio:NotebookChanged")
            if(!this.env.config.viewId){
                await this.rpc('cyllo_studio/form/add/form_view',{
                    arch: serializeXML(this.props.arch),
                    model: this.props.resModel,
                })
                sessionStorage.setItem('CyStudioView', this.props.resModel)
                await this.action.doAction('studio_reload')
            }
        })
        const state = this.props.state || {};
        const activeNotebookPages = {
            ...state.activeNotebookPages
        };
        this.onNotebookPageChange = (notebookId, page) => {
            if (page) {
                this.fieldMove.toggle = !this.fieldMove.toggle;
                activeNotebookPages[notebookId] = page;

                sessionStorage.setItem(
                    "cy_studio_active_notebook",
                    JSON.stringify(activeNotebookPages)
                );
            }
        };
        useEffect(
            () => {
            const storedPages = sessionStorage.getItem("cy_studio_active_notebook");
            if (storedPages) {
                try {
                    const parsedPages = JSON.parse(storedPages);
                    Object.keys(parsedPages).forEach(notebookId => {
                        const pageIndex = parsedPages[notebookId];
                        const notebook = document.querySelector(`.o_notebook[data-notebook-id="${notebookId}"]`);
                        if (!notebook) {
                            // Fallback: try to find the first notebook
                            const firstNotebook = document.querySelector('.o_notebook');
                            if (firstNotebook) {
                                const tabs = firstNotebook.querySelectorAll('.nav-link');
                                if (tabs[pageIndex]) {
                                    tabs[pageIndex].click();
                                }
                            }
                        } else {
                            const tabs = notebook.querySelectorAll('.nav-link');
                            if (tabs[pageIndex]) {
                                tabs[pageIndex].click();
                            }
                        }
                    });
                } catch (e) {
                    console.error("Error restoring tabs:", e);
                }
            }
        },
        () => []
        );
        useEffect(
            () => {
                var self = this;
                const InGrps = document.getElementsByClassName("o_inner_group");
                var drake = dragula([...InGrps], {
                    revertOnSpill: true,
                    moves: function(el, container, handle) {
                        if (handle.classList.contains("cy-studio-icon") || el.classList.contains("add-fields")) {
                            return false;
                        }
                        if(el.children.length > 2){
                            return false
                        }
                        if (el.classList.contains("o_wrap_field")) {
                            return true;
                        }
                        return false;
                    },
                    accepts: function(el, target, source, sibling) {
                        if (!sibling || sibling.classList.contains('o_wrap_field') || sibling.classList.contains('o_cell')|| sibling.classList.contains('cy-inner-trash-container')) {
                            return true;
                        }
                        return false;
                    },
                });
                let initialIndex = ''
                let initialX = ''
                drake.on("drag", (el,source) => {
                        initialIndex = Array.from(source.children).indexOf(el);
                        initialX = el.getBoundingClientRect().left;
                        const elementIcon = el.querySelector(".cy-studio-field-icons");
                        elementIcon?.classList.add("d-none");

                        el.classList.remove("d-sm-contents", "flex-column");
                        if (el.children[1]) {
                            el.children[0]?.classList.add(
                                "col-6",
                                "border",
                                "border-primary",
                                "me-3",
                                "w-100",
                                "h-100",

                            );
                            el.children[1]?.classList.add(
                                "col-6",
                                "border",
                                "border-primary",
                                "ms-3",
                                "w-100",
                                "h-100",
                            );
                        } else {
                            el.children[0]?.classList.add(
                                "col-12",
                                "border",
                                "border-primary"
                            );
                        }
                    })
                    .on("over", function(el, container, source) {
                        const ghostDiv = container.querySelector('ghost-container')
                        el.classList.add("d-sm-contents", "flex-column");
                    })
                    .on("dragend", function(el, container) {
                        const elementIcon = el.querySelector(".cy-studio-field-icons");
                        elementIcon?.classList.remove("d-none");
                        el.classList.add("d-sm-contents", "flex-column");
                        if (el.children[1]) {
                            el.children[0]?.classList.remove(
                                "col-6",
                                "border",
                                "border-primary"
                            );
                            el.children[1]?.classList.remove(
                                "col-6",
                                "border",
                                "border-primary"
                            );
                        } else {
                            el.children[0]?.classList.remove(
                                "col-12",
                                "border",
                                "border-primary"
                            );
                        }
                    })
                    .on("drop", async (el, target, source, sibling) => {
                        let finalIndex = Array.from(target.children).indexOf(el);
                        let finalX = el.getBoundingClientRect().left;
                        let path = target?.getAttribute("cy-xpath");
                        let position = "inside";
                        if (sibling) {
                            position = "before";
                            if(sibling.classList.contains('cy-inner-trash-container')){
                                const siblingPath = sibling.nextElementSibling?.firstElementChild?.getAttribute("cy-xpath");
                                path = siblingPath ? siblingPath : sibling.nextElementSibling?.firstElementChild?.firstElementChild?.getAttribute("cy-xpath");
                            }else{
                                path = sibling.firstElementChild?.getAttribute("cy-xpath");
                            }
                            if (!path){
                                let child = sibling.firstElementChild;
                                path = child.firstElementChild?.getAttribute("cy-xpath");
                            }
                        }
                        let has_multipath = false;
                        let item_path = el.firstElementChild?.getAttribute("cy-xpath") || "";
                        if (!item_path) {
                            let child = el.firstElementChild;
                            if (child.firstElementChild.nodeName == "BUTTON") {
                                item_path = child.firstElementChild?.getAttribute("cy-xpath");
                            } else if(!child.nextElementSibling){
                                item_path = child.firstElementChild?.getAttribute("cy-xpath")
                            } else {
                                has_multipath = true;
                                item_path = {
                                    first_path: child.firstElementChild?.getAttribute("cy-xpath"),
                                    second_path: child.nextElementSibling.firstElementChild?.getAttribute(
                                        "cy-xpath"
                                    ),
                                };
                            }
                        }
                        let direction = "";
                        if (finalIndex > initialIndex) {
                            direction = "down"; // Moved Down
                        } else if (finalIndex < initialIndex) {
                            direction = "up"; // Moved Up
                        }
                        if (finalX > initialX) {
                            direction = "right";
                        } else if (finalX < initialX) {
                            direction = "left";
                        }
                        if(path){
                        self.env.services.ui.block();
                            try {
                                const currentNotebook = document.querySelector('.o_notebook .nav-link.active');
                                    if (currentNotebook) {
                                        const notebookContainer = currentNotebook.closest('.o_notebook');
                                        const notebookId = notebookContainer?.getAttribute('data-notebook-id') || 'default';
                                        const pageIndex = Array.from(currentNotebook.parentElement.parentElement.children)
                                            .indexOf(currentNotebook.parentElement);

                                        const storedPages = JSON.parse(sessionStorage.getItem("cy_studio_active_notebook") || "{}");
                                        storedPages[notebookId] = pageIndex;
                                        sessionStorage.setItem("cy_studio_active_notebook", JSON.stringify(storedPages));
                                    }
                                const args = {
                                    'item_path': item_path,
                                    'path': path,
                                    'position': position,
                                    'has_multipath': has_multipath,
                                    'model': self.props.resModel,
                                    'view_id': self.env.config.viewId,
                                    'direction': direction,
                                    'inSource': target === source,
                                }
                                const result = await self.rpc("/cyllo_studio/FieldPositionMove", {
                                    args
                                });
                               if(result){
                                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                                let cleanedStr = result.FormArch.replace(/\s+/g, ' ').trim();
                                storedArray.push(cleanedStr)
                                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                                sessionStorage.setItem('ReDO', JSON.stringify([]));
                                }
                        } finally {
                            self.env.services.ui.unblock();
                        }
                        }
                        self.action.doAction("studio_reload");
                        this.env.bus.trigger('resetProperties')
                    });
                return () => {
                    drake.destroy();
                };
            },
            () => [this.fieldMove.toggle]
        );

         await this.env.bus.addEventListener('X2ManyDetails', (ev) => {
            this.state.x2ManyDetails = ev.detail
            this.state.isX2Many = true
            this.path = ev.detail.path

        });
    }

    get rendererX2ManyProps() {
        const props = {
            archInfo: this.state.x2ManyDetails.archInfo,
            list: this.state.x2ManyDetails.list,
            openRecord: (record) => {},
            evalViewModifier: (modifier) => {
                return evaluateBooleanExpr(modifier, this.state.x2ManyDetails.list.evalContext);
            },
        };

        if (this.state.x2ManyDetails.viewMode === "kanban") {
            const recordsDraggable = !this.state.x2ManyDetails.readonly && this.state.x2ManyDetails.recordsDraggable;
            props.archInfo = { ...props.archInfo, recordsDraggable };
            props.readonly = this.state.x2ManyDetails.readonly;
            // TODO: apply same logic in the list case
            props.deleteRecord = (record) => {
                if (this.state.x2ManyDetails.isMany2Many) {
                    return this.state.x2ManyDetails.list.forget(record);
                }
                return this.state.x2ManyDetails.list.delete(record);
            };

            return props;
        }
        props.activeActions = this.state.x2ManyDetails.archInfo?.activeActions
        return props;
    }

    /*  Rewriting this function as empty for restrict auto save of record when studio on */
    async beforeUnload(ev) {}

}

CylloFormController.components = {
    ...FormController.components,
    Layout,
    CylloListRenderer,
    CylloKanbanRenderer,
}
CylloFormController.template = "studio.CylloFormController"