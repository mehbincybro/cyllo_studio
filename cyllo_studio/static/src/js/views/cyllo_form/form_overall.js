/** @odoo-module **/

/**
 * FormOverall
 *
 * Odoo Studio component for managing overall form layout and interactions.
 * Provides drag-and-drop functionality for form elements, including:
 *   - Fields
 *   - Inner groups
 *   - Notebook pages
 *   - Chatter component
 *   - Tree view components (for X2Many)
 *
 * Handles component setup, state management, and interaction with Odoo services:
 *   - rpc: For server calls related to form modifications.
 *   - dialogService: For opening dialogs, such as FormTreeDialog.
 *   - action: For triggering Odoo actions and reloading the studio view.
 *   - notification: For effect notifications.
 *
 * State Properties:
 *   - can_create, can_edit, can_delete: Permissions for CRUD operations.
 *   - invisible: Tracks elements visibility status.
 *   - position: Tracks editable position of elements.
 *   - massedit: Enables multi-edit functionality.
 *   - view: Current view type (form, tree, kanban, etc.).
 *   - active_field: Currently selected field.
 *   - orders: Sorting order for the view.
 *   - groupBy: Grouping configuration.
 *   - showLink: Whether to open linked form view.
 *   - view_type: Determines form view type (tree, kanban, or standard form).
 *   - isChatterAvailable, hasChatter: Chatter availability.
 *   - isNotebookPageChange: Tracks notebook page changes.
 *   - fieldDropped: Indicates if a field was dropped in the form.
 *
 * Key Functionalities:
 *   - onWillStart: Initializes chatter availability and invisible state from server/session.
 *   - useEffect: Sets up drag-and-drop functionality for form elements.
 *   - Drag-and-drop handling:
 *       - Provides visual feedback while dragging.
 *       - Handles cloning, shadowing, and dropping of components.
 *       - Supports dynamic addition of notebook pages, inner groups, and fields.
 *       - Integrates with server-side RPC for adding/removing components.
 *       - Manages Undo/Redo history via sessionStorage.
 *   - Listens to events such as 'Studio:NotebookChanged' to update state accordingly.
 *
 * Overall, FormOverall provides a central orchestration layer for building and editing forms
 * dynamically in Odoo Studio, ensuring user-friendly interactions and seamless integration
 * with the backend.
 */
import { Component, onWillStart, useRef, useState, onMounted, useEffect, onWillUpdateProps } from "@odoo/owl";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormTreeDialog } from "@cyllo_studio/js/view_editor/dialog/form_tree_dialog";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { RibbonProperties } from "@cyllo_studio/js/view_editor/kanban/ribbon_properties"; // ADD THIS
import { RibbonDialog } from "@cyllo_studio/js/view_editor/kanban/ribbon_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
const Sortable = window.Sortable;

export class FormOverall extends Component {
    static template = "cyllo_studio.FormOverall";

    setup() {
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
        this.action = useService("action");
        this.notification = useService('effect')
        this.isPreviewModeActive = false
        this.state = useState({
            can_create: this.props.mode.activeActions?.create || this.props.mode.create,
            can_edit: this.props.mode.activeActions?.edit || this.props.mode.edit,
            can_delete: this.props.mode.activeActions?.delete || this.props.mode.delete,
            invisible: false,
            position: this.props.mode.editable || "",
            massedit: this.props.mode.multiEdit,
            view: "",
            active_field: this.props.mode.defaultOrder?.[0]?.name || null,
            orders: this.props.mode.defaultOrder?.[0]?.asc,
            groupBy: this.props.mode.defaultGroupBy,
            showLink: this.props.mode.openFormView,
            view_type: this.props.x2many ? (this.props.x2many === 'list' ? 'tree' : 'kanban') : this.props.view_type,
            isChatterAvailable: true,
            hasChatter: this.props.isChatterAvailable,
            isNotebookPageChange: true,
            fieldDropped: false,
            hasStudioChanges: false,
            isPreviewMode: false,
            buttonLimitEnabled: false,
            buttonLimitValue: '',
            hasButtonLimitAttribute: false,
        });
        this.state.deactivatedViews = [];
        this.state.selectedDeactivatedViewId = null;
        this.loadDeactivatedViews();
        this.state.recordNameOptions = [];
        this.state.currentRecName = null;
        this.loadRecordNameData();
        const model =
            this.props?.viewInfo?.action?.res_model ||
            this.props?.archInfo?.model ||
            this.props?.resModel ||
            this.props?.model ||
            null;
        this.state.isStudioModel = model && model.startsWith("x_");

        onWillStart(async () => {
            await this.loadButtonLimitAttribute();
            this.state.invisible = sessionStorage.getItem('invisible');

            if (this.props.model) {
                const result = await this.rpc("/cyllo_studio/check/chatter", {
                    model: this.props.model
                });
                this.state.isChatterAvailable = !!result;
            } else {
                this.state.isChatterAvailable = false;
            }
        });

        const self = this;
        document.addEventListener('click', async (event) => {
            if (!self.state.isPreviewMode || !self.isPreviewModeActive) {
                return;
            }
            const clickText = (event.target.textContent || '').toLowerCase();
            if (clickText.includes('activate') ||
                clickText.includes('cancel') ||
                event.target.closest('select')) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            await self.cancelPreview();
            this.action.doAction("studio_reload");

        }, false);

        this.env.bus.addEventListener('Studio:NotebookChanged', (ev) => {
            setTimeout(() => {
                this.state.isNotebookPageChange = !this.state.isNotebookPageChange
            }, 100)

        })
        useEffect(() => {
            const self = this;
            const sortableInstances = [];

            // MONKEY PATCH: Fix SortableJS drag-and-drop bug with display:contents elements in Odoo grid.
            // SortableJS relies on getBoundingClientRect for hover detection. However, o_wrap_field elements
            // use 'display: contents', causing their bounding rect to be 0x0. This patch computes the
            // bounding box based on their children (label + input) so SortableJS can properly place ghosts
            // between existing grid fields.
            if (!window._cy_sortable_gbcr_patched) {
                const originalGBCR = Element.prototype.getBoundingClientRect;
                Element.prototype.getBoundingClientRect = function() {
                    if (this.classList && this.classList.contains('o_wrap_field') && this.classList.contains('d-sm-contents')) {
                        let rect = { top: Infinity, left: Infinity, right: -Infinity, bottom: -Infinity };
                        let hasChildren = false;
                        for (let i = 0; i < this.children.length; i++) {
                            let childRect = originalGBCR.call(this.children[i]);
                            if (childRect.width > 0 || childRect.height > 0) {
                                hasChildren = true;
                                rect.top = Math.min(rect.top, childRect.top);
                                rect.left = Math.min(rect.left, childRect.left);
                                rect.right = Math.max(rect.right, childRect.right);
                                rect.bottom = Math.max(rect.bottom, childRect.bottom);
                            }
                        }
                        if (hasChildren) {
                            return {
                                top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom,
                                width: rect.right - rect.left, height: rect.bottom - rect.top,
                                x: rect.left, y: rect.top, toJSON: () => ({})
                            };
                        }
                    }
                    return originalGBCR.call(this);
                };
                window._cy_sortable_gbcr_patched = true;
            }

            const getXpath = (el) => {
                if (!el) return null;
                return el.getAttribute('cy-xpath') || el.querySelector('[cy-xpath]')?.getAttribute('cy-xpath');
            };

            // 1. Helpers for styling ghosts and clones
            const applyGhostAppearance = (ghost, original) => {
                ghost.classList.remove('cy-components-column');
                if (original.classList.contains('cy-studio-ribbon')) {
                    ghost.classList.add('ribbon', 'ribbon-top-right');
                    ghost.style.zIndex = '10';
                    ghost.style.opacity = '1';
                    ghost.innerHTML = `<span class="text-bg-danger"></span>`;
                } else if (original.classList.contains('column-1')) {
                    ghost.innerHTML = col1;
                } else if (original.classList.contains('column-2')) {
                    ghost.innerHTML = col2;
                } else if (original.classList.contains('tab')) {
                    ghost.innerHTML = tab;
                } else if (original.classList.contains('field')) {
                    ghost.removeAttribute('style');
                    ghost.classList.remove('cy-studio-component-btn', 'cy-studio-move');
                    ghost.classList.add('add-fields', 'o_wrap_field', 'd-flex', 'd-sm-contents', 'flex-column', 'mb-3', 'mb-sm-0', 'dd-box', 'cy-container');
                    ghost.innerHTML = field;
                } else if (original.classList.contains('chatter')) {
                    ghost.innerHTML = chatter;
                } else if (original.classList.contains('kanban')) {
                    ghost.innerHTML = x2manyKanban;
                } else {
                    ghost.innerHTML = x2many;
                }
            };

            const applyCloneAppearance = (clone, original) => {
                clone.style.color = "black";
                if (original.classList.contains('cy-studio-ribbon')) {
                    clone.classList.remove('cy-studio-icon', 'bg-secondary', 'rounded', 'px-2', 'py-1',
                        'border', 'border-white', 'text-white', 'cy-component-container', 'kanban-component-text');
                    clone.removeAttribute('data-tooltip');
                    clone.classList.add('ribbon', 'ribbon-top-right');
                    clone.style.zIndex = '10';
                    clone.style.opacity = '1';
                    clone.innerHTML = `<span class="text-bg-danger"></span>`;
                } else if (original.classList.contains('field')) {
                    clone.classList.add('d-flex', 'gap-2');
                    clone.innerHTML = dragField;
                }
            };

            // 2. Ribbon Interaction Handler
            const setupRibbonClickHandlers = () => {
                const ribbons = document.querySelectorAll('div.ribbon[cy-xpath]');
                ribbons.forEach((ribbon) => {
                    ribbon.style.cursor = 'pointer';
                    ribbon.style.pointerEvents = 'auto';
                    const oldHandler = ribbon._ribbonClickHandler;
                    if (oldHandler) ribbon.removeEventListener('click', oldHandler, true);
                    const newHandler = (e) => {
                        e.stopPropagation(); e.stopImmediatePropagation(); e.preventDefault();
                        const ribbonPath = ribbon.getAttribute('cy-xpath');
                        if (!ribbonPath) return;
                        const allRibbons = document.querySelectorAll('div.ribbon[cy-xpath]');
                        const viewId = self.props.viewId;
                        const model = self.props.model || self.action.currentController.props.resModel;
                        const fields = [];
                        if (self.props.allFields) {
                            for (const [fieldName, field] of Object.entries(self.props.allFields)) {
                                fields.push({ value: fieldName, label: field.string });
                            }
                        }
                        self.dialogService.add(RibbonDialog, {
                            fields: fields,
                            ribbonElement: Array.from(allRibbons),
                            viewDetails: { viewId, viewType: self.props.viewType || 'form', model, active_fields: self.props.allFields, ribbonPath }
                        });
                    };
                    ribbon._ribbonClickHandler = newHandler;
                    ribbon.addEventListener('click', newHandler, true);
                });
            };

            // 3. Global click interceptor for ribbons
            const globalRibbonInterceptor = (e) => {
                const ribbon = e.target.closest('div.ribbon[cy-xpath]');
                if (ribbon) {
                    e.stopPropagation(); e.stopImmediatePropagation(); e.preventDefault();
                    ribbon._ribbonClickHandler?.(e);
                    return false;
                }
            };
            document.addEventListener('click', globalRibbonInterceptor, true);

            // 4. Containers and HTML templates
            const forms = document.getElementsByClassName('o_form_sheet');
            const form_tabs = document.getElementsByClassName('tab-pane');
            const innerGroup = document.getElementsByClassName('o_inner_group');
            const component = document.getElementById('cyComponents');
            const componentElement = document.getElementById('cyComponents-elements-1');
            const componentElement2 = document.getElementById('cyComponents-elements-2');
            const chatterComponent = document.getElementById('chatterComponent');
            const form = forms ? forms[0] : forms;

            const col1 = '<div class="o_inner_group grid dd-container cy-studio-inner"></div>';
            const col2 = '<div class="o_group row align-items-start"><div class="o_inner_group grid dd-container cy-studio-inner border-class col-lg-6 py-2"></div><div class="o_inner_group grid dd-container cy-studio-inner border-class col-lg-6 py-2"></div></div>';
            const tab = '<div class="o_notebook d-flex w-100 horizontal flex-column"><div class="o_notebook_headers"><ul class="nav nav-tabs flex-row flex-nowrap"><li class="nav-item flex-nowrap cursor-pointer"><a class="nav-link active" href="#" role="tab" tabindex="0" name="">New Page</a></li><li class="nav-item flex-nowrap cursor-pointer"><a class="nav-link ri-add-line"></a></li></ul></div><div class="o_notebook_content tab-content"><div class="tab-pane active"></div></div></div>';
            const x2many = '<div class="o_field_widget o_field_one2many"><div class="o_list_view o_field_x2many o_field_x2many_list"><div class="o_x2m_control_panel d-empty-none mb-4"></div><div class="o_list_renderer o_renderer table-responsive o_list_renderer_5 col-12" tabindex="-1" style=""><table class="o_list_table table table-sm table-hover position-relative mb-0 o_list_table_ungrouped table-striped" style="table-layout: fixed;"><thead><tr><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer o_list_number_th o_handle_cell opacity-trigger-hover" style="width: 33px;"></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer opacity-trigger-hover" style="width: 33.33%;"><div class="d-flex"><span class="d-block min-w-0 text-truncate flex-grow-1">Product</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer o_list_number_th opacity-trigger-hover" style="width: 92px;"><div class="d-flex flex-row-reverse"><span class="d-block min-w-0 text-truncate flex-grow-1 o_list_number_th">Quantity</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer opacity-trigger-hover" style="width: 33.33%;"><div class="d-flex"><span class="d-block min-w-0 text-truncate flex-grow-1">Description</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer o_list_number_th opacity-trigger-hover" style="width: 92px;"><div class="d-flex flex-row-reverse"><span class="d-block min-w-0 text-truncate flex-grow-1 o_list_number_th">Unit Price</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th class="o_list_button" style="width: 33.33%;"></th><th class="o_list_controller o_list_actions_header position-sticky end-0"><div class="o-dropdown dropdown o_optional_columns_dropdown text-center border-top-0 o-dropdown--no-caret"><button type="button" class="dropdown-toggle btn p-0" tabindex="-1" aria-expanded="false"><i class="o_optional_columns_dropdown_toggle oi oi-fw oi-settings-adjust"></i></button></div></th></tr></thead><tbody class="ui-sortable"><tr><td></td><td class="o_field_x2many_list_row_add" colspan="6"><a href="#" role="button" tabindex="0">Add a product</a></td></tr><tr><td colspan="7">​</td></tr><tr><td colspan="7">​</td></tr><tr><td colspan="7">​</td></tr></tbody><tfoot class="o_list_footer cursor-default"><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr></tfoot></table></div></div></div>';
            const x2manyKanban = '<div class="o_kanban_view" style="width: 100%;"><div class="d-flex flex-wrap gap-3" style="width:100%;"><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div><div class="o_kanban_primary text-muted small">Unit Price:</div></div><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div><div class="o_kanban_primary text-muted small">Unit Price:</div></div><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div><div class="o_kanban_primary text-muted small">Unit Price:</div></div><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div>      <div class="o_kanban_primary text-muted small">Unit Price:</div></div></div></div>';
            const chatter = '<div class="o-mail-Form-chatter oe_chatter o-isInFormSheetCy w-auto o-aside"><div class="o-mail-Chatter w-100 h-100 flex-grow-1 d-flex flex-column overflow-auto"></div></div>';
            const field = '<div class=" new_field o_cell flex-grow-1 o_wrap_label w-100  text-900 cursor-pointer opacity-75"><label class="o_form_label oe_inline">New Field</label></div><div class=" new_field o_cell flex-grow-1 flex-sm-grow-0 cursor-pointer opacity-75" style="width: 100%;"><div class="o_row o_row_readonly"><div name="new_field"><div class="d-inline-flex w-100"><input class="o_input" type="text" autocomplete="off" id="new_field_0" readonly="1"/></div></div></div></div>';
            const dragField = '<label class="text-nowrap">New Field</label>';

            // 5. Initialize Source Sortables
            const sources = [component, componentElement, componentElement2, chatterComponent].filter(Boolean);
            sources.forEach(src => {
                const s = Sortable.create(src, {
                    group: { name: 'form-components', pull: 'clone', put: false },
                    sort: false,
                    animation: 150,
                    onStart: (evt) => {
                        const el = evt.item;
                        if (el.classList.contains('chatter')) {
                            chatterComponent.classList.add('chatterContainer');
                            const dropHereDiv = document.createElement('div');
                            dropHereDiv.textContent = 'Drop Here';
                            dropHereDiv.classList.add('drop-here-container');
                            chatterComponent.appendChild(dropHereDiv);
                        }
                    },
                    onClone: (evt) => applyCloneAppearance(evt.clone, evt.item),
                    onEnd: (evt) => {
                        chatterComponent?.classList.remove('chatterContainer');
                        document.querySelector('.drop-here-container')?.remove();
                    }
                });
                sortableInstances.push(s);
            });

            // 6. Initialize Target Sortables
            const targetContainers = [form, ...Array.from(form_tabs), ...Array.from(innerGroup)].filter(Boolean);
            targetContainers.forEach(target => {
                const s = Sortable.create(target, {
                    group: {
                        name: 'form-components',
                        put: (to, from, dragEl) => {
                            if ([...innerGroup].includes(from.el) || dragEl.classList.contains('cy-chatter-exist')) return false;
                            if (dragEl.classList.contains('chatter')) return to.el === chatterComponent;
                            if (dragEl.classList.contains('cy-studio-ribbon')) return to.el.classList.contains('o_form_sheet') || to.el.classList.contains('tab-pane');
                            if (dragEl.classList.contains('field')) return to.el.classList.contains('o_inner_group');
                            if (dragEl.classList.contains('tab')) return to.el.classList.contains('o_form_sheet');
                            return to.el.classList.contains('o_form_sheet') || to.el.classList.contains('tab-pane');
                        }
                    },
                    animation: 150,
                    // Fix: enable symmetric upward-drag behaviour (matches Dragula behaviour).
                    // Without these options, SortableJS only fires a swap when the cursor
                    // enters the *bottom* half of the element above, making dragging upward
                    // feel blocked or impossible.
                    // direction: 'vertical',
                    // swapThreshold: 0.65,  // trigger zone covers 65% of each item height
                    // invertSwap: true,      // top 35% of an item triggers "insert before" it
                    ghostClass: 'sortable-ghost',
                    chosenClass: 'sortable-chosen',
                    // FIXED: read sibling from live DOM after SortableJS has already inserted el
                    onAdd: async (evt) => {
                        const el = evt.item;
                        const targetEl = evt.to;

                        // SortableJS has already placed el at the correct DOM position by the
                        // time onAdd fires. Walk el.nextElementSibling (not evt.nextSibling,
                        // which is stale and wrong for upward drags) to find the real backend
                        // anchor node.
                        let rawSibling = el.nextElementSibling;
                        while (rawSibling && !getXpath(rawSibling)) {
                            rawSibling = rawSibling.nextElementSibling;
                        }
                        const sibling = rawSibling || null;

                        applyGhostAppearance(el, el);
                        await handleDrop(el, targetEl, sibling);
                    }
                    // onAdd: async (evt) => {
                    //     const el = evt.item;
                    //     const targetEl = evt.to;
                    //     // Bug fix: evt.nextSibling from SortableJS can be a text node,
                    //     // a sortable ghost/placeholder, or a non-cy-xpath element.
                    //     // Walk forward until we find a real element carrying cy-xpath
                    //     // so that "position=before" lands on the correct backend node.
                    //     let rawSibling = evt.nextSibling;
                    //     while (
                    //         rawSibling &&
                    //         (rawSibling.nodeType !== 1 ||
                    //          !rawSibling.getAttribute('cy-xpath'))
                    //     ) {
                    //         rawSibling = rawSibling.nextElementSibling || rawSibling.nextSibling;
                    //     }
                    //     // Exclude the just-dropped element itself if it ended up as its own sibling
                    //     const sibling = rawSibling === el ? null : (rawSibling || null);
                    //     applyGhostAppearance(el, el);
                    //     await handleDrop(el, targetEl, sibling);
                    // }
                });
                sortableInstances.push(s);
            });

            // 7. Drop Handler Logic
            const handleDrop = async (el, target, sibling) => {
                if (el.classList.contains("cy-studio-ribbon")) {
                    const viewId = self.props.viewId;
                    const model = self.props.model || self.action.currentController.props.resModel;
                    const ribbonPath = sibling ? getXpath(sibling) : getXpath(target);
                    const ribbonPosition = sibling ? "before" : "inside";
                    self.env.bus.trigger("KANBAN_COMPONENT", {
                        type: "ribbon",
                        properties: { elementInfo: { path: ribbonPath, position: ribbonPosition } },
                        viewDetails: { model, view_id: viewId, view_type: self.props.viewType, allFields: self.props.allFields },
                        element: el,
                    });
                    self.props.updateState?.("type", "ribbon");
                    self.props.updateState?.("edit", true);
                    return;
                }

                let item = '', position = sibling ? 'before' : 'inside';
                let path = sibling ? getXpath(sibling) : getXpath(target);
                self.state.fieldDropped = true;

                if (el.classList.contains('chatter')) path = '/form';
                if (el.classList.contains('column-1')) item = '<group></group>';
                else if (el.classList.contains('column-2')) item = '<group><group></group><group></group></group>';
                else if (el.classList.contains('tab')) item = '<notebook><page string="New Page"></page></notebook>';

                if (item || el.classList.contains('field') || el.classList.contains('chatter')) {
                    if (el.classList.contains('chatter')) {
                        self.env.services.ui.block();
                        try {
                            const add_remove = await self.rpc("cyllo_studio/add_remove/chatter", {
                                model: self.props.model, view_id: self.props.viewId, path: "/form", view_type: "form", position: "inside"
                            });
                            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo') || "[]");
                            storedArray.push(add_remove.replace(/\s+/g, ' ').trim());
                            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                            sessionStorage.setItem('ReDO', JSON.stringify([]));
                        } finally {
                            self.env.services.ui.unblock();
                            self.action.doAction('studio_reload');
                        }
                    } else if (el.classList.contains('field')) {
                        // Bug fix: In o_inner_group grid, cy-xpath sits directly on the
                        // row wrapper (sibling itself), NOT on its first child.
                        // Priority: sibling[cy-xpath] → sibling.firstElementChild[cy-xpath] → target[cy-xpath]
                        const fieldPath = sibling ? getXpath(sibling) : getXpath(target);
                        self.env.bus.trigger("FIELDS_DETAILS", { cy_path: fieldPath, position, create: true, type: "Properties" });
                    } else {
                        // Store notebook state if applicable
                        const currentNotebook = document.querySelector('.o_notebook .nav-link.active');
                        if (currentNotebook) {
                            const notebookContainer = currentNotebook.closest('.o_notebook');
                            const notebookId = notebookContainer?.getAttribute('data-notebook-id') || 'default';
                            const pageIndex = Array.from(currentNotebook.parentElement.parentElement.children).indexOf(currentNotebook.parentElement);
                            const storedPages = JSON.parse(sessionStorage.getItem("cy_studio_active_notebook") || "{}");
                            storedPages[notebookId] = pageIndex;
                            sessionStorage.setItem("cy_studio_active_notebook", JSON.stringify(storedPages));
                        }

                        self.env.services.ui.block();
                        const response = await self.rpc("cyllo_studio/add/component", {
                            method: 'add_component',
                            args: [{ view_type: 'form', view_id: self.props.viewId, path, position, item, model: self.action.currentController.action.res_model }]
                        });
                        self.env.services.ui.unblock();
                        self.action.doAction('studio_reload');
                        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo') || "[]");
                        storedArray.push(response.replace(/\s+/g, ' ').trim());
                        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                        sessionStorage.setItem('ReDO', JSON.stringify([]));

                        if (sessionStorage.getItem('cylloActivePagePath')) {
                            const newPath = sessionStorage.getItem('cylloActivePagePath');
                            const element = document.querySelector(`[cy-xpath="${newPath}"]`);
                            element?.firstElementChild?.click();
                        }
                    }
                } else if (el.classList.contains('kanban') || el.classList.contains('tree')) {
                    self.dialogService.add(FormTreeDialog, {
                        resModel: self.action.currentController.props.resModel,
                        isKanban: el.classList.contains('kanban'),
                        onConfirm: async (result) => {
                            self.env.services.ui.block();
                            const response = await self.rpc("cyllo_studio/add/form_tree", {
                                kwargs: { ...result, path, position, view_id: self.props.viewId, view_type: el.classList.contains('kanban') ? 'kanban' : 'form', model: self.action.currentController.props.resModel }
                            });
                            self.env.services.ui.unblock();
                            if (response) {
                                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo') || "[]");
                                storedArray.push(response.replace(/\s+/g, ' ').trim());
                                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                                sessionStorage.setItem('ReDO', JSON.stringify([]));
                            }
                            self.action.doAction("studio_reload");
                        }
                    });
                }
            };

            setupRibbonClickHandlers();
            const observer = new MutationObserver(setupRibbonClickHandlers);
            const formElement = document.querySelector('div[role="main"]') || document.querySelector('.o_form_sheet');
            if (formElement) observer.observe(formElement, { childList: true, subtree: true });

            const selectedRibbonPath = sessionStorage.getItem('SelectedRibbonXPath');
            if (selectedRibbonPath) {
                const selectedRibbon = document.querySelector(`div.ribbon[cy-xpath="${selectedRibbonPath}"]`);
                if (selectedRibbon) {
                    const formSheet = selectedRibbon.closest('.o_form_sheet');
                    if (formSheet) {
                        formSheet.querySelectorAll('div.ribbon[cy-xpath]').forEach(rb => {
                            rb.style.display = rb === selectedRibbon ? '' : 'none';
                        });
                    }
                }
                sessionStorage.removeItem('SelectedRibbonXPath');
            }

            return () => {
                document.removeEventListener('click', globalRibbonInterceptor, true);
                observer.disconnect();
                sortableInstances.forEach(s => s.destroy());
            };
        }, () => [this.state.isNotebookPageChange])
        //         ) {
        //             el.remove();
        //             return;
        //         }
        //
        //         if (!item) {
        //             if (original.classList.contains('kanban')) {
        //                 const vid = self.props.viewId;
        //                 self.dialogService.add(FormTreeDialog, {
        //                     resModel: self.action.currentController.props.resModel,
        //                     isKanban: true,
        //                     onConfirm: async (result) => {
        //                         const properties = {
        //                             ...result,
        //                             path,
        //                             position,
        //                             resModel: self.action.currentController.props.resModel,
        //                         };
        //                         self.env.services.ui.block();
        //                         self.rpc("cyllo_studio/add/form_tree", {
        //                             kwargs: {
        //                                 ...properties,
        //                                 view_id: vid || null,
        //                                 view_type: 'kanban',
        //                                 model: self.action.currentController.props.resModel,
        //                             }
        //                         })
        //                             .then((response) => {
        //                                 self.env.services.ui.unblock();
        //                                 if (response) {
        //                                     let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
        //                                     storedArray.push(response.replace(/\s+/g, ' ').trim());
        //                                     sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
        //                                     sessionStorage.setItem('ReDO', JSON.stringify([]));
        //                                 }
        //                                 self.action.doAction("studio_reload");
        //                             })
        //                             .catch((err) => {
        //                                 self.env.services.ui.unblock();
        //                                 throw err;
        //                             });
        //                     }
        //                 });
        //                 return;
        //             }
        //
        //             if (original.classList.contains('tree')) {
        //                 const vid = self.props.viewId;
        //                 self.dialogService.add(FormTreeDialog, {
        //                     resModel: self.action.currentController.props.resModel,
        //                     onConfirm: async (result) => {
        //                         const properties = {
        //                             ...result,
        //                             path,
        //                             position,
        //                             resModel: self.action.currentController.props.resModel,
        //                         };
        //                         self.env.services.ui.block();
        //                         const currentNotebook = document.querySelector('.o_notebook .nav-link.active');
        //                         if (currentNotebook) {
        //                             const notebookContainer = currentNotebook.closest('.o_notebook');
        //                             const notebookId = notebookContainer?.getAttribute('data-notebook-id') || 'default';
        //                             const pageIndex = Array.from(currentNotebook.parentElement.parentElement.children)
        //                                 .indexOf(currentNotebook.parentElement);
        //                             const storedPages = JSON.parse(sessionStorage.getItem("cy_studio_active_notebook") || "{}");
        //                             storedPages[notebookId] = pageIndex;
        //                             sessionStorage.setItem("cy_studio_active_notebook", JSON.stringify(storedPages));
        //                         }
        //                         self.rpc("cyllo_studio/add/form_tree", {
        //                             kwargs: {
        //                                 ...properties,
        //                                 view_id: vid ? vid : null,
        //                                 view_type: 'form',
        //                                 model: self.action.currentController.props.resModel,
        //                             }
        //                         })
        //                             .then((response) => {
        //                                 self.env.services.ui.unblock();
        //                                 if (response) {
        //                                     let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
        //                                     storedArray.push(response.replace(/\s+/g, ' ').trim());
        //                                     sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
        //                                     sessionStorage.setItem('ReDO', JSON.stringify([]));
        //                                 }
        //                                 self.action.doAction('studio_reload');
        //                             })
        //                             .catch((err) => {
        //                                 self.env.services.ui.unblock();
        //                                 throw err;
        //                             });
        //                     },
        //                 });
        //                 return;
        //             }
        //             if (original.classList.contains('chatter')) {
        //                 if (chatterComponent) chatterComponent.classList.remove('chatterContainer');
        //                 self.env.services.ui.block();
        //                 try {
        //                     const add_remove = await self.rpc("cyllo_studio/add_remove/chatter", {
        //                         model: self.props.model,
        //                         view_id: self.props.viewId,
        //                         path: "/form",
        //                         view_type: "form",
        //                         position: "inside",
        //                     });
        //                     let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
        //                     storedArray.push(add_remove.replace(/\s+/g, ' ').trim());
        //                     sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
        //                     sessionStorage.setItem('ReDO', JSON.stringify([]));
        //                 } finally {
        //                     self.env.services.ui.unblock();
        //                     self.state.hasChatter = false;
        //                     self.action.doAction('studio_reload');
        //                 }
        //                 return;
        //             }
        //
        //             if (original.classList.contains('field')) {
        //                 const fieldPath = sibling ?
        //                     sibling.firstElementChild?.firstElementChild?.getAttribute('cy-xpath') ||
        //                     sibling.firstElementChild?.getAttribute('cy-xpath') ||
        //                     (sibling.firstElementChild?.classList?.contains('fa-trash-o') ?
        //                         sibling.nextElementSibling?.firstElementChild?.getAttribute('cy-xpath') ||
        //                         sibling.nextElementSibling?.firstElementChild?.firstElementChild?.getAttribute('cy-xpath') :
        //                         null) : target.getAttribute('cy-xpath');
        //                 const fieldPosition = sibling ? 'before' : 'inside';
        //                 self.env.bus.trigger("FIELDS_DETAILS", {
        //                     cy_path: fieldPath,
        //                     position: fieldPosition,
        //                     create: true,
        //                     type: "Properties",
        //                 });
        //                 return;
        //             }
        //
        //         } else {
        //             const vid = self.props?.viewId || null;
        //             const model = self.action.currentController.action.res_model;
        //             const currentNotebook = document.querySelector('.o_notebook .nav-link.active');
        //             if (currentNotebook) {
        //                 const notebookContainer = currentNotebook.closest('.o_notebook');
        //                 const notebookId = notebookContainer?.getAttribute('data-notebook-id') || 'default';
        //                 const pageIndex = Array.from(currentNotebook.parentElement.parentElement.children)
        //                     .indexOf(currentNotebook.parentElement);
        //                 const storedPages = JSON.parse(sessionStorage.getItem("cy_studio_active_notebook") || "{}");
        //                 storedPages[notebookId] = pageIndex;
        //                 sessionStorage.setItem("cy_studio_active_notebook", JSON.stringify(storedPages));
        //             }
        //             self.env.services.ui.block();
        //             self.rpc("cyllo_studio/add/component", {
        //                 method: 'add_component',
        //                 args: [{
        //                     view_type: 'form',
        //                     view_id: vid,
        //                     path: path,
        //                     position: position,
        //                     item: item,
        //                     model: model,
        //                 }],
        //             })
        //                 .then((response) => {
        //                     self.env.services.ui.unblock();
        //                     self.action.doAction('studio_reload');
        //                     let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
        //                     storedArray.push(response.replace(/\s+/g, ' ').trim());
        //                     sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
        //                     sessionStorage.setItem('ReDO', JSON.stringify([]));
        //                     if (sessionStorage.getItem('cylloActivePagePath')) {
        //                         const newPath = sessionStorage.getItem('cylloActivePagePath');
        //                         const element = document.querySelector(`[cy-xpath="${newPath}"]`);
        //                         const firstChild = element ? element.firstElementChild : null;
        //                         if (firstChild) firstChild.click();
        //                     }
        //                 })
        //                 .catch((err) => {
        //                     self.env.services.ui.unblock();
        //                     throw err;
        //                 });
        //         }
        //     };
        //
        //     const sortableInstances = [];
        //
        //     if (component) {
        //         const sourceContainers = [component, componentElement, componentElement2, chatterComponent].filter(Boolean);
        //
        //         sourceContainers.forEach((src) => {
        //             const existing = Sortable.get(src);
        //             if (existing) {
        //                 try {
        //                     existing.destroy();
        //                 } catch (e) {
        //                 }
        //             }
        //
        //             Sortable.create(src, {
        //                 group: {
        //                     name: 'form-components',
        //                     pull: 'clone',
        //                     put: false,
        //                 },
        //                 sort: false,
        //                 animation: 150,
        //                 removeCloneOnHide: true,
        //                 onStart: function (evt) {
        //                     _originalDragEl = evt.item;
        //                     applyGhostAppearance(evt.item, evt.item);
        //                     // evt.item.style.visibility = 'hidden';
        //                     const el = evt.item;
        //                     el.classList.add('smooth-drag');
        //
        //                     if (el.classList.contains('chatter') && chatterComponent) {
        //                         chatterComponent.classList.add('chatterContainer');
        //                         const dropHereDiv = document.createElement('div');
        //                         dropHereDiv.textContent = 'Drop Here';
        //                         dropHereDiv.classList.add('drop-here-container');
        //                         chatterComponent.appendChild(dropHereDiv);
        //
        //                         function findScrollableContainer(node) {
        //                             while (node && node !== document.body) {
        //                                 const ov = window.getComputedStyle(node).overflowY;
        //                                 if (ov === 'auto' || ov === 'scroll') return node;
        //                                 node = node.parentElement;
        //                             }
        //                             return null;
        //                         }
        //
        //                         const sc = findScrollableContainer(chatterComponent);
        //                         if (sc) {
        //                             const cr = chatterComponent.getBoundingClientRect();
        //                             const scr = sc.getBoundingClientRect();
        //                             sc.scrollTo({
        //                                 top: Math.max(0, cr.top - scr.top + sc.scrollTop - sc.clientHeight / 2),
        //                                 behavior: 'smooth',
        //                             });
        //                         }
        //                     }
        //                 },
        //
        //                 onClone: function (evt) {
        //                     applyCloneAppearance(evt.clone, evt.item);
        //                 },
        //
        //                 onEnd: function (evt) {
        //                     evt.item.classList.remove('smooth-drag');
        //
        //                     if (evt.item.classList.contains('chatter')) {
        //                         if (chatterComponent) chatterComponent.classList.remove('chatterContainer');
        //                         const dh = document.querySelector('.drop-here-container');
        //                         if (dh) dh.remove();
        //                     }
        //                     if (evt.to === evt.from) {
        //                         _originalDragEl = null;
        //                     }
        //                 },
        //             });
        //
        //             sortableInstances.push(Sortable.get(src));
        //         });
        //         const targetContainers = [
        //             form,
        //             ...Array.from(form_tabs),
        //         ].filter(Boolean);
        //
        //         targetContainers.forEach((targetEl) => {
        //             const existing = Sortable.get(targetEl);
        //             if (existing) {
        //                 try {
        //                     existing.destroy();
        //                 } catch (e) {
        //                 }
        //             }
        //
        //             Sortable.create(targetEl, {
        //                 group: {
        //                     name: 'form-components',
        //                     pull: false,
        //                     put: function (to, from, dragEl) {
        //                         if ([...innerGroup].includes(from.el)) return false;
        //                         if (dragEl.classList.contains('cy-chatter-exist')) return false;
        //                         if (from.el.classList.contains('o_form_sheet') || from.el.classList.contains('tab-pane')) return false;
        //                         if (dragEl.classList.contains('chatter') && !self.state.isChatterAvailable) return false;
        //                         if (dragEl.classList.contains('chatter')) return to.el === chatterComponent;
        //                         if (dragEl.classList.contains('cy-studio-ribbon')) {
        //                             return to.el.classList.contains('o_form_sheet') || to.el.classList.contains('tab-pane');
        //                         }
        //                         if (dragEl.classList.contains('field')) return to.el.classList.contains('o_inner_group');
        //                         if (dragEl.classList.contains('tab')) return to.el.classList.contains('o_form_sheet');
        //                         return to.el.classList.contains('o_form_sheet') || to.el.classList.contains('tab-pane');
        //                     },
        //                 },
        //                 animation: 150,
        //                 ghostClass: 'sortable-ghost',
        //
        //                 onMove: function (evt) {
        //                     const related = evt.related;
        //                     if (related?.classList.contains('cy-add-avatar')) return false;
        //                     const dragEl = evt.dragged;
        //                     if (dragEl.classList.contains('field')) {
        //                         if (related?.children[0]?.classList?.contains('o_horizontal_separator')) return false;
        //                         if (related?.nextElementSibling?.children[0]?.classList?.contains('o_horizontal_separator')) return false;
        //                     }
        //                     return true;
        //                 },
        //
        //                 onAdd: async function (evt) {
        //                     const el = evt.item;
        //                     const target = evt.to;
        //                     const original = _originalDragEl || el; // fallback to el if somehow missing
        //                     applyGhostAppearance(el, original);
        //                     const children = Array.from(target.children);
        //                     const droppedIndex = children.indexOf(el);
        //                     const sibling = (droppedIndex >= 0 && droppedIndex < children.length - 1)
        //                         ? children[droppedIndex + 1]
        //                         : null;
        //
        //                     await handleDrop(el, target, sibling, original);
        //                 },
        //             });
        //
        //             sortableInstances.push(Sortable.get(targetEl));
        //         });
        //     }
        //
        //     const setupRibbonClickHandlers = () => {
        //         const ribbons = document.querySelectorAll('div.ribbon[cy-xpath]');
        //         ribbons.forEach((ribbon) => {
        //             ribbon.style.cursor = 'pointer';
        //             ribbon.style.pointerEvents = 'auto';
        //             const oldHandler = ribbon._ribbonClickHandler;
        //             if (oldHandler) ribbon.removeEventListener('click', oldHandler, true);
        //             const newHandler = handleRibbonClick.bind(null, ribbon);
        //             ribbon._ribbonClickHandler = newHandler;
        //             ribbon.addEventListener('click', newHandler, true);
        //             ribbon.querySelectorAll('*').forEach(child => {
        //                 const childHandler = (e) => {
        //                     e.stopPropagation();
        //                     e.stopImmediatePropagation();
        //                     e.preventDefault();
        //                     newHandler(e);
        //                 };
        //                 child._ribbonChildClickHandler = childHandler;
        //                 child.addEventListener('click', childHandler, true);
        //             });
        //         });
        //     };
        //
        //     const handleRibbonClick = function (ribbonElement, e) {
        //         e.stopPropagation();
        //         e.stopImmediatePropagation();
        //         e.preventDefault();
        //         const ribbonPath = ribbonElement.getAttribute('cy-xpath');
        //         if (!ribbonPath) {
        //             console.warn("No cy-xpath found on ribbon");
        //             return;
        //         }
        //         const allRibbons = document.querySelectorAll('div.ribbon[cy-xpath]');
        //         const viewId = self.props.viewId;
        //         const model = self.props.model || self.action.currentController.props.resModel;
        //         const fields = [];
        //         if (self.props.allFields) {
        //             for (const [fieldName, field] of Object.entries(self.props.allFields)) {
        //                 fields.push({value: fieldName, label: field.string});
        //             }
        //         }
        //         self.dialogService.add(RibbonDialog, {
        //             fields: fields,
        //             ribbonElement: Array.from(allRibbons),
        //             viewDetails: {
        //                 viewId: viewId,
        //                 viewType: self.props.viewType || 'form',
        //                 model: model,
        //                 active_fields: self.props.allFields,
        //                 ribbonPath: ribbonPath,
        //             },
        //         });
        //         return false;
        //     };
        //
        //     setupRibbonClickHandlers();
        //
        //     const selectedRibbonPath = sessionStorage.getItem('SelectedRibbonXPath');
        //     if (selectedRibbonPath) {
        //         const selectedRibbon = document.querySelector(`div.ribbon[cy-xpath="${selectedRibbonPath}"]`);
        //         if (selectedRibbon) {
        //             const formSheet = selectedRibbon.closest('.o_form_sheet');
        //             if (formSheet) {
        //                 formSheet.querySelectorAll('div.ribbon[cy-xpath]').forEach(rb => {
        //                     rb.style.display = rb === selectedRibbon ? '' : 'none';
        //                 });
        //             }
        //         }
        //         sessionStorage.removeItem('SelectedRibbonXPath');
        //     }
        //
        //     const formElement = document.querySelector('div[role="main"]') || document.querySelector('.o_form_sheet');
        //     if (formElement) {
        //         const observer = new MutationObserver((mutations) => {
        //             const hasNewRibbon = mutations.some(mutation =>
        //                 Array.from(mutation.addedNodes).some(node =>
        //                     node.nodeType === 1 && (node.classList?.contains('ribbon') || node.querySelector?.('div.ribbon'))
        //                 )
        //             );
        //             if (hasNewRibbon) setupRibbonClickHandlers();
        //         });
        //         observer.observe(formElement, {childList: true, subtree: true, attributes: false});
        //         window._ribbonObserver = observer;
        //     }
        //
        //     return () => {
        //         _originalDragEl = null;
        //         document.removeEventListener('click', globalRibbonInterceptor, true);
        //         document.querySelectorAll('div.ribbon[cy-xpath]').forEach((ribbon) => {
        //             if (ribbon._ribbonClickHandler) ribbon.removeEventListener('click', ribbon._ribbonClickHandler, true);
        //             ribbon.querySelectorAll('*').forEach(child => {
        //                 if (child._ribbonChildClickHandler) child.removeEventListener('click', child._ribbonChildClickHandler, true);
        //             });
        //         });
        //         if (window._ribbonObserver) window._ribbonObserver.disconnect();
        //
        //         sortableInstances.forEach(instance => {
        //             try {
        //                 if (instance && instance.el) {
        //                     instance.destroy();
        //                 }
        //             } catch (e) {
        //             }
        //         });
        //         sortableInstances.length = 0;
        //     };
        //
        // }, () => [this.state.isNotebookPageChange])

    }

    /**
     * Loads available model fields and the currently configured display name.
     * Updates `state.recordNameOptions` and `state.currentRecName`.
     */
    async loadRecordNameData() {
        const model = this.props.model;
        if (!model) {
            this.state.recordNameOptions = [];
            this.state.currentRecName = null;
            return;
        }
        const fields = await this.rpc("/cyllo_studio/get_model_fields", { model });
        this.state.recordNameOptions = fields.map(f => ({
            label: f.label,
            value: f.name,
        }));
        const data = await this.rpc("/web/dataset/call_kw/ir.model/search_read", {
            model: "ir.model",
            method: "search_read",
            args: [[["model", "=", model]], ["cy_display_field"]],
            kwargs: {},
        });
        this.state.currentRecName = data?.[0]?.cy_display_field || "";
    }

    /**
     * Saves the selected field as the display name for the model.
     * Updates backend and reloads the view to reflect the change.
     */
    onRecordNameChange = async (newValue) => {
        const model = this.props.model;
        if (!model || !newValue) return;
        await this.rpc("/cyllo_studio/set_display_name", {
            model: model,
            field: newValue,
        });
        this.state.currentRecName = newValue;
        window.location.reload();
    };

    async resetView() {
        this.dialogService.add(ConfirmationDialog, {
            title: "Reset View",
            body: "Are you sure you want to reset this view to the default version? All studio changes will be lost.",
            confirmLabel: "Reset",
            cancelLabel: "Cancel",
            confirm: async () => {
                try {
                    let view_type = this.props.viewType;
                    let view_id = this.props.viewId;

                    const searchViewId = sessionStorage.getItem("searchViewId");
                    if (searchViewId) {
                        view_type = "search";
                        view_id = searchViewId;
                    }

                    await this.rpc("/cyllo_studio/reset_view", {
                        model: this.props.model,
                        view_type: view_type,
                        view_id: view_id,
                    });

                    sessionStorage.removeItem("UndoRedo");
                    sessionStorage.removeItem("ReDO");

                } finally {
                    this.action.doAction("studio_reload");
                    window.location.reload();
                }
            },
        });
    }

    async loadDeactivatedViews() {
        const view_id = this.props.viewId;
        if (!view_id) return;
        const views = await this.rpc("/cyllo_studio/get_deactivated_views", { view_id });
        this.state.deactivatedViews = (views || []).map(v => ({
            ...v,
            displayName: `Created: ${v.create_date} [ID: ${v.id}] ${v.name} `
        }));
        this.state.selectedDeactivatedViewId = views?.[0]?.id || null;
    }

    broadcastPreviewMode = () => {
        console.log("this.state.isPreviewMode", this.state.isPreviewMode)// ✅ ADD THIS
        this.env.bus.trigger('PREVIEW_MODE_CHANGED', {
            isPreviewMode: this.state.isPreviewMode
        });
    }

    //onDeactivatedViewSelect = async (viewId) => {
    //    this.state.selectedDeactivatedViewId = viewId;
    //}
    onDeactivatedViewSelect = async (viewId) => {
        const baseViewId = this.props.viewDetails?.viewId || this.props.viewId;
        if (!viewId || !baseViewId) return;

        this.state.selectedDeactivatedViewId = viewId;
        this.state.isPreviewMode = true;
        this.isPreviewModeActive = true;
        this.broadcastPreviewMode();
        await this.rpc("/cyllo_studio/preview_view", {
            view_id: viewId,
            base_view_id: baseViewId,
        });

        this.action.doAction("studio_reload");
    }


    async cancelPreview() {
        await this.rpc("/cyllo_studio/cancel_preview", {});
        this.state.isPreviewMode = false;
        this.state.selectedDeactivatedViewId = null;
        this.broadcastPreviewMode();
        this.action.doAction("studio_reload");
    }

    async activateSelectedView() {
        const viewId = this.state.selectedDeactivatedViewId;
        const baseViewId = this.props.viewDetails?.viewId || this.props.viewId;
        if (!viewId || !baseViewId) return;

        this.dialogService.add(ConfirmationDialog, {
            title: "Activate Studio View",
            body: "This will permanently activate the previewed view. Continue?",
            confirmLabel: "Activate",
            cancelLabel: "Cancel",
            confirm: async () => {
                try {
                    // Already active from preview, just clear session + undo history
                    await this.rpc("/cyllo_studio/cancel_preview", {}); // clear session only
                    // Re-activate cleanly via the proper route
                    await this.rpc("/cyllo_studio/activate_single_view", {
                        view_id: viewId,
                        base_view_id: baseViewId,
                    });
                    this.state.isPreviewMode = false;
                    this.isPreviewModeActive = false;

                    sessionStorage.removeItem("UndoRedo");
                    sessionStorage.removeItem("ReDO");
                } finally {
                    window.location.reload()
                }
            },
        });
    }

    /**
     * Load the current button_limit attribute from the header element
     */
    async loadButtonLimitAttribute() {
        try {
            const view_id = this.props.viewId || this.props.viewDetails?.viewId;
            const model = this.props.model;

            if (!view_id || !model) {
                this.state.buttonLimitEnabled = false;
                this.state.buttonLimitValue = '';
                return;
            }

            const result = await this.rpc("/cyllo_studio/get_button_limit", {
                view_id: view_id,
                model: model
            });

            if (result && result.button_limit) {
                this.state.buttonLimitEnabled = true;
                this.state.buttonLimitValue = result.button_limit.toString();
                this.state.hasButtonLimitAttribute = true;
            } else {
                this.state.buttonLimitEnabled = false;
                this.state.buttonLimitValue = '';
                this.state.hasButtonLimitAttribute = false;
            }
        } catch (error) {
            console.error("Error loading button limit attribute:", error);
        }
    }

    /**
     * Handle checkbox toggle for button limit
     */
    async toggleButtonLimit(event) {
        const isChecked = event.target.checked;
        this.state.buttonLimitEnabled = isChecked;

        if (!isChecked) {
            await this.removeButtonLimitAttribute();
            this.state.buttonLimitValue = '';
            this.state.hasButtonLimitAttribute = false;
        }
    }

    /**
     * Handle input field changes for button limit value
     */
    async updateButtonLimitValue(event) {
        const value = event.target.value.trim();

        if (!value) {
            return;
        }

        const numValue = parseInt(value);
        if (isNaN(numValue) || numValue <= 0) {
            return;
        }

        this.state.buttonLimitValue = numValue.toString();

        try {
            this.env.services.ui.block();
            await this.saveButtonLimitAttribute(numValue);
            this.action.doAction("studio_reload");
        } catch (error) {
            console.error("Error updating button limit:", error);
        } finally {
            this.env.services.ui.unblock();
        }
    }

    /**
     * Save button_limit attribute to header element via RPC
     */
    async saveButtonLimitAttribute(value) {
        const view_id = this.props.viewId || this.props.viewDetails?.viewId;
        const model = this.props.model;

        if (!view_id || !model) {
            throw new Error("Missing required parameters: view_id or model");
        }

        const result = await this.rpc("/cyllo_studio/set_button_limit", {
            view_id: view_id,
            model: model,
            button_limit: value
        });

        if (!result.success) {
            throw new Error(result.message || "Failed to save button limit");
        }

        this.state.hasButtonLimitAttribute = true;
    }

    /**
     * Remove button_limit attribute from header element via RPC
     */
    async removeButtonLimitAttribute() {
        const view_id = this.props.viewId || this.props.viewDetails?.viewId;
        const model = this.props.model;

        if (!view_id || !model) {
            console.warn("Missing parameters for removing button limit");
            return;
        }

        try {
            this.env.services.ui.block();
            const result = await this.rpc("/cyllo_studio/remove_button_limit", {
                view_id: view_id,
                model: model
            });

            if (result.success) {
                this.state.hasButtonLimitAttribute = false;
                this.action.doAction("studio_reload");
            }
        } catch (error) {
            console.error("Error removing button limit:", error);
        } finally {
            this.env.services.ui.unblock();
        }
    }

}

FormOverall.components = {
    ...FormOverall.components,
    CylloStudioDropdown
}
