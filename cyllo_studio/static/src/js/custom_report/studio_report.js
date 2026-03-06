/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useRef, onMounted, useState, onWillStart } from "@odoo/owl";
import { StudioFieldSelectorPopover } from "@cyllo_studio/js/studio_field_selector_popover";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { usePopover } from "@web/core/popover/popover_hook";
import { groupBy } from "@web/core/utils/arrays";
const Sortable = window.Sortable;
const SS_TEMPLATE = 'cyllo_report_template';
const SS_RES_MODEL = 'cyllo_report_res_model';

const PAPER_FORMAT_MAP = {
    'A0': [841, 1189], 'A1': [594, 841], 'A2': [420, 594], 'A3': [297, 420],
    'A4': [210, 297], 'A5': [148, 210], 'A6': [105, 148], 'A7': [74, 105],
    'A8': [52, 74], 'A9': [37, 52], 'B0': [1000, 1414], 'B1': [707, 1000],
    'B2': [500, 707], 'B3': [353, 500], 'B4': [250, 353], 'B5': [176, 250],
    'B6': [125, 176], 'B7': [88, 125], 'B8': [62, 88], 'B9': [44, 62],
    'B10': [31, 44], 'C5E': [163, 229], 'Comm10E': [105, 241], 'DLE': [110, 220],
    'Executive': [184, 267], 'Folio': [210, 330], 'Ledger': [432, 279],
    'Legal': [216, 356], 'Letter': [216, 279], 'Tabloid': [279, 432]
};

export class EditReport extends Component {
    setup() {
        this.reportFrameRef = useRef("report_frame");
        this.undoBtn = useRef("undoBtn");
        this.redoBtn = useRef("redoBtn");
        this.aceEditorRef = useRef("aceEditor");
        this.action = useService("action");
        this.popover = useService("popover");
        this.loadFieldInfo = useLoadFieldInfo();
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            previewMode: false,
            records: [],
            currentIndex: 0,
            reportInfo: {},
            paperFormats: [],
            previewHtml: false,
            showSourceEditor: false,
            sourceCode: "",
            showResetDialog: false,
            includeHeaderFooter: true,
        });

        // Track SortableJS instances so we can destroy/recreate on DOM changes
        this._sortableInstances = [];
        this._isDragging = false;

        onWillStart(async () => {
            await loadJS("/web/static/lib/ace/ace.js");
        });

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
            if (self.state.previewMode) return;
            if (self._isDragging) return;

            let el = e.target.nodeType === 3 ? e.target.parentElement : e.target;
            if (el.classList.contains('page')) {
                $('.selected').removeClass('selected');
                if (self.editor) self.editor.destroy();
                return;
            }

            const wasSelected = el.classList.contains('selected');

            $('.selected').removeClass('selected');
            if ($('#branchSelector').css('display') !== 'none') self.closeBranchSelector();

            let element = e.target;
            for (let i = 0; i <= 4 && element; i++, element = element.parentElement) {
                if (['t-if', 't-elif', 't-else'].some(attr => element.hasAttribute(attr))) {
                    self.showBranchSelector(element);
                    break;
                }
            }

            el.classList.add('selected');

            // "Select then Edit" strategy:
            // Only trigger the editor if the element was ALREADY selected.
            // This ensures the first click just selects it, making it draggable.
            if (!wasSelected) {
                if (self.editor) {
                    self.editor.destroy();
                    self.editor = null;
                }
                return;
            }

            if (self.editor) self.editor.destroy();

            self.editor = new MediumEditor(el, {
                toolbar: {
                    buttons: [
                        'bold', 'italic', 'underline', 'strikethrough',
                        'h1', 'h3', 'quote', 'anchor', 'deleteElement',
                    ],
                },
                extensions: {
                    'deleteElement': new window.DeleteButton(),
                    'undoButton': new window.UndoButton(),
                    'redoButton': new window.RedoButton(),
                },
                owner: self,
                placeholder: false,
                disableExtraSpaces: true,
            });
            self.editor.selectElement(el);
        });
    }

    togglePreview() {
        this.state.previewMode = !this.state.previewMode;
        if (this.state.previewMode) {
            // Destroy the medium editor if it's active
            if (this.editor) {
                this.editor.destroy();
                this.editor = null;
            }
            // Remove selection highlight
            $('.selected').removeClass('selected');
            // Disable drag and drop
            this._destroySortableInstances();
        } else {
            // Re-enable drag and drop
            setTimeout(() => {
                this._setupReportFrame(this._loadedArch);
                this._setupSortable();
            }, 0);
        }
        if (this.state.previewMode) {
            this._fetchPreviewData();
        }
    }

    async _fetchPreviewData() {
        const data = await this.rpc("/cyllo_studio/get_report_preview_data", {
            template: this._template,
            res_model: this._resModel,
        });
        if (data.success) {
            this.state.records = data.record_ids;
            this.state.reportInfo = data.report;
            this.state.paperFormats = data.paper_formats;
            if (this.state.records.length > 0) {
                this._loadRealReport(this.state.records[0]);
            }
        }
    }

    async _loadRealReport(docId) {
        const res = await this.rpc("/cyllo_studio/render_report_html", {
            report_id: this.state.reportInfo.id,
            doc_ids: [docId],
        });
        if (res.success) {
            this.state.previewHtml = res.html;
        }
    }

    onPrevRecord() {
        if (this.state.currentIndex > 0) {
            this.state.currentIndex--;
            this._loadRealReport(this.state.records[this.state.currentIndex]);
        }
    }

    onNextRecord() {
        if (this.state.currentIndex < this.state.records.length - 1) {
            this.state.currentIndex++;
            this._loadRealReport(this.state.records[this.state.currentIndex]);
        }
    }

    async onReportPropertyChange(field, value) {
        if (field === "paperformat_id") {
            value = value ? parseInt(value) : false;
        }

        this.state.reportInfo[field] = value;

        await this.orm.write(
            "ir.actions.report",
            [this.state.reportInfo.id],
            { [field]: value }
        );

        if (this.state.previewMode) {
            await this._fetchPreviewData();
        }
    }

    async onEditSources() {
        this.state.showSourceEditor = !this.state.showSourceEditor;
        if (this.state.showSourceEditor) {
            const res = await this.rpc('/cyllo_studio/get_report_source', {
                template: this._template,
            });
            if (res.success) {
                this.state.sourceCode = res.arch;
                // Store the resolved document template name so we save to the right view
                this._docTemplate = res.doc_template || this._template;
                this._initAceEditor();
            } else {
                this.notification.add(res.error, { type: "danger" });
                this.state.showSourceEditor = false;
            }
        }
    }

    _initAceEditor() {
        setTimeout(() => {
            const editorEl = this.aceEditorRef.el;
            console.log("[EditSources] Initializing Ace. Element:", editorEl, "window.ace:", !!window.ace);
            if (editorEl && window.ace) {
                if (this.aceEditor) {
                    this.aceEditor.destroy();
                }
                this.aceEditor = ace.edit(editorEl);
                this.aceEditor.setTheme("ace/theme/monokai");
                this.aceEditor.session.setMode("ace/mode/xml");

                const code = this.state.sourceCode || "<!-- No source code found -->";
                this.aceEditor.setValue(code, -1);

                this.aceEditor.on('change', () => {
                    this.state.sourceCode = this.aceEditor.getValue();
                });
                console.log("[EditSources] Ace initialized with content length:", code.length);
            } else {
                console.error("[EditSources] Could not initialize Ace. Element:", !!editorEl, "Lib:", !!window.ace);
                if (!window.ace) {
                    this.notification.add("Ace library not loaded yet", { type: "warning" });
                }
            }
        }, 500);
    }

    async onSaveSource() {
        const res = await this.rpc('/cyllo_studio/save_report_source', {
            template: this._template,
            doc_template: this._docTemplate || this._template,
            arch: this.state.sourceCode,
        });
        if (res.success) {
            this.notification.add("Source saved successfully", { type: "success" });
            if (this.state.previewMode) {
                await this._fetchPreviewData();
            }
        } else {
            this.notification.add(res.error, { type: "danger" });
        }
    }

    onResetReport() {
        // Show the confirmation dialog
        this.state.showResetDialog = true;
    }

    async confirmResetReport() {
        this.state.showResetDialog = false;
        const res = await this.rpc('/cyllo_studio/reset_report_source', {
            template: this._template,
            include_header_footer: this.state.includeHeaderFooter,
        });
        if (res.success) {
            this.notification.add("Report reset to factory settings", { type: "success" });
            // If source editor is open, refresh it with the reset arch
            if (this.state.showSourceEditor && res.arch) {
                this.state.sourceCode = res.arch;
                if (this.aceEditor) {
                    this.aceEditor.setValue(res.arch, -1);
                }
            }
            // Reload the editor preview
            const result = await this.rpc('/cyllo_studio/get_arch', { template: this._template });
            if (result && result.success) {
                this._loadedArch = result.arch;
                if (!this.state.previewMode) {
                    this._setupReportFrame(result.arch);
                    this._setupSortable();
                } else {
                    await this._fetchPreviewData();
                }
            }
        } else {
            this.notification.add(res.error || "Reset failed", { type: "danger" });
        }
    }

    onPrintReport() {
        const report = this.state.reportInfo;
        const activeId = this.state.records[this.state.currentIndex];
        if (!report.id || !activeId) return;

        this.action.doAction({
            type: 'ir.actions.report',
            report_name: report.report_name,
            report_type: 'qweb-pdf',
            res_model: report.model,
            context: {
                active_ids: [activeId],
                active_model: report.model,
            }
        });
    }

    get currentPaperFormat() {
        if (!this.state.reportInfo.paperformat_id) return null;
        const format = this.state.paperFormats.find(f => f.id === this.state.reportInfo.paperformat_id);
        if (format) {
            let width = format.page_width;
            let height = format.page_height;
            if ((!width || !height) && PAPER_FORMAT_MAP[format.format]) {
                [width, height] = PAPER_FORMAT_MAP[format.format];
            }
            return { ...format, page_width: width || 210, page_height: height || 297 };
        }
        return null;
    }
    //    async onReportPropertyChange(field, value) {
    //        console.log('valueee',value,this)
    //        this.state.reportInfo[field] = value;
    //        await this.rpc("/web/dataset/call_kw/ir.actions.report/write", {
    //            model: "ir.actions.report",
    //            method: "write",
    //            args: [[this.state.reportInfo.id], { [field]: value }],
    //            kwargs: {},
    //        });
    //    }

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
        //        this._reportFrame = document.getElementById('studio_report');
        this._reportFrame = this.reportFrameRef.el
        console.log('test', this.reportFrameRef.el)
        if (!this._reportFrame) return;
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
            onStart: () => {
                this._isDragging = true;
                if (this.editor) {
                    this.editor.destroy();
                    this.editor = null;
                }
                $('.selected').removeClass('selected');
            },
            onEnd: () => {
                console.log('njnjnjnjnj')
                this._isDragging = false;
                this._justDragged = true;
                setTimeout(() => { this._justDragged = false; }, 300);
            },
            onClone: (evt) => {
                // Tag the item being dragged (the "real" drop candidate)
                // so the onAdd handler knows it came from the panel
                evt.item.dataset._fromPanel = '1';
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
                pull: true,
                put: true,
            },
            animation: 150,

            onStart() {
                self._isDragging = true;
                if (self.editor) {
                    self.editor.destroy();
                    self.editor = null;
                }
                $('.selected').removeClass('selected');
            },

            onEnd() {
                self._isDragging = false;
            },

            async onAdd(evt) {
                console.log("DROP", evt);
                console.log(self.reportFrameRef.el.querySelectorAll('[cy-template]'))
                const item = evt.item;
                const fromPanel = item.dataset._fromPanel === '1';

                if (!fromPanel) return;

                const type = item.dataset.type; // read BEFORE anything
                delete item.dataset._fromPanel;

                // hide while async runs
                item.style.opacity = '0.4';

                if (type === 'field') {
                    const resModel = self._resModel || self.props.action.params?.res_model || '';

                    const { fieldPath, fieldInfo } =
                        await self.openFieldSelectorPopover(
                            zone,
                            resModel,
                            (field) => !['one2many', 'many2many'].includes(field.type),
                        );

                    if (!fieldPath) {
                        console.log('mdnjdnjdnjd')
                        item.remove(); // cancelled
                        return;
                    }

                    // transform existing dropped node
                    item.className = 'c_new';
                    item.innerHTML = fieldPath;
                    item.setAttribute('t-field', `doc.${fieldPath}`);
                    item.setAttribute('title', fieldInfo.string);
                    item.setAttribute('cy-type', 'dynamic');
                    item.style.cursor = 'grab';
                    item.style.opacity = '1';
                }

                if (type === 'box') {
                    item.className = 'box rounded-2 c_new';
                    item.innerHTML = '<span>New box</span>';
                    item.setAttribute('cy-type', 'box');
                    item.style.border = '1px solid #000';
                    item.style.padding = '10px';
                    item.style.cursor = 'grab';
                    item.style.opacity = '1';
                }
            }
        });

        this._sortableInstances.push(instance);
    }

    /** Destroy all tracked SortableJS instances. */
    _destroySortableInstances() {
        this._sortableInstances.forEach(s => { try { s.destroy(); } catch (_) { } });
        this._sortableInstances = [];
    }

    /**
     * Re-create zone sortables so newly inserted elements participate in DnD.
     * Called after inserting new nodes into the report frame.
     */
    _refreshDragHandles() {
        // Destroy existing zone sortables (keep panel sortable alive – index 0)
        const [panelSortable, ...zoneSortables] = this._sortableInstances;
        zoneSortables.forEach(s => { try { s.destroy(); } catch (_) { } });
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
                if (component.state.previewMode) {
                    component.notification.add("Report saved successfully", { type: "success" });
                    await component._fetchPreviewData();
                } else {
                    component.close_edit(component);
                }
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
                    console.warn("[Cyllo Studio] Skipping structural/table node:", change.xpath);
                    return;
                }

                // Safety net: skip any xpath that targets table internals
                const unsafeSegments = ['tbody', 'thead', 'tfoot', '/tr', '/td', '/th'];
                if (unsafeSegments.some(seg => change.xpath.includes(seg))) {
                    console.warn("[Cyllo Studio] Skipping unsafe table xpath:", change.xpath);
                    return;
                }

                // ── FIX: only use c_new nodes (freshly dropped) as "inside" inserts.
                // Previously ALL non-cy-xpath children triggered an "inside" insert,
                // causing already-saved content to be re-inserted on every save.
                const newNodes = Array.from(change.el.children)
                    .filter(child => !child.hasAttribute('cy-xpath') && child.classList.contains('c_new'));

                if (newNodes.length) {
                    newNodes.forEach(node => {
                        const cloned = node.cloneNode(true);
                        this._cleanStudioAttrs(cloned);
                        // Strip the c_new marker so it isn't saved into the template
                        cloned.classList.remove('c_new');

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

                // Text-only edit: replace the element
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

