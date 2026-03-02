/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useRef, onMounted } from "@odoo/owl";
import { StudioFieldSelectorPopover } from "@cyllo_studio/js/studio_field_selector_popover";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { groupBy } from "@web/core/utils/arrays";
const Sortable = window.Sortable;
const SS_TEMPLATE = 'cyllo_report_template';
const SS_RES_MODEL = 'cyllo_report_res_model';

export class EditReport extends Component {
    setup() {
        this.reportFrameRef = useRef("report_frame");
        this.undoBtn = useRef("undoBtn");
        this.redoBtn = useRef("redoBtn");
        this.action = useService("action");
        this.popover = useService("popover");
        this.loadFieldInfo = useLoadFieldInfo();
        this.rpc = useService("rpc");

        // Track SortableJS instances so we can destroy/recreate on DOM changes
        this._sortableInstances = [];

        onMounted(async () => {
            const params = this.props.action.params || {};

            let template = params.template;
            let resModel = params.res_model;

            if (template) {
                sessionStorage.setItem(SS_TEMPLATE, template);
                sessionStorage.setItem(SS_RES_MODEL, resModel || '');
            } else {
                template = sessionStorage.getItem(SS_TEMPLATE) || '';
                resModel = sessionStorage.getItem(SS_RES_MODEL) || '';
            }

            this._template = template;
            this._resModel = resModel;

            let arch = params.arch;
            if (!arch || arch === 'undefined') {
                if (!template) {
                    console.warn('[Cyllo Studio] No template available – cannot fetch arch.');
                } else {
                    const result = await this.rpc('/cyllo_studio/get_arch', { template });
                    arch = (result && result.success) ? result.arch : '';
                    if (!result || !result.success) {
                        console.warn('[Cyllo Studio] get_arch failed:', result?.error);
                    }
                }
            }

            this._setupReportFrame(arch || '');
            this._setupSortable();
        });
    }

    _setupReportFrame(arch) {
        this._loadedArch = arch;
        this.reportFrameRef.el.innerHTML = arch;
        const editableArea = this.reportFrameRef.el;
        this.editor = null;
        $('[t-elif], [t-else]').hide();

        this.undoManager = new UndoRedoManager(editableArea, {
            maxStackSize: 50,
            debounceTime: 300,
            autoTrack: true,
            trackAttributes: true,
            keyboardShortcuts: true
        });
        this.undoManager.startTracking();

        new MutationObserver(() => {
            this.undoBtn.el.disabled = !this.undoManager?.canUndo();
            this.redoBtn.el.disabled = !this.undoManager?.canRedo();
        }).observe(editableArea, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true
        });

        const self = this;
        editableArea.addEventListener("click", function (e) {
            $('.selected').removeClass('selected');
            if ($('#branchSelector').css('display') !== 'none') self.closeBranchSelector();

            let element = e.target;
            for (let i = 0; i <= 4 && element; i++, element = element.parentElement) {
                if (['t-if', 't-elif', 't-else'].some(attr => element.hasAttribute(attr))) {
                    self.showBranchSelector(element);
                    break;
                }
            }

            let el = e.target.nodeType === 3 ? e.target.parentElement : e.target;
            if (el.classList.contains('page')) return;
            el.classList.add('selected');
            if (self.editor) self.editor.destroy();

            self.editor = new MediumEditor(el, {
                buttons: [
                    'bold', 'italic', 'underline', 'strikethrough',
                    'subscript', 'superscript', 'h1', 'h3', 'quote',
                    'anchor', 'undoButton', 'redoButton','deleteElement',
                ],
                placeholder: false,
                disableExtraSpaces: true,
            });
            self.editor.selectElement(el);
        });
    }

    undo() { this.undoManager?.undo(); }
    redo() { this.undoManager?.redo(); }

    showBranchSelector(element) {
        this.currentGroup = this.findConditionalGroup(element);
        let optionsHtml = '';
        this.currentGroup?.forEach((branch, index) => {
            let type = branch.getAttribute('t-if') ? 't-if' :
                branch.getAttribute('t-elif') ? 't-elif' : 't-else';
            let condition = branch.getAttribute(type) || '(else)';
            let isActive = $(branch).is(':visible');
            optionsHtml += `
                <div class="branch-option ${isActive ? 'active' : ''}" data-index="${index}">
                    <span class="branch-type">${type}</span>
                    <span class="branch-condition">${condition}</span>
                </div>`;
        });
        $('#branchOptions').html(optionsHtml);
        $('#branchSelector').fadeIn(200);
        const self = this;
        $('.branch-option').on('click', function () {
            const index = $(this).closest('[data-index]').data('index');
            self.switchToBranch(index);
        });
    }

    findConditionalGroup(element) {
        let group = [];
        let current = element;
        while (current && !current.hasAttribute('t-if')) {
            if (!current.hasAttribute('t-elif') && !current.hasAttribute('t-else')) break;
            current = current.previousElementSibling;
        }
        if (!current) return null;
        group.push(current);
        let next = current.nextElementSibling;
        while (next && (next.hasAttribute('t-elif') || next.hasAttribute('t-else'))) {
            group.push(next);
            if (next.hasAttribute('t-else')) break;
            next = next.nextElementSibling;
        }
        return group;
    }

    switchToBranch(index) {
        if (!this.currentGroup[index]) return;
        this.currentGroup.forEach(branch => $(branch).hide());
        $(this.currentGroup[index]).show().addClass('selected');
        $('.branch-option').removeClass('active');
        $(`[data-index="${index}"]`).addClass('active');
    }

    async closeBranchSelector() {
        $('#branchSelector').fadeOut(200);
        $('#branchOptions').html('');
        $('.selected').removeClass('selected');
        this.currentGroup = [];
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SortableJS drag-and-drop
    // ─────────────────────────────────────────────────────────────────────────

    _setupSortable() {
        this._snippetPanel = document.getElementById('snippet-panel');
        this._reportFrame = document.getElementById('studio_report');

        // Destroy any previous instances before reinitialising
        this._destroySortableInstances();

        // ── 1. Sidebar panel: clone items into drop zones ────────────────────
        const panelSortable = Sortable.create(this._snippetPanel, {
            group: {
                name: 'studio',
                pull: 'clone',   // clone from panel
                put: false,      // panel itself is source-only
            },
            sort: false,         // don't reorder panel items
            animation: 150,
            ghostClass: 'gu-transit',
            chosenClass: 'dragging',
            onClone: (evt) => {
                // Tag the clone so the onAdd handler knows it came from the panel
                evt.clone.dataset._fromPanel = '1';
            },
        });
        this._sortableInstances.push(panelSortable);

        // ── 2. Each [cy-template] zone: accept drops & allow internal moves ──
        this._reportFrame.querySelectorAll('[cy-template]').forEach(zone => {
            this._createZoneSortable(zone);
        });
    }

    /** Create (or re-create) a SortableJS instance for a single drop zone. */
    _createZoneSortable(zone) {
        const self = this;

        const instance = Sortable.create(zone, {
            group: {
                name: 'studio',
                pull: true,   // elements can be moved out of this zone
                put: true,    // elements from panel clones or other zones land here
            },
            animation: 150,
            ghostClass: 'gu-transit',
            dragClass: 'gu-mirror',
            // Only allow dragging of movable nodes (not the page/row wrappers)
            filter: '.page, .row',
            preventOnFilter: false,

            // Fired when an element from ANOTHER list (panel or other zone) is dropped here
            onAdd: async (evt) => {
                const item = evt.item;
                const fromPanel = item.dataset._fromPanel === '1';

                if (fromPanel) {
                    // Remove the placeholder node SortableJS already inserted
                    item.remove();
                    delete item.dataset._fromPanel;

                    const type = item.dataset.type;
                    let html = '';

                    if (type === 'field') {
                        const resModel = self._resModel || self.props.action.params?.res_model || '';
                        const { fieldPath, fieldInfo } = await self.openFieldSelectorPopover(
                            zone, resModel,
                            (field) => !['one2many', 'many2many'].includes(field.type),
                        );
                        if (!fieldPath) return;
                        html = `<span class="c_new"
                                t-field="doc.${fieldPath}"
                                style="cursor:grab;"
                                title="${fieldInfo.string}">${fieldPath}</span>`;
                    } else if (type === 'box') {
                        html = `<div class="box rounded-2 c_new"
                                style="border:1px solid #000;padding:10px;cursor:grab;">
                                <span>New box</span>
                            </div>`;
                    }

                    if (html) {
                        zone.insertAdjacentHTML('beforeend', html);
                        // Re-wire sortable so the newly added element is draggable
                        this._refreshDragHandles();
                    }
                }
                // For existing elements moved between zones, SortableJS handles the
                // DOM move automatically — nothing extra needed.
            },

            // After any sort/move within the same list
            onEnd: () => {
                // Nothing extra needed; DOM is already updated by SortableJS
            },
        });

        this._sortableInstances.push(instance);
    }

    /** Destroy all tracked SortableJS instances. */
    _destroySortableInstances() {
        this._sortableInstances.forEach(s => { try { s.destroy(); } catch (_) {} });
        this._sortableInstances = [];
    }

    /**
     * Re-create zone sortables so newly inserted elements participate in DnD.
     * Called after inserting new nodes into the report frame.
     */
    _refreshDragHandles() {
        // Destroy existing zone sortables (keep panel sortable alive – index 0)
        const [panelSortable, ...zoneSortables] = this._sortableInstances;
        zoneSortables.forEach(s => { try { s.destroy(); } catch (_) {} });
        this._sortableInstances = panelSortable ? [panelSortable] : [];

        // Recreate for every cy-template zone
        this._reportFrame.querySelectorAll('[cy-template]').forEach(zone => {
            this._createZoneSortable(zone);
        });
    }

    /** Kept for compatibility. */
    _reinitDrake() {
        this._refreshDragHandles();
    }

    async openFieldSelectorPopover(targetEl, resModel, filter) {
        return new Promise((resolve) => {
            this.popover.add(targetEl, StudioFieldSelectorPopover, {
                resModel,
                update: async (path) => { path = path; },
                showSearchInput: true,
                isDebugMode: (odoo.debug == 1),
                filter,
                complete: async (finalPath = null) => {
                    if (finalPath) {
                        const fieldInfo = await this.loadFieldInfo(resModel, finalPath);
                        resolve({ fieldPath: finalPath, fieldInfo: fieldInfo.fieldDef });
                    } else {
                        resolve({ fieldPath: null, fieldInfo: null });
                    }
                },
            });
        });
    }

    async close_edit(component) {
        component.action.doAction({
            name: 'Reports',
            type: 'ir.actions.act_window',
            res_model: 'ir.actions.report',
            target: 'current',
            views: [[false, 'kanban']],
        });
    }

    async save_changes(component) {
        document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
        document.querySelectorAll('[class="/"], [class=""]').forEach(el => el.removeAttribute('class'));
        $('[t-if], [t-elif], [t-else]').removeAttr('style');
        if (component.editor) component.editor.destroy();

        const editedHTML = component.reportFrameRef.el.innerHTML;
        const parser = new DOMParser();
        const editedDoc = parser.parseFromString(editedHTML, 'text/html');
        const originalDoc = parser.parseFromString(component._loadedArch || '', 'text/html');

        const changes = component.getChangedElements(originalDoc, editedDoc);
        console.log('[Cyllo Studio] Changes detected:', changes.length, changes);

        const newTemplates = component.buildInheritanceXML(changes);
        console.log('[Cyllo Studio] Sending templates:', newTemplates);

        try {
            const result = await component.rpc('/cyllo_studio/create/inherited_view', {
                all_arch: newTemplates,
            });
            console.log('[Cyllo Studio] Save result:', result);
            if (result && result['success'] === true) {
                component.close_edit(component);
            } else {
                alert('Save failed: ' + (result?.error || 'Unknown error from server'));
            }
        } catch (e) {
            console.error('[Cyllo Studio] Save RPC error:', e);
            alert('Save failed: ' + e.message);
        }
    }

    getChangedElements(originalDoc, editedDoc) {
        let allChanges = [];
        editedDoc.querySelectorAll('[cy-template]').forEach(el => {
            const xpath = el.getAttribute('cy-xpath');
            const template = el.getAttribute('cy-template');
            const original = originalDoc.querySelector(
                `[cy-template="${template}"][cy-xpath="${xpath}"]`);
            if (!original) return;

            const text = (node) => Array.from(node.childNodes)
                .filter(n => n.nodeType === 3)
                .map(n => n.textContent.trim()).join('');

            const inner = (node) => Array.from(node.children)
                .filter(c => !c.hasAttribute('cy-xpath'))
                .map(c => c.outerHTML.trim()).join('');

            const cyXpathChildren = (node) => Array.from(node.children)
                .filter(c => c.hasAttribute('cy-xpath'))
                .map(c => c.getAttribute('cy-xpath')).join(',');

            const textChanged = text(original) !== text(el);
            const innerChanged = inner(original) !== inner(el);
            const structChanged = cyXpathChildren(original) !== cyXpathChildren(el);

            if (textChanged || innerChanged || structChanged) {
                allChanges.push({ el, xpath, template });
            }
        });

        return allChanges.filter(change =>
            !allChanges.some(p => p !== change && change.xpath.startsWith(p.xpath + '/'))
        );
    }

    _cleanStudioAttrs(el) {
        const studioAttrs = ['cy-xpath', 'cy-template', 'cy-type', 'draggable'];
        const clean = (node) => {
            studioAttrs.forEach(a => node.removeAttribute && node.removeAttribute(a));
            if (node.style && node.style.cursor) node.style.removeProperty('cursor');
            if (node.style && node.style.outline) node.style.removeProperty('outline');
            Array.from(node.children || []).forEach(clean);
        };
        clean(el);
    }

    _isStructuralNode(el) {
        if (!el) return false;
        if (el.tagName && el.tagName.toLowerCase() === 't') return true;
        if (
            el.querySelector('[t-foreach]') ||
            el.querySelector('[t-set]') ||
                el.querySelector('[t-call]') ||
            el.querySelector('[t-if]') ||
            el.querySelector('[t-elif]') ||
            el.querySelector('[t-else]')
        ) return true;
        return false;
    }

    buildInheritanceXML(changes) {
        let new_inherits = [];

        for (const [key, items] of Object.entries(groupBy(changes, 'template'))) {
            let xpathBlock = "";

            items.forEach(change => {
                if (this._isStructuralNode(change.el)) {
                    console.warn("[Cyllo Studio] Skipping structural node:", change.xpath);
                    return;
                }

                const newNodes = Array.from(change.el.children)
                    .filter(child => !child.hasAttribute('cy-xpath'));

                if (newNodes.length) {
                    newNodes.forEach(node => {
                        const cloned = node.cloneNode(true);
                        this._cleanStudioAttrs(cloned);

                        let content = new XMLSerializer()
                            .serializeToString(cloned)
                            .replace(/ xmlns="[^"]*"/g, "")
                            .replace(/<br>/gi, '<br/>');

                        xpathBlock += `
    <xpath expr="${change.xpath}" position="inside">
        ${content}
    </xpath>`;
                    });
                    return;
                }

                const cloned = change.el.cloneNode(true);
                this._cleanStudioAttrs(cloned);
                cloned.querySelectorAll('[class=""]').forEach(el => el.removeAttribute('class'));

                let content = new XMLSerializer()
                    .serializeToString(cloned)
                    .replace(/ xmlns="[^"]*"/g, "")
                    .replace(/<br>/gi, '<br/>');

                xpathBlock += `
    <xpath expr="${change.xpath}" position="replace">
        ${content}
    </xpath>`;
            });

            if (xpathBlock.trim()) {
                new_inherits.push({
                    key,
                    xpathBlocks: `<data>\n${xpathBlock}\n</data>`
                });
            }
        }

        return new_inherits;
    }
}

EditReport.template = "custom_report.edit_report";
registry.category("actions").add("edit_report", EditReport);




///** @odoo-module **/
//
//import { registry } from '@web/core/registry';
//import { Component, useRef, onMounted } from "@odoo/owl";
//import { StudioFieldSelectorPopover } from "@cyllo_studio/js/studio_field_selector_popover";
//import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
//import { useService } from "@web/core/utils/hooks";
//import { usePopover } from "@web/core/popover/popover_hook";
//import { groupBy } from "@web/core/utils/arrays";
//
//// SessionStorage keys used to survive browser refreshes.
//// ir.actions.client params are NOT persisted in the URL so they are
//// lost on refresh. We store the critical identifiers here on first load.
//const SS_TEMPLATE = 'cyllo_report_template';
//const SS_RES_MODEL = 'cyllo_report_res_model';
//
//export class EditReport extends Component {
//    setup() {
//        this.reportFrameRef = useRef("report_frame");
//        this.undoBtn = useRef("undoBtn");
//        this.redoBtn = useRef("redoBtn");
//        this.action = useService("action");
//        this.popover = useService("popover");
//        this.loadFieldInfo = useLoadFieldInfo();
//        this.rpc = useService("rpc");
//        this.snippets = {
//            box: '<div class="box rounded-2 c_new" style="border:1px solid #000;padding:10px;"><span> New box</span></div>',
//        };
//
//        onMounted(async () => {
//            const params = this.props.action.params || {};
//
//            // ── Persist / restore template & res_model across refreshes ──────
//            // On first open (from kanban click) params are fully populated.
//            // On browser refresh params is stripped to routing keys only,
//            // so we fall back to sessionStorage.
//            let template = params.template;
//            let resModel = params.res_model;
//
//            if (template) {
//                // First open: save to sessionStorage for later refreshes
//                sessionStorage.setItem(SS_TEMPLATE, template);
//                sessionStorage.setItem(SS_RES_MODEL, resModel || '');
//            } else {
//                // Refresh case: restore from sessionStorage
//                template = sessionStorage.getItem(SS_TEMPLATE) || '';
//                resModel = sessionStorage.getItem(SS_RES_MODEL) || '';
//            }
//
//            // Store on instance so other methods (drag-drop) can use them
//            this._template = template;
//            this._resModel = resModel;
//
//            let arch = params.arch;
//            if (!arch || arch === 'undefined') {
//                if (!template) {
//                    console.warn('[Cyllo Studio] No template available – cannot fetch arch.');
//                } else {
//                    const result = await this.rpc('/cyllo_studio/get_arch', { template });
//                    arch = (result && result.success) ? result.arch : '';
//                    if (!result || !result.success) {
//                        console.warn('[Cyllo Studio] get_arch failed:', result?.error);
//                    }
//                }
//            }
//
//            this._setupReportFrame(arch || '');
//            this._setupDragula();
//        });
//    }
//
//    _setupReportFrame(arch) {
//        this._loadedArch = arch;                      // stored for save_changes
//        this.reportFrameRef.el.innerHTML = arch;
//        const editableArea = this.reportFrameRef.el;
//        this.editor = null;
//        $('[t-elif], [t-else]').hide();
//
//        this.undoManager = new UndoRedoManager(editableArea, {
//            maxStackSize: 50,
//            debounceTime: 300,
//            autoTrack: true,
//            trackAttributes: true,
//            keyboardShortcuts: true
//        });
//        this.undoManager.startTracking();
//
//        new MutationObserver(() => {
//            this.undoBtn.el.disabled = !this.undoManager?.canUndo();
//            this.redoBtn.el.disabled = !this.undoManager?.canRedo();
//        }).observe(editableArea, {
//            childList: true,
//            subtree: true,
//            characterData: true,
//            attributes: true
//        });
//
//        const self = this;
//        editableArea.addEventListener("click", function (e) {
//            $('.selected').removeClass('selected');
//            if ($('#branchSelector').css('display') !== 'none') self.closeBranchSelector();
//
//            let element = e.target;
//            for (let i = 0; i <= 4 && element; i++, element = element.parentElement) {
//                if (['t-if', 't-elif', 't-else'].some(attr => element.hasAttribute(attr))) {
//                    self.showBranchSelector(element);
//                    break;
//                }
//            }
//
//            let el = e.target.nodeType === 3 ? e.target.parentElement : e.target;
//            if (el.classList.contains('page')) return;
//            el.classList.add('selected');
//            if (self.editor) self.editor.destroy();
//
//            self.editor = new MediumEditor(el, {
//                buttons: [
//                    'bold', 'italic', 'underline', 'strikethrough',
//                    'subscript', 'superscript', 'h1', 'h3', 'quote',
//                    'anchor', 'undoButton', 'redoButton'
//                ],
//                placeholder: false,
//                disableExtraSpaces: true,
//            });
//            self.editor.selectElement(el);
//        });
//    }
//
//    undo() { this.undoManager?.undo(); }
//    redo() { this.undoManager?.redo(); }
//
//    showBranchSelector(element) {
//        this.currentGroup = this.findConditionalGroup(element);
//        let optionsHtml = '';
//        this.currentGroup?.forEach((branch, index) => {
//            let type = branch.getAttribute('t-if') ? 't-if' :
//                branch.getAttribute('t-elif') ? 't-elif' : 't-else';
//            let condition = branch.getAttribute(type) || '(else)';
//            let isActive = $(branch).is(':visible');
//            optionsHtml += `
//                <div class="branch-option ${isActive ? 'active' : ''}" data-index="${index}">
//                    <span class="branch-type">${type}</span>
//                    <span class="branch-condition">${condition}</span>
//                </div>`;
//        });
//        $('#branchOptions').html(optionsHtml);
//        $('#branchSelector').fadeIn(200);
//        const self = this;
//        $('.branch-option').on('click', function () {
//            const index = $(this).closest('[data-index]').data('index');
//            self.switchToBranch(index);
//        });
//    }
//
//    findConditionalGroup(element) {
//        let group = [];
//        let current = element;
//        while (current && !current.hasAttribute('t-if')) {
//            if (!current.hasAttribute('t-elif') && !current.hasAttribute('t-else')) break;
//            current = current.previousElementSibling;
//        }
//        if (!current) return null;
//        group.push(current);
//        let next = current.nextElementSibling;
//        while (next && (next.hasAttribute('t-elif') || next.hasAttribute('t-else'))) {
//            group.push(next);
//            if (next.hasAttribute('t-else')) break;
//            next = next.nextElementSibling;
//        }
//        return group;
//    }
//
//    switchToBranch(index) {
//        if (!this.currentGroup[index]) return;
//        this.currentGroup.forEach(branch => $(branch).hide());
//        $(this.currentGroup[index]).show().addClass('selected');
//        $('.branch-option').removeClass('active');
//        $(`[data-index="${index}"]`).addClass('active');
//    }
//
//    async closeBranchSelector() {
//        $('#branchSelector').fadeOut(200);
//        $('#branchOptions').html('');
//        $('.selected').removeClass('selected');
//        this.currentGroup = [];
//    }
//
//    // ─────────────────────────────────────────────────────────────────────────
//    // Native HTML5 drag-and-drop (replaces dragula – no library dependency)
//    // ─────────────────────────────────────────────────────────────────────────
//
//    _setupDragula() {
//        this._snippetPanel = document.getElementById('snippet-panel');
//        this._reportFrame = document.getElementById('studio_report');
//        this._dragType = null;   // 'panel' | 'existing'
//        this._dragEl = null;   // element being dragged (existing only)
//        this._dragGhost = null;   // custom ghost node
//        this._lastOver = null;   // last highlighted drop zone
//
//        // ── 1. Make sidebar panel items draggable ────────────────────────────
//        this._snippetPanel.querySelectorAll('[data-type]').forEach(item => {
//            item.setAttribute('draggable', 'true');
//
//            item.addEventListener('dragstart', (e) => {
//                this._dragType = 'panel';
//                this._dragEl = null;
//                e.dataTransfer.setData('text/plain', item.dataset.type);
//                e.dataTransfer.effectAllowed = 'copy';
//                item.classList.add('dragging');
//            });
//
//            item.addEventListener('dragend', () => {
//                item.classList.remove('dragging');
//                this._clearHighlight();
//            });
//        });
//
//        // ── 2. Make existing report elements draggable ───────────────────────
//        this._refreshDragHandles();
//
//        // ── 3. Wire drop zone events on the report frame ─────────────────────
//        this._reportFrame.addEventListener('dragover', (e) => {
//            const zone = this._dropZoneFor(e.target);
//            if (!zone) { e.dataTransfer.dropEffect = 'none'; return; }
//            e.preventDefault();
//            e.dataTransfer.dropEffect = this._dragType === 'panel' ? 'copy' : 'move';
//            if (zone !== this._lastOver) {
//                this._clearHighlight();
//                zone.classList.add('gu-over');
//                this._lastOver = zone;
//            }
//        });
//
//        this._reportFrame.addEventListener('dragleave', (e) => {
//            // Only clear when leaving the frame entirely
//            if (!this._reportFrame.contains(e.relatedTarget)) {
//                this._clearHighlight();
//            }
//        });
//
//        this._reportFrame.addEventListener('drop', async (e) => {
//            e.preventDefault();
//            this._clearHighlight();
//
//            const zone = this._dropZoneFor(e.target);
//            if (!zone) return;
//
//            if (this._dragType === 'panel') {
//                // ── Panel item dropped ──────────────────────────────────────
//                const type = e.dataTransfer.getData('text/plain');
//                let html = '';
//
//                if (type === 'field') {
//                    const resModel = this._resModel || this.props.action.params?.res_model || '';
//                    const { fieldPath, fieldInfo } = await this.openFieldSelectorPopover(
//                        zone, resModel,
//                        (field) => !['one2many', 'many2many'].includes(field.type),
//                    );
//                    if (!fieldPath) return;
//                    // Plain t-field span — identical style to existing report fields
//                    html = `<span class="c_new"
//                            t-field="doc.${fieldPath}"
//                            draggable="true"
//                            style="cursor:grab;"
//                            title="${fieldInfo.string}">${fieldPath}</span>`;
////                    html = `<span class="c_new" t-field="doc.${fieldPath}"
////                        draggable="true"
////                        style="cursor:grab;border-bottom:2px solid #5b8dee;"
////                        title="${fieldInfo.string}">${fieldPath}</span>`;
//                } else if (type === 'box') {
//                    html = `<div class="box rounded-2 c_new" draggable="true"
//                        style="border:1px solid #000;padding:10px;cursor:grab;">
//                        <span>New box</span>
//                    </div>`;
//                }
//
//                if (html) {
//                    zone.insertAdjacentHTML('beforeend', html);
//                    this._refreshDragHandles();
//                }
//
//            } else if (this._dragType === 'existing' && this._dragEl) {
//                zone.appendChild(this._dragEl);
//                this._dragEl = null;
//            }
//
//            this._dragType = null;
//        });
//    }
//
//    /** Returns the nearest [cy-template] container element for a drop target. */
//    _dropZoneFor(target) {
//        if (!target) return null;
//        // Walk up from the hovered element until we find the [cy-template] node itself
//        let el = (target instanceof Element) ? target : target.parentElement;
//        while (el && el !== this._reportFrame) {
//            if (el.hasAttribute('cy-template')) return el;
//            el = el.parentElement;
//        }
//        return null;
//    }
//
//    /** Attach drag events to all draggable report elements. */
//    _refreshDragHandles() {
//        const isMovable = (el) => {
//            if (el.classList.contains('page') || el.classList.contains('row')) return false;
//            return el.closest('[cy-xpath]') !== null ||
//                el.classList.contains('c_new') ||
//                !!el.closest('.c_new');
//        };
//
//        this._reportFrame.querySelectorAll('[cy-xpath], .c_new').forEach(el => {
//            if (!isMovable(el)) return;
//
//            // Re-attach every time to ensure fresh bindings after DOM changes.
//            // Use a named function so removeEventListener can clean up first.
//            if (el._onDragStart) el.removeEventListener('dragstart', el._onDragStart);
//            if (el._onDragEnd) el.removeEventListener('dragend', el._onDragEnd);
//
//            el.setAttribute('draggable', 'true');
//            el.style.cursor = 'grab';
//
//            el._onDragStart = (e) => {
//                e.stopPropagation();
//                this._dragType = 'existing';
//                this._dragEl = el;
//                e.dataTransfer.effectAllowed = 'move';
//                e.dataTransfer.setData('text/plain', 'existing');
//                setTimeout(() => el.classList.add('gu-transit'), 0);
//            };
//
//            el._onDragEnd = () => {
//                el.classList.remove('gu-transit');
//                this._clearHighlight();
//                this._dragType = null;
//                this._dragEl = null;
//            };
//
//            el.addEventListener('dragstart', el._onDragStart);
//            el.addEventListener('dragend', el._onDragEnd);
//        });
//    }
//
//    _clearHighlight() {
//        if (this._lastOver) {
//            this._lastOver.classList.remove('gu-over');
//            this._lastOver = null;
//        }
//    }
//
//    /** Kept for compatibility – re-runs setup so new elements get drag handles. */
//    _reinitDrake() {
//        this._refreshDragHandles();
//    }
//
//    async openFieldSelectorPopover(targetEl, resModel, filter) {
//        return new Promise((resolve) => {
//            this.popover.add(targetEl, StudioFieldSelectorPopover, {
//                resModel,
//                update: async (path) => { path = path; },
//                showSearchInput: true,
//                isDebugMode: (odoo.debug == 1),
//                filter,
//                complete: async (finalPath = null) => {
//                    if (finalPath) {
//                        const fieldInfo = await this.loadFieldInfo(resModel, finalPath);
//                        resolve({ fieldPath: finalPath, fieldInfo: fieldInfo.fieldDef });
//                    } else {
//                        resolve({ fieldPath: null, fieldInfo: null });
//                    }
//                },
//            });
//        });
//    }
//
//    async close_edit(component) {
//        component.action.doAction({
//            name: 'Reports',
//            type: 'ir.actions.act_window',
//            res_model: 'ir.actions.report',
//            target: 'current',
//            views: [[false, 'kanban']],
//        });
//    }
//
//    async save_changes(component) {
//        document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
//        document.querySelectorAll('[class="/"], [class=""]').forEach(el => el.removeAttribute('class'));
//        $('[t-if], [t-elif], [t-else]').removeAttr('style');
//        if (component.editor) component.editor.destroy();
//
//        const editedHTML = component.reportFrameRef.el.innerHTML;
//        const parser = new DOMParser();
//        const editedDoc = parser.parseFromString(editedHTML, 'text/html');
//        const originalDoc = parser.parseFromString(component._loadedArch || '', 'text/html');
//
//        const changes = component.getChangedElements(originalDoc, editedDoc);
//        console.log('[Cyllo Studio] Changes detected:', changes.length, changes);
//
//        const newTemplates = component.buildInheritanceXML(changes);
//        console.log('[Cyllo Studio] Sending templates:', newTemplates);
//
//        try {
//            const result = await component.rpc('/cyllo_studio/create/inherited_view', {
//                all_arch: newTemplates,
//            });
//            console.log('[Cyllo Studio] Save result:', result);
//            if (result && result['success'] === true) {
//                component.close_edit(component);
//            } else {
//                alert('Save failed: ' + (result?.error || 'Unknown error from server'));
//            }
//        } catch (e) {
//            console.error('[Cyllo Studio] Save RPC error:', e);
//            alert('Save failed: ' + e.message);
//        }
//    }
//
//    getChangedElements(originalDoc, editedDoc) {
//        let allChanges = [];
//        editedDoc.querySelectorAll('[cy-template]').forEach(el => {
//            const xpath = el.getAttribute('cy-xpath');
//            const template = el.getAttribute('cy-template');
//            const original = originalDoc.querySelector(
//                `[cy-template="${template}"][cy-xpath="${xpath}"]`);
//            if (!original) return;
//
//            // Compare direct text nodes
//            const text = (node) => Array.from(node.childNodes)
//                .filter(n => n.nodeType === 3)
//                .map(n => n.textContent.trim()).join('');
//
//            // Compare children WITHOUT cy-xpath (i.e. newly dropped elements)
//            const inner = (node) => Array.from(node.children)
//                .filter(c => !c.hasAttribute('cy-xpath'))
//                .map(c => c.outerHTML.trim()).join('');
//
//            // Compare children WITH cy-xpath (detect removals/reorders)
//            const cyXpathChildren = (node) => Array.from(node.children)
//                .filter(c => c.hasAttribute('cy-xpath'))
//                .map(c => c.getAttribute('cy-xpath')).join(',');
//
//            const textChanged = text(original) !== text(el);
//            const innerChanged = inner(original) !== inner(el);
//            const structChanged = cyXpathChildren(original) !== cyXpathChildren(el);
//
//            if (textChanged || innerChanged || structChanged) {
//                allChanges.push({ el, xpath, template });
//            }
//        });
//
//        // Only send top-most changed elements
//        return allChanges.filter(change =>
//            !allChanges.some(p => p !== change && change.xpath.startsWith(p.xpath + '/'))
//        );
//    }
//
//    /**
//     * Strips all studio-injected attrs from el and every descendant.
//     * Must be called BEFORE serializing so these never land in saved QWeb.
//     */
//    _cleanStudioAttrs(el) {
//        const studioAttrs = ['cy-xpath', 'cy-template', 'cy-type', 'draggable'];
//        const clean = (node) => {
//            studioAttrs.forEach(a => node.removeAttribute && node.removeAttribute(a));
//            if (node.style && node.style.cursor) node.style.removeProperty('cursor');
//            // Also strip the dashed outline added to newly dropped field spans
//            if (node.style && node.style.outline) node.style.removeProperty('outline');
//            Array.from(node.children || []).forEach(clean);
//        };
//        clean(el);
//    }
//    _isStructuralNode(el) {
//    if (!el) return false;
//
//    // If the element itself is a QWeb control tag
//    if (el.tagName && el.tagName.toLowerCase() === 't') {
//        return true;
//    }
//
//    // If it contains QWeb execution logic
//    if (
//        el.querySelector('[t-foreach]') ||
//        el.querySelector('[t-set]') ||
//        el.querySelector('[t-call]') ||
//        el.querySelector('[t-if]') ||
//        el.querySelector('[t-elif]') ||
//        el.querySelector('[t-else]')
//    ) {
//        return true;
//    }
//
//    return false;
//}
//
//buildInheritanceXML(changes) {
//    let new_inherits = [];
//
//    for (const [key, items] of Object.entries(groupBy(changes, 'template'))) {
//
//        let xpathBlock = "";
//
//        items.forEach(change => {
//
//            if (this._isStructuralNode(change.el)) {
//                console.warn("[Cyllo Studio] Skipping structural node:", change.xpath);
//                return;
//            }
//
//            // ✅ Detect new children properly
//            const newNodes = Array.from(change.el.children)
//                .filter(child => !child.hasAttribute('cy-xpath'));
//
//            if (newNodes.length) {
//
//                newNodes.forEach(node => {
//
//                    const cloned = node.cloneNode(true);
//                    this._cleanStudioAttrs(cloned);
//
//                    let content = new XMLSerializer()
//                        .serializeToString(cloned)
//                        .replace(/ xmlns="[^"]*"/g, "")
//                        .replace(/<br>/gi, '<br/>');
//
//                    xpathBlock += `
//    <xpath expr="${change.xpath}" position="inside">
//        ${content}
//    </xpath>`;
//                });
//
//                return;
//            }
//
//            // Fallback: full replace for text edit
//            const cloned = change.el.cloneNode(true);
//            this._cleanStudioAttrs(cloned);
//
//            cloned.querySelectorAll('[class=""]').forEach(el =>
//                el.removeAttribute('class')
//            );
//
//            let content = new XMLSerializer()
//                .serializeToString(cloned)
//                .replace(/ xmlns="[^"]*"/g, "")
//                .replace(/<br>/gi, '<br/>');
//
//            xpathBlock += `
//    <xpath expr="${change.xpath}" position="replace">
//        ${content}
//    </xpath>`;
//        });
//
//        if (xpathBlock.trim()) {
//            new_inherits.push({
//                key,
//                xpathBlocks: `<data>
//${xpathBlock}
//</data>`
//            });
//        }
//    }
//
//    return new_inherits;
//}
////    buildInheritanceXML(changes) {
////        let new_inherits = [];
////        for (const [key, items] of Object.entries(groupBy(changes, 'template'))) {
////            let xpathBlock = "";
////            items.forEach(change => {
////                // Deep-clean ALL studio attrs from the element and all its children
////                // before serializing — prevents draggable, cy-xpath, cursor etc.
////                // from leaking into the saved QWeb template and breaking rendering.
////                this._cleanStudioAttrs(change.el);
////
////                // Use XMLSerializer but ensure we deal with <t> tags which
////                // the browser might have morphed if cy-type wasn't preserved perfectly.
////                // The backend parser expects valid XML.
////                let content = new XMLSerializer().serializeToString(change.el)
////                    .replace(/ xmlns="[^"]*"/g, "")
////                    .replace(/<br>/gi, '<br/>');
////
////                // Fix <t> tags that were converted to generic spans/divs by medium-editor or the DOM
////                // if they had a cy-type="t" (though we just stripped it, so we rely on t-* attributes if we needed to).
////                // Actually, the parser handles <t> natively if it was in the DOM as <t>.
////                // Odoo's get_iframe_rendered_template injects QWeb natively.
////
////                xpathBlock += `\n    <xpath expr="${change.xpath}" position="replace">${content}</xpath>`;
////            });
////            new_inherits.push({ key, xpathBlocks: `<data>\n    ${xpathBlock}\n</data>` });
////        }
////        return new_inherits;
////    }
//}
//
//EditReport.template = "custom_report.edit_report";
//registry.category("actions").add("edit_report", EditReport);