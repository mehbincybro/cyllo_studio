/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useRef, onMounted, useState, onWillStart, onPatched } from "@odoo/owl";
import { StudioFieldSelectorPopover } from "@cyllo_studio/js/studio_field_selector_popover";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { usePopover } from "@web/core/popover/popover_hook";
import { groupBy } from "@web/core/utils/arrays";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

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
        this.dialog = useService("dialog");

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
            // ── Table Config Modal state ──
            showTableModal: false,
            isSaving: false,
            tcm: this._getDefaultTcmState(),
            // ── QR Wizard state ──
            showQrWizard: false,
            qr: this._getDefaultQrState(),
            hasThumbnail: this.props.action.params.has_thumbnail || false,
            // ── Box Properties Panel state ──
            showBoxProps: false,
            boxConfig: {
                label: 'Section',
                width: 300,
                height: 200,
                backgroundColor: 'transparent',
                border: '1px solid #ccc',
                borderRadius: 4,
                padding: 8,
                layoutMode: 'free',
            },
        });

        // Promise resolver for the table config modal
        this._tcmResolve = null;

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
            this._reportId = params.report_id || null;

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

        onPatched(() => {
            // Re-setup sortable if the component was patched (e.g. after modal close)
            // to ensure listeners are still attached to the live DOM elements.
            this._setupSortable();
        });
    }

    _setupReportFrame(arch) {
        this._loadedArch = arch;
        this.reportFrameRef.el.innerHTML = arch;
        const editableArea = this.reportFrameRef.el;

        // Enrich existing DOM with Studio wrappers/handles
        this._enrichReportDOM(editableArea);

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

        // ── QR Block Internal Click Handler ──
        editableArea.addEventListener("click", (e) => {
            const qrBlock = e.target.closest('.s_qr_block');
            if (qrBlock && e.target.classList.contains('qr-edit-btn')) {
                e.preventDefault();
                e.stopPropagation();
                this.openQrWizard(qrBlock, 'edit').then(config => {
                    if (config) this.insertQrBlock(qrBlock, config, 'update');
                });
            }
        });

        const self = this;
        editableArea.addEventListener("click", function (e) {
            if (self.state.previewMode) return;
            if (self._isDragging) return;

            let el = e.target.nodeType === 3 ? e.target.parentElement : e.target;
            if (el.classList.contains('page')) {
                $('.selected').removeClass('selected');
                if (self.editor) self.editor.destroy();
                // Close box props when clicking canvas background
                self.closeBoxProps();
                return;
            }

            // ── Box toolbar / resize handle – ignore for selection ──
            if (el.closest('.box-toolbar') || el.closest('.box-resize-handles')) {
                return;
            }

            // ── Box drop zone click logic ──
            // If the click target is INSIDE a box dropzone, select the child element
            // (not the box wrapper) unless the click is directly on the dropzone itself.
            const boxWrapper = el.closest('.box-section-wrapper');
            const boxDropzone = el.closest('.box-dropzone');
            if (boxWrapper) {
                if (el === boxWrapper || el === boxDropzone) {
                    // Clicked the box itself (not a child) – select box
                    e.stopPropagation();
                    $('.selected').removeClass('selected');
                    boxWrapper.classList.add('selected');
                    self.openBoxProps(boxWrapper);
                    return;
                } else {
                    // Clicked a child inside the box – close box props, let normal selection flow
                    e.stopPropagation();
                    self.closeBoxProps();
                    // Fall through to normal selection logic below with el unchanged
                }
            } else {
                // Clicked outside any box – close box props panel
                self.closeBoxProps();
            }

            // If we clicked something inside a table, we might want to select the cell OR the whole table.
            // Requirement says: clicking border/edge selects entire table.
            const tableWrapper = el.closest('.table-wrapper');
            const isHandle = el.classList.contains('table-handle') || el.closest('.table-handle') || el.classList.contains('table-toolbar') || el.closest('.table-toolbar');
            const isInCell = el.closest('td, th');

            if (isHandle && tableWrapper) {
                el = tableWrapper;
            } else if (isInCell) {
                // If we click inside a cell, select the cell and STOP PROPAGATION
                // so we don't accidentally select the table wrapper.
                el = isInCell;
                if (!self.state.previewMode) {
                    e.stopPropagation();
                }
            } else if (tableWrapper) {
                const isTableTag = el.tagName === 'TABLE';
                // If we click the wrapper directly or the table tag (border), select whole table
                if (isTableTag || el === tableWrapper) {
                    el = tableWrapper;
                }
            }

            // Handle text node selection
            const textNode = el.closest('.text-node');
            if (textNode) {
                el = textNode;
            }

            // Handle field block selection (atomic unit)
            const fieldBlock = el.closest('.field-block');
            if (fieldBlock) {
                el = fieldBlock;
            }

            const wasSelected = el.classList.contains('selected');

            $('.selected').removeClass('selected');
            if ($('#branchSelector').css('display') !== 'none') self.closeBranchSelector();

            let element = el;
            for (let i = 0; i <= 4 && element; i++, element = element.parentElement) {
                if (['t-if', 't-elif', 't-else'].some(attr => element.hasAttribute(attr))) {
                    self.showBranchSelector(element);
                    break;
                }
            }

            el.classList.add('selected');

            // "Select then Edit" strategy:
            // Only trigger the editor if the element was ALREADY selected.
            // And DON'T trigger MediumEditor for the whole table wrapper or field block.
            if (!wasSelected || el.classList.contains('table-wrapper') || el.classList.contains('field-block') || el.classList.contains('box-section-wrapper')) {
                if (self.editor) {
                    const prevEl = self.editor.elements[0];
                    self.editor.destroy();
                    self.editor = null;
                    if (prevEl && prevEl.classList.contains('text-node')) {
                        prevEl.setAttribute('contenteditable', 'false');
                    }
                }
                return;
            }

            if (self.editor) {
                const prevEl = self.editor.elements[0];
                self.editor.destroy();
                if (prevEl && prevEl.classList.contains('text-node')) {
                    prevEl.setAttribute('contenteditable', 'false');
                }
            }
            self.editor = null;

            if (e.target.classList.contains('tcm-delete-table') || e.target.closest('.tcm-delete-table')) {
                if (tableWrapper && confirm("Are you sure you want to delete this table?")) {
                    tableWrapper.remove();
                    return;
                }
            }

            // Bug fix: for text-nodes, enable contenteditable before MediumEditor init
            if (el.classList.contains('text-node')) {
                el.setAttribute('contenteditable', 'true');
            }

            self.editor = new MediumEditor(el, {
                toolbar: {
                    buttons: [
                        'bold', 'italic', 'underline', 'strikethrough',
                        'h1', 'h3', 'quote', 'anchor', 'deleteElement',
                    ],
                    relativeContainer: self.reportFrameRef.el,
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
        } else {
            // If we are exiting preview and source editor was ON,
            // we might need to re-init Ace to ensure it's properly sized
            // in the new layout if it's still visible.
            if (this.state.showSourceEditor) {
                this._initAceEditor();
            }
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
            // ── SYNC PENDING CHANGES ─────────────────────────────────────────
            // If there's an active undo stack or modified nodes, we should
            // save before fetching the source so that the 'combined' arch
            // returned by the backend includes current DnD changes.
            const hasChanges = $('.c_new').length > 0 || (this.undoManager && this.undoManager.canUndo());
            if (hasChanges) {
                console.log("[EditSources] Pending changes detected, saving first...");
                await this.save_changes(this);
            }

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

            // ── LIVE SYNC: Source -> UI ──────────────────────────────────────
            // Immediately re-fetch the arch and update the visual report frame
            // so the user sees their XML edits without a page reload.
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

    /**
     * Build the inner HTML string for a box section wrapper.
     */
    _buildBoxInnerHTML(cfg) {
        const layoutMode = cfg.layoutMode || 'free';
        const label = cfg.label || 'Section';
        return `
            <div class="box-toolbar" contenteditable="false">
                <span class="box-drag-handle fa fa-bars" title="Drag to move"></span>
                <span class="box-label-text">${label}</span>
                <span class="box-layout-badge">${layoutMode}</span>
                <span class="box-delete-btn fa fa-trash" title="Delete Section"></span>
            </div>
            <div class="box-dropzone layout-${layoutMode}"></div>
            <div class="box-resize-handles" contenteditable="false">
                <div class="box-resize-handle nw" data-dir="nw"></div>
                <div class="box-resize-handle n"  data-dir="n"></div>
                <div class="box-resize-handle ne" data-dir="ne"></div>
                <div class="box-resize-handle e"  data-dir="e"></div>
                <div class="box-resize-handle se" data-dir="se"></div>
                <div class="box-resize-handle s"  data-dir="s"></div>
                <div class="box-resize-handle sw" data-dir="sw"></div>
                <div class="box-resize-handle w"  data-dir="w"></div>
            </div>`;
    }

    /**
     * Create a SortableJS instance for a box inner drop zone.
     * Accepts all element types and stops propagation so the parent canvas
     * does not also receive the drop.
     */
    _createBoxDropzoneSortable(dropzone) {
        const self = this;
        const instance = Sortable.create(dropzone, {
            group: { name: 'studio', pull: true, put: true },
            animation: 150,
            draggable: '.table-wrapper, .box-section-wrapper, .dynamic-field-wrapper, .field-block, .text-node, [cy-type="dynamic"]:not(.dynamic-field-wrapper *)',
            handle: '.table-handle, .box-drag-handle, .box-toolbar, .field-handle, .dynamic-field-wrapper, .field-block, .text-node',
            onStart() {
                self._isDragging = true;
                if (self.editor) { self.editor.destroy(); self.editor = null; }
                $('.selected').removeClass('selected');
            },
            onEnd() { self._isDragging = false; },
            async onAdd(evt) {
                evt.originalEvent && evt.originalEvent.stopPropagation && evt.originalEvent.stopPropagation();
                const item = evt.item;
                const fromPanel = item.dataset._fromPanel === '1';
                if (!fromPanel) return;

                const type = item.dataset.type;
                delete item.dataset._fromPanel;
                item.style.opacity = '0.4';

                if (type === 'text') {
                    item.className = 'text-node c_new';
                    item.setAttribute('contenteditable', 'false');
                    item.innerHTML = 'Click to select, click again to edit';
                    item.style.opacity = '1';
                    self._refreshDragHandles();
                    return;
                }

                if (type === 'field') {
                    const resModel = self._resModel || '';
                    const { fieldPath, fieldInfo } = await self.openFieldSelectorPopover(dropzone, resModel, (f) => !['one2many', 'many2many'].includes(f.type));
                    if (!fieldPath) { item.remove(); return; }
                    item.className = 'field-block c_new dynamic-field-wrapper';
                    item.innerHTML = `
                        <div class="field-handle-container" contenteditable="false">
                            <span class="field-handle fa fa-bars" title="Drag to move"></span>
                            <span class="field-delete fa fa-trash" title="Delete Field"></span>
                        </div>
                        <div class="field-container d-inline-flex gap-1">
                            <strong class="field-label">${fieldInfo.string}: </strong>
                            <span t-field="doc.${fieldPath}" title="${fieldInfo.string}">${fieldPath}</span>
                        </div>`;
                    item.setAttribute('cy-type', 'dynamic');
                    item.style.opacity = '1';
                    item.querySelector('.field-delete').onclick = (e) => { e.stopPropagation(); if (confirm('Delete this field?')) item.remove(); };
                }

                if (type === 'box') {
                    const boxId = 'box_' + Math.random().toString(36).slice(2, 10);
                    const cfg = { id: boxId, label: 'Section', style: { width: 280, height: 160, backgroundColor: 'transparent', border: '1px solid #ccc', borderRadius: 4, padding: 8 }, layoutMode: 'free', children: [] };
                    item.className = 'box-section-wrapper c_new';
                    item.setAttribute('cy-type', 'box');
                    item.setAttribute('data-box-id', boxId);
                    item.setAttribute('data-box-config', JSON.stringify(cfg));
                    item.style.width = cfg.style.width + 'px';
                    item.style.height = cfg.style.height + 'px';
                    item.style.opacity = '1';
                    item.innerHTML = self._buildBoxInnerHTML(cfg);
                    item.querySelector('.box-delete-btn').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, { body: 'Delete this section?', confirm: () => item.remove(), cancel: () => { } });
                    };
                    self._setupBoxResizeHandles(item);
                    const inner = item.querySelector('.box-dropzone');
                    if (inner) self._createBoxDropzoneSortable(inner);
                }

                if (type === 'table') {
                    const resModel = self._resModel || '';
                    const config = await self.openTableConfigModal(dropzone, resModel);
                    if (!config) { item.remove(); return; }
                    const tableHtml = self._generateTableHtml(config);
                    item.className = 'c_new table-wrapper';
                    item.innerHTML = `
                        <div class="table-handle-container" contenteditable="false">
                            <div class="table-handle fa fa-bars" title="Drag to move"></div>
                            <div class="table-delete fa fa-trash" title="Delete Table"></div>
                        </div>
                        ${tableHtml}`;
                    item.setAttribute('cy-type', 'table');
                    item.setAttribute('cy-config', JSON.stringify(config));
                    item.style.opacity = '1';
                    item.querySelector('.table-delete').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, { body: 'Delete this table?', confirm: () => item.remove(), cancel: () => { } });
                    };
                }

                if (type === 'qr') {
                    const config = await self.openQrWizard(item);
                    if (!config) { item.remove(); return; }
                    self.insertQrBlock(item, config);
                }

                self._refreshDragHandles();
            }
        });
        this._sortableInstances.push(instance);
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

            draggable: '.table-wrapper, .box-wrapper, .dynamic-field-wrapper, .field-block, .text-node, [cy-type="dynamic"]:not(.dynamic-field-wrapper *)',
            handle: '.table-handle, .box-handle, .field-handle, .dynamic-field-wrapper, .field-block, .text-node, [cy-type="dynamic"]',
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

                if (type === 'text') {
                    // Transform dropped snippet into a text node at the drop position
                    item.className = 'text-node c_new';
                    item.setAttribute('contenteditable', 'false');
                    item.innerHTML = 'Click to select, click again to edit';
                    item.style.position = '';
                    item.style.left = '';
                    item.style.top = '';
                    item.style.opacity = '1';
                    // Select the new text node
                    setTimeout(() => {
                        item.classList.add('selected');
                    }, 0);
                    self._refreshDragHandles();
                    return;
                }

                if (type === 'field') {
                    const resModel = self._resModel || self.props.action.params?.res_model || '';

                    const { fieldPath, fieldInfo } =
                        await self.openFieldSelectorPopover(
                            zone,
                            resModel,
                            (field) => !['one2many', 'many2many'].includes(field.type),
                        );

                    if (!fieldPath) {
                        item.remove(); // cancelled
                        return;
                    }

                    // transform existing dropped node
                    item.className = 'field-block c_new dynamic-field-wrapper';
                    item.innerHTML = `
                        <div class="field-handle-container" contenteditable="false">
                            <span class="field-handle fa fa-bars" title="Drag to move"></span>
                            <span class="field-delete fa fa-trash" title="Delete Field"></span>
                        </div>
                        <div class="field-container d-inline-flex gap-1">
                            <strong class="field-label">${fieldInfo.string}: </strong>
                            <span t-field="doc.${fieldPath}" title="${fieldInfo.string}">${fieldPath}</span>
                        </div>`;
                    item.setAttribute('cy-type', 'dynamic');
                    item.style.cursor = 'default';
                    item.style.opacity = '1';

                    // Internal delete handler
                    item.querySelector('.field-delete').onclick = (e) => {
                        e.stopPropagation();
                        if (confirm("Delete this field?")) item.remove();
                    };
                }

                if (type === 'box') {
                    const boxId = 'box_' + Math.random().toString(36).slice(2, 10);
                    const defaultCfg = {
                        id: boxId,
                        label: 'Section',
                        style: { width: 300, height: 200, backgroundColor: 'transparent', border: '1px solid #ccc', borderRadius: 4, padding: 8 },
                        layoutMode: 'free',
                        children: [],
                    };
                    item.className = 'box-section-wrapper c_new';
                    item.setAttribute('cy-type', 'box');
                    item.setAttribute('data-box-id', boxId);
                    item.setAttribute('data-box-config', JSON.stringify(defaultCfg));
                    item.style.width = defaultCfg.style.width + 'px';
                    item.style.height = defaultCfg.style.height + 'px';
                    item.style.opacity = '1';
                    item.style.cursor = 'default';
                    item.innerHTML = self._buildBoxInnerHTML(defaultCfg);

                    // Wire box toolbar delete
                    item.querySelector('.box-delete-btn').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: 'Delete this section container and all its contents?',
                            confirm: () => {
                                if (self.state.showBoxProps && self._selectedBoxEl === item) {
                                    self.closeBoxProps();
                                }
                                item.remove();
                            },
                            cancel: () => { },
                        });
                    };

                    // Wire resize handles
                    self._setupBoxResizeHandles(item);

                    // Register inner dropzone as sortable zone
                    const dropzone = item.querySelector('.box-dropzone');
                    if (dropzone) {
                        self._createBoxDropzoneSortable(dropzone);
                    }
                }

                if (type === 'table') {
                    const resModel = self._resModel || self.props.action.params?.res_model || '';
                    const config = await self.openTableConfigModal(zone, resModel);

                    if (!config) {
                        item.remove();
                        return;
                    }

                    // transform existing dropped node
                    const tableHtml = self._generateTableHtml(config);
                    item.className = 'c_new table-wrapper';
                    item.innerHTML = `
                            <div class="table-handle-container" contenteditable="false">
                                <div class="table-handle fa fa-bars" title="Drag to move"></div>
                                <div class="table-delete fa fa-trash" title="Delete Table"></div>
                            </div>
                            ${tableHtml}`;
                    item.setAttribute('cy-type', 'table');
                    item.setAttribute('cy-config', JSON.stringify(config));
                    item.style.cursor = 'default';
                    item.style.opacity = '1';

                    // Internal delete handler
                    item.querySelector('.table-delete').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: "Are you sure you want to delete this table?",
                            confirm: () => item.remove(),
                            cancel: () => { },
                        });
                    };

                    const refreshRes = await self.rpc('/cyllo_studio/get_report_source', {
                        template: self._template,
                    });
                    if (refreshRes.success) {
                        self.state.sourceCode = refreshRes.arch;
                        if (self.aceEditor) {
                            self.aceEditor.setValue(refreshRes.arch, -1);
                        }
                    }
                }

                if (type === 'qr') {
                    const config = await self.openQrWizard(item);
                    if (!config) {
                        item.remove();
                        return;
                    }
                    self.insertQrBlock(item, config);
                }
                // Re-initialize drag handles for the new zone content
                self._refreshDragHandles();
            }
        });

        this._sortableInstances.push(instance);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Table Config Modal — Preset Definitions
    // ─────────────────────────────────────────────────────────────────────────

    static TABLE_PRESETS = {
        balance_sheet: {
            model: 'account.account',
            columns: [
                { label: 'Account', field: 'name', fieldType: 'char', aggregation: 'none', width: '40%' },
                { label: 'Debit', field: 'debit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
                { label: 'Credit', field: 'credit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
            ],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: true,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [
                {
                    label: 'Assets',
                    rowType: 'static',
                    domain: [["account_type", "in", ["asset_receivable", "asset_cash", "asset_current", "asset_non_current"]]],
                    subtotal: true,
                },
                {
                    label: 'Liabilities & Equity',
                    rowType: 'static',
                    domain: [["account_type", "in", ["liability_payable", "liability_current", "equity"]]],
                    subtotal: true,
                },
            ],
            grandTotal: {
                rowType: 'computed',
                formula: 'Total Assets = Total Liabilities + Equity',
                validate: true,
            },
        },
        p_and_l: {
            model: 'account.move.line',
            columns: [
                { label: 'Account', field: 'account_id', fieldType: 'many2one', aggregation: 'none', width: '40%' },
                { label: 'Debit', field: 'debit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
                { label: 'Credit', field: 'credit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
            ],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: true,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [
                {
                    label: 'Revenue',
                    rowType: 'static',
                    domain: [["account_id.account_type", "=", "income"]],
                    subtotal: true,
                },
                {
                    label: 'Expenses',
                    rowType: 'static',
                    domain: [["account_id.account_type", "=", "expense"]],
                    subtotal: true,
                },
            ],
            grandTotal: {
                rowType: 'computed',
                formula: 'Net Profit = Revenue - Expenses',
                validate: true,
            },
        },
        invoice: {
            model: 'account.move.line',
            columns: [
                { label: 'Description', field: 'name', fieldType: 'char', aggregation: 'none', width: '40%' },
                { label: 'Quantity', field: 'quantity', fieldType: 'float', aggregation: 'sum', width: '15%' },
                { label: 'Unit Price', field: 'price_unit', fieldType: 'float', aggregation: 'none', width: '20%' },
                { label: 'Amount', field: 'price_subtotal', fieldType: 'monetary', aggregation: 'sum', width: '25%' },
            ],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: true,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [],
            grandTotal: null,
        },
        blank: {
            model: '',
            columns: [],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: false,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [],
            grandTotal: null,
        },
    };

    _getDefaultTcmState() {
        const preset = EditReport.TABLE_PRESETS.balance_sheet;
        return {
            preset: 'balance_sheet',
            model: preset.model,
            columns: JSON.parse(JSON.stringify(preset.columns)),
            rowSource: preset.rowSource,
            manualRows: preset.manualRows,
            headerRow: preset.headerRow,
            totalsRow: preset.totalsRow,
            applyDomain: preset.applyDomain,
            domain: preset.domain,
            includeAllCompanies: preset.includeAllCompanies,
            sections: JSON.parse(JSON.stringify(preset.sections)),
            grandTotal: preset.grandTotal ? JSON.parse(JSON.stringify(preset.grandTotal)) : null,
            availableModels: [],
            availableFields: [],
        };
    }

    _getDefaultQrState() {
        return {
            step: 1,
            type: 'portal',
            config: {
                field: 'object.name',
                baseUrl: window.location.origin,
                portalPath: '',
                tokenType: 'auto',
                tokenExpr: '',
                upiVpa: '',
                amountField: 'amount_residual',
                noteField: 'object.name',
                expression: '',
                size: 100,
                align: 'center',
                errorCorrection: 'M',
                caption: '',
                requireAuth: false,
                trackAnalytics: true,
                hasExpiry: false,
                expiresDays: 30,
            },
            previewImgUrl: '',
            previewLoading: false,
            previewError: false,
            previewStr: '',
            qwebPreview: '',
            validationResult: 'none',
            validationError: '',
            warnings: {},
            errors: {
                hasErrors: false,
                upi_vpa: false,
            }
        };
    }

    async openQrWizard(placeholderEl, mode = 'insert') {
        const self = this;
        this.state.showQrWizard = true;

        if (mode === 'edit' && placeholderEl.dataset.qrConfig) {
            try {
                const existing = JSON.parse(placeholderEl.dataset.qrConfig);
                this.state.qr = this._getDefaultQrState();
                this.state.qr.type = existing.type || 'portal';
                Object.assign(this.state.qr.config, existing.config || {});
                this.state.qr.step = 3;
            } catch (e) {
                this.state.qr = this._getDefaultQrState();
            }
        } else {
            this.state.qr = this._getDefaultQrState();
        }

        const model = this.state.reportInfo.model;
        if (model === 'account.move') {
            this.state.qr.config.portalPath = '/my/invoices/';
        } else if (model === 'sale.order') {
            this.state.qr.config.portalPath = '/my/orders/';
        }

        this._updateQrPreviews();

        return new Promise((resolve) => {
            self._qrResolve = (config) => {
                self.state.showQrWizard = false;
                resolve(config);
            };
        });
    }

    onSelectQrType(type) {
        this.state.qr.type = type;
        this._updateQrPreviews();
    }

    updateQrConfig(key, value) {
        if (key === 'size') {
            value = parseInt(value, 10) || 100;
        }
        this.state.qr.config[key] = value;
        if (this.state.qr.type === 'upi') {
            this.state.qr.errors.upi_vpa = !this.state.qr.config.upiVpa;
            this.state.qr.errors.hasErrors = this.state.qr.errors.upi_vpa;
        } else {
            this.state.qr.errors.hasErrors = false;
        }
        this._updateQrPreviews();
    }

    qrNextStep() {
        if (this.state.qr.step < 3) this.state.qr.step++;
    }

    qrPrevStep() {
        if (this.state.qr.step > 1) this.state.qr.step--;
    }

    qrGoToStep(step) {
        if (step < this.state.qr.step || !this.state.qr.errors.hasErrors) {
            this.state.qr.step = step;
        }
    }

    onQrWizardCancel() {
        this.onQrCancel();
    }

    onQrCancel() {
        this.state.showQrWizard = false;
        if (this._qrResolve) this._qrResolve(null);
    }

    async onQrWizardConfirm() {
        if (this.state.qr.type === 'pdf_link' && !this.state.qr.config.token) {
            console.log('entered',this.state.reportInfo.report_name,this)
            try {
                this.state.qr.previewLoading = true;
                const res = await this.rpc('/cyllo_studio/generate_qr_token', {
                    template: this.state.reportInfo.report_name || this._template,
                    options: {
                        requireAuth: this.state.qr.config.requireAuth,
                        trackAnalytics: this.state.qr.config.trackAnalytics,
                        expiresDays: this.state.qr.config.hasExpiry ? this.state.qr.config.expiresDays : null,
                    }
                });
                if (res.success) {
                    this.state.qr.config.token = res.token;
                } else {
                    this.notification.add(res.error || "Failed to generate token", { type: "danger" });
                    this.state.qr.previewLoading = false;
                    return;
                }
            } catch (e) {
                this.notification.add("Could not connect to server", { type: "danger" });
                this.state.qr.previewLoading = false;
                return;
            }
        }

        if (this._qrResolve) {
            this._qrResolve({
                type: this.state.qr.type,
                config: { ...this.state.qr.config }
            });
        }
    }

    async validateQrExpression() {
        const expr = this.state.qr.config.expression;
        if (!expr) return;
        try {
            const result = await this.rpc('/studio/report/validate_expr', {
                expr: expr,
                model: this.state.reportInfo.model
            });
            this.state.qr.validationResult = result.valid ? 'valid' : 'invalid';
            this.state.qr.validationError = result.error || '';
        } catch (e) {
            this.state.qr.validationResult = 'invalid';
            this.state.qr.validationError = e.message;
        }
    }

    onQrPreviewError() {
        this.state.qr.previewError = true;
        this.state.qr.previewLoading = false;
    }

    _updateQrPreviews() {
        if (!this.state.showQrWizard) return;
        const expr = this._buildQrExpression();
        this.state.qr.previewStr = expr;
        this.state.qr.previewLoading = true;
        this.state.qr.previewError = false;

        const encoded = encodeURIComponent(expr.replace(/doc\./g, 'object.'));
        const size = this.state.qr.config.size || 100;
        this.state.qr.previewImgUrl = `/report/barcode/?barcode_type=QR&value=${encoded}&width=${size}&height=${size}`;

        const align = this.state.qr.config.align;
        const qwebExpr = this._buildQrExpression(true);

        let html = `<div style="text-align:${align};">\n`;
        html += `  <img t-att-src="'/report/barcode/?barcode_type=QR&amp;value=%s&amp;width=${size}&amp;height=${size}' % url_quote(str(${qwebExpr}) or 'No Data')" \n`;
        html += `       style="width:${size}px; height:${size}px;"/>\n`;
        if (this.state.qr.config.caption) {
            html += `  <div style="font-size:8pt; margin-top:3px;">${this.state.qr.config.caption}</div>\n`;
        }
        html += `</div>`;
        this.state.qr.qwebPreview = html;
    }

    _buildQrExpression(forQWeb = false, qrState = null) {
        const type = qrState ? qrState.type : this.state.qr.type;
        const config = qrState ? qrState.config : this.state.qr.config;
        const obj = 'doc'; // Always use 'doc' to match the blank report iterator

        /**
         * Determine whether a string value looks like a Python field expression
         * (e.g. "doc.partner_id.name") or a static literal that must be quoted.
         * A static value = anything that:
         *   - contains '://' (URLs like https://...)
         *   - starts with a digit or special char that isn't a valid Python identifier start
         *   - contains spaces
         *   - is NOT prefixed with a known Python variable name
         */
        const _quoteIfStatic = (val) => {
            if (!val) return "''";
            // Already a quoted string in the expression (starts/ends with quote)
            if ((val.startsWith("'") && val.endsWith("'")) ||
                (val.startsWith('"') && val.endsWith('"'))) {
                return val;
            }
            // Looks like a field path: starts with a word char and contains only
            // word chars, dots, underscores (e.g. doc.partner_id.name)
            if (/^[a-zA-Z_][a-zA-Z0-9_.]*$/.test(val)) {
                return val.replace(/object\./g, obj + '.');
            }
            // Static value — escape single quotes and wrap
            const escaped = val.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            return `'${escaped}'`;
        };

        if (type === 'plain') return _quoteIfStatic(config.field);
        if (type === 'portal') {
            const path = config.portalPath || '/my/view/';
            // Ensure no double slashes between base_url and path
            //            const normalizedPath = path.startsWith('/') ? path : '/' + path;
            //            console.log('hnjkkjj',normalizedPath)

            // Check if the user entered a custom Base URL that overrides the server origin
            let baseUrlStr = `str(${obj}.get_base_url()).rstrip('/')`;
            if (config.baseUrl && config.baseUrl !== window.location.origin) {
                const safeUrl = config.baseUrl.replace(/'/g, "\\'").replace(/\/$/, '');
                baseUrlStr = `'${safeUrl}'`;
            }

            const s = `${baseUrlStr} `;
            if (config.tokenType === 'auto') return s + ` + '?' + ${obj}._get_share_url()`;
            return s;
        }
        if (type === 'upi') {
            const pa = config.upiVpa;
            const am = `${obj}.${config.amountField}`;
            const tn = config.noteField === 'custom' ? "'Payment'" : config.noteField.replace(/object\./g, obj + '.');
            return `'upi://pay?pa=${pa}&am=' + str(${am}) + '&tn=' + str(${tn})`;
        }
        if (type === 'custom') return _quoteIfStatic(config.expression || "''");
        if (type === 'pdf_link') {
            const reportId = this.state.reportInfo?.id || this._reportId || 'REPORT_ID';
            let baseUrlStr = `str(${obj}.get_base_url()).rstrip('/')`;
            return `${baseUrlStr} + '/report/pdf/${this.state.reportInfo.id}/' + str(${obj}.id) + '?token=${config.token || "PENDING"}'`;
        }
        return "''";
    }

    async openTableConfigModal(targetEl, resModel) {
        // Reset state to default
        Object.assign(this.state.tcm, this._getDefaultTcmState());

        // Fetch available models
        try {
            const models = await this.orm.searchRead('ir.model', [], ['name', 'model'], { order: 'name' });
            this.state.tcm.availableModels = models.map(m => ({ name: m.name, model: m.model }));
        } catch (e) {
            console.warn('[TableConfig] Could not fetch models:', e);
            this.state.tcm.availableModels = [
                { name: 'Account', model: 'account.account' },
                { name: 'Journal Item', model: 'account.move.line' },
                { name: 'Invoice', model: 'account.move' },
            ];
        }

        // Apply default preset to load fields for the default model
        await this._loadModelFields(this.state.tcm.model);

        // Show the modal and return a promise
        this.state.showTableModal = true;

        return new Promise((resolve) => {
            this._tcmResolve = resolve;
        });
    }

    onSelectPreset(presetName) {
        const preset = EditReport.TABLE_PRESETS[presetName];
        if (!preset) return;

        this.state.tcm.preset = presetName;
        this.state.tcm.model = preset.model;
        this.state.tcm.columns = JSON.parse(JSON.stringify(preset.columns));
        this.state.tcm.rowSource = preset.rowSource;
        this.state.tcm.manualRows = preset.manualRows;
        this.state.tcm.headerRow = preset.headerRow;
        this.state.tcm.totalsRow = preset.totalsRow;
        this.state.tcm.applyDomain = preset.applyDomain;
        this.state.tcm.domain = preset.domain;
        this.state.tcm.includeAllCompanies = preset.includeAllCompanies;
        this.state.tcm.sections = JSON.parse(JSON.stringify(preset.sections));
        this.state.tcm.grandTotal = preset.grandTotal ? JSON.parse(JSON.stringify(preset.grandTotal)) : null;

        if (preset.model) {
            this._loadModelFields(preset.model);
        } else {
            this.state.tcm.availableFields = [];
        }
    }

    async onModelChange(ev) {
        const model = ev.target.value;
        this.state.tcm.model = model;
        if (model) {
            await this._loadModelFields(model);
        } else {
            this.state.tcm.availableFields = [];
        }
    }

    async _loadModelFields(modelName) {
        if (!modelName) {
            this.state.tcm.availableFields = [];
            return;
        }
        try {
            const fields = await this.orm.call(modelName, 'fields_get', [], {
                attributes: ['string', 'type', 'store', 'relation'],
            });
            const HIDDEN_TYPES = ['one2many', 'many2many', 'binary'];
            const fieldList = Object.entries(fields)
                .filter(([name, info]) => !HIDDEN_TYPES.includes(info.type) && !name.startsWith('__'))
                .map(([name, info]) => ({
                    name,
                    string: info.string || name,
                    type: info.type,
                    store: info.store,
                    relation: info.relation || null,
                }))
                .sort((a, b) => (a.string || a.name).localeCompare(b.string || b.name));
            this.state.tcm.availableFields = fieldList;
        } catch (e) {
            console.warn('[TableConfig] Could not fetch fields for', modelName, e);
            this.state.tcm.availableFields = [];
        }
    }

    // ── Column management ────────────────────────────────────────────────────

    onAddColumn() {
        this.state.tcm.columns.push({
            label: '',
            field: '',
            fieldType: '',
            aggregation: 'none',
            width: '',
        });
    }

    onRemoveColumn(index) {
        this.state.tcm.columns.splice(index, 1);
    }

    onColumnLabelChange(index, ev) {
        this.state.tcm.columns[index].label = ev.target.value;
    }

    onColumnFieldChange(index, ev) {
        const fieldName = ev.target.value;
        this.state.tcm.columns[index].field = fieldName;
        // Auto-detect field type from availableFields
        const fieldInfo = this.state.tcm.availableFields.find(f => f.name === fieldName);
        if (fieldInfo) {
            this.state.tcm.columns[index].fieldType = fieldInfo.type;
            // Auto-set label if empty
            if (!this.state.tcm.columns[index].label) {
                this.state.tcm.columns[index].label = fieldInfo.string || fieldName;
            }
        }
    }

    onColumnAggChange(index, ev) {
        this.state.tcm.columns[index].aggregation = ev.target.value;
    }

    onColumnWidthChange(index, ev) {
        this.state.tcm.columns[index].width = ev.target.value;
    }

    // ── Modal confirm / cancel ───────────────────────────────────────────────

    onTableModalConfirm() {
        const config = JSON.parse(JSON.stringify(this.state.tcm));
        // Remove internal UI fields
        delete config.availableModels;
        delete config.availableFields;
        this.state.showTableModal = false;
        if (this._tcmResolve) {
            this._tcmResolve(config);
            this._tcmResolve = null;
        }
    }

    onTableModalCancel() {
        this.state.showTableModal = false;
        if (this._tcmResolve) {
            this._tcmResolve(null);
            this._tcmResolve = null;
        }
    }

    _generateTableHtml(config) {
        const cols = config.columns || [];
        const colCount = cols.length || 3;

        // Column width style helper
        const colStyle = (col, align) => {
            let s = `text-align: ${align || 'left'}; padding: 8px;`;
            if (col.width) s += ` width: ${col.width};`;
            return s;
        };

        // Determine if a field type is numeric
        const isNumeric = (type) => ['float', 'monetary', 'integer'].includes(type);

        let html = `
            <table class="table table-sm mt-3" style="width: 100%; border-collapse: collapse;">`;

        // ── Header Row ────────────────────────────────────────────────
        if (config.headerRow && cols.length > 0) {
            html += `<thead style="border-bottom: 2px solid #333;"><tr>`;
            cols.forEach(col => {
                const align = isNumeric(col.fieldType) ? 'right' : 'left';
                html += `<th style="${colStyle(col, align)}">${col.label || col.field || 'Column'}</th>`;
            });
            html += `</tr></thead>`;
        }

        html += `<tbody style="border-bottom: 1px solid #dee2e6;">`;

        // ── Preset: Balance Sheet ─────────────────────────────────────
        if (config.preset === 'balance_sheet' && config.sections && config.sections.length > 0) {
            config.sections.forEach(section => {
                const domainStr = JSON.stringify(section.domain || []);
                // Section header
                html += `
                    <tr class="table-active section-header" style="background-color: #f2f2f2; font-weight: bold; border-top: 2px solid #333;">
                        <td colspan="${colCount}">${(section.label || 'Section').toUpperCase()}</td>
                    </tr>`;
                // Data rows — use t-foreach with the model on the tr directly
                html += `
                    <tr t-foreach="docs.filtered(lambda r: r.account_type in ${this._pythonDomainValues(section.domain)})" t-as="doc" class="data-row" style="border-bottom: 1px solid #eee;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    if (col.fieldType === 'many2one') {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}"/></td>`;
                    } else if (isNumeric(col.fieldType)) {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}" t-att-class="doc.${col.field} &lt; 0 and 'text-danger' or ''"/></td>`;
                    } else {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}"/></td>`;
                    }
                });
                html += `</tr>`;
                // Section subtotal
                if (section.subtotal) {
                    html += `
                    <tr class="total-row" style="border-top: 1px solid #333; font-weight: bold; background-color: #fafafa;">`;
                    cols.forEach((col, ci) => {
                        const align = isNumeric(col.fieldType) ? 'right' : 'left';
                        if (ci === 0) {
                            html += `<td style="${colStyle(col, align)}">Total ${section.label || ''}</td>`;
                        } else if (isNumeric(col.fieldType) && col.aggregation === 'sum') {
                            html += `<td style="${colStyle(col, 'right')}"><span t-esc="sum(section_records.mapped('${col.field}'))"/></td>`;
                        } else {
                            html += `<td style="${colStyle(col, align)}"></td>`;
                        }
                    });
                    html += `</tr>`;
                }
            });

            // ── Preset: Invoice ───────────────────────────────────────────
        } else if (config.preset === 'invoice') {
            html += `
                    <t t-foreach="doc.invoice_line_ids" t-as="line">
                        <tr style="border-bottom: 1px solid #f8f9fa;">`;
            cols.forEach(col => {
                const align = isNumeric(col.fieldType) ? 'right' : 'left';
                html += `<td style="${colStyle(col, align)}"><span t-field="line.${col.field}" /></td>`;
            });
            html += `
                        </tr>
                </t>`;

            // ── Preset: P&L ───────────────────────────────────────
        } else if (config.preset === 'p_and_l' && config.sections && config.sections.length > 0) {
            config.sections.forEach(section => {
                html += `
                    <tr class="table-active section-header" style="background-color: #f2f2f2; font-weight: bold; border-top: 2px solid #333;">
                        <td colspan="${colCount}">${(section.label || 'Section').toUpperCase()}</td>
                    </tr>
                    <t t-foreach="doc.line_ids.filtered(lambda l: l.${section.domain?.[0]?.[0] || 'account_id.account_type'} ${section.domain?.[0]?.[1] || '='} '${section.domain?.[0]?.[2] || 'income'}')" t-as="line">
                        <tr class="data-row" style="border-bottom: 1px solid #eee;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    html += `<td style="${colStyle(col, align)}"><span t-field="line.${col.field}" /></td>`;
                });
                html += `
                        </tr>
                    </t>`;
                if (section.subtotal) {
                    html += `
                        <tr class="total-row" style="border-top: 1px solid #333; font-weight: bold; background-color: #fafafa;">`;
                    cols.forEach((col, ci) => {
                        if (ci === 0) {
                            html += `<td>Total ${section.label || ''}</td>`;
                        } else if (isNumeric(col.fieldType)) {
                            html += `<td style="text-align: right;">—</td>`;
                        } else {
                            html += `<td></td>`;
                        }
                    });
                    html += `</tr>`;
                }
            });

            // ── Dynamic / Manual / Blank ─────────────────────────────────
        } else {
            if (config.rowSource === 'manual') {
                const rows = config.manualRows || 5;
                for (let r = 0; r < rows; r++) {
                    html += `<tr style="border-bottom: 1px solid #f8f9fa;">`;
                    cols.forEach(col => {
                        html += `<td style="padding: 8px;">${col.label || ''}</td>`;
                    });
                    html += `</tr>`;
                }
            } else if (config.model && cols.length > 0) {
                // Dynamic with model — t-foreach over docs
                html += `
                <tr t-foreach="docs" t-as="doc" style="border-bottom: 1px solid #f8f9fa;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    if (col.field) {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}"/></td>`;
                    } else {
                        html += `<td style="padding: 8px;">${col.label || ''}</td>`;
                    }
                });
                html += `</tr>`;
            } else {
                // Fallback — empty placeholder rows
                for (let r = 0; r < 3; r++) {
                    html += `<tr style="border-bottom: 1px solid #f8f9fa;">`;
                    for (let c = 0; c < Math.max(colCount, 3); c++) {
                        html += `<td style="padding: 8px;">Data ${r + 1}-${c + 1}</td>`;
                    }
                    html += `</tr>`;
                }
            }
        }

        html += `</tbody>`;

        // ── Totals Row ────────────────────────────────────────────────
        if (config.totalsRow && cols.length > 0) {
            html += `<tfoot style="border-top: 2px solid #333; font-weight: bold;"><tr>`;
            cols.forEach((col, ci) => {
                const align = isNumeric(col.fieldType) ? 'right' : 'left';
                if (ci === 0) {
                    html += `<td style="${colStyle(col, align)}">Total</td>`;
                } else if (col.aggregation && col.aggregation !== 'none' && isNumeric(col.fieldType)) {
                    html += `<td style="${colStyle(col, 'right')}">—</td>`;
                } else {
                    html += `<td style="${colStyle(col, align)}"></td>`;
                }
            });
            html += `</tr></tfoot>`;
        }

        html += `</table>`;
        return html;
    }

    /**
     * Helper: extract domain values for Python filtering.
     * Converts [["account_type", "in", ["asset_receivable",...]]] → the list values.
     */
    _pythonDomainValues(domain) {
        if (!domain || !domain.length) return '[]';
        const first = domain[0];
        if (Array.isArray(first) && first.length >= 3 && Array.isArray(first[2])) {
            return JSON.stringify(first[2]).replace(/"/g, "'");
        }
        return '[]';
    }
    //    _createZoneSortable(zone) {
    //        const self = this;
    //
    //        const instance = Sortable.create(zone, {
    //            group: {
    //                name: 'studio',
    //                pull: 'clone',   // elements can be moved out of this zone
    //                put: true,    // elements from panel clones or other zones land here
    //            },
    //            animation: 150,
    //            ghostClass: 'gu-transit',
    //            dragClass: 'gu-mirror',
    //
    //            onStart: () => {
    //                self._isDragging = true;
    //                if (self.editor) {
    //                    self.editor.destroy();
    //                    self.editor = null;
    //                }
    //                $('.selected').removeClass('selected');
    //            },
    //
    //            onEnd: () => {
    //                self._isDragging = false;
    //            },
    //
    //            // Fired when an element from ANOTHER list (panel or other zone) is dropped here
    //            onAdd: async (evt) => {
    //                console.log('avtttt',evt)
    //                const item = evt.item;
    //                const fromPanel = item.dataset._fromPanel === '1';
    //
    //                if (fromPanel) {
    //                    // Remove the placeholder node SortableJS already inserted
    //                    item.remove();
    //                    delete item.dataset._fromPanel;
    //
    //                    const type = item.dataset.type;
    //                    let html = '';
    //
    //                    if (type === 'field') {
    //                        const resModel = self._resModel || self.props.action.params?.res_model || '';
    //                        const { fieldPath, fieldInfo } = await self.openFieldSelectorPopover(
    //                            zone, resModel,
    //                            (field) => !['one2many', 'many2many'].includes(field.type),
    //                        );
    //                        if (!fieldPath) return;
    //                        html = `<span class="c_new"
    //                                t-field="doc.${fieldPath}"
    //                                style="cursor:grab;"
    //                                title="${fieldInfo.string}">${fieldPath}</span>`;
    //                    } else if (type === 'box') {
    //                        html = `<div class="box rounded-2 c_new"
    //                                style="border:1px solid #000;padding:10px;cursor:grab;">
    //                                <span>New box</span>
    //                            </div>`;
    //                    }
    //
    //                    if (html) {
    //                        zone.insertAdjacentHTML('beforeend', html);
    //                        // Re-wire sortable so the newly added element is draggable
    //                        this._refreshDragHandles();
    //                    }
    //                }
    //                // For existing elements moved between zones, SortableJS handles the
    //                // DOM move automatically — nothing extra needed.
    //            },
    //
    //            // After any sort/move within the same list
    //            onEnd: () => {
    //                // Nothing extra needed; DOM is already updated by SortableJS
    //            },
    //
    //        });
    //
    //        this._sortableInstances.push(instance);
    //    }

    /**
     * Remove orphaned <t>/<cy-qweb-t> structural nodes that the HTML parser
     * foster-parents as siblings of the table wrapper.
     *
     * Background: `<t t-foreach>` / `<t t-set>` are not valid inside <tbody>,
     * so the browser hoists them *before* the <table> as zone siblings while
     * leaving the actual <tr> rows inside <tbody>.  When the .table-wrapper is
     * removed these empty <t> ghosts remain and get serialised into the saved
     * QWeb XML.  We kill them here BEFORE calling wrapper.remove().
     *
     * @param {HTMLElement} wrapper  The .table-wrapper about to be deleted.
     */
    _removeOrphanedQwebElements(wrapper) {
        const zone = wrapper.parentElement;
        if (!zone) return;

        const siblings = Array.from(zone.children);
        const wrapperIdx = siblings.indexOf(wrapper);

        siblings.forEach((sib, idx) => {
            const tag = (sib.tagName || '').toLowerCase();
            if (tag !== 't' && tag !== 'cy-qweb-t') return;

            // Determine whether this <t> carries visible user content.
            // Structural nodes (t-foreach, t-set, t-as, t-value …) foster-parented
            // out of the table will be empty or only contain other <t> nodes.
            const hasVisibleContent =
                sib.textContent.trim().length > 0 &&
                Array.from(sib.children).some(
                    c => !['t', 'cy-qweb-t'].includes((c.tagName || '').toLowerCase())
                );

            // Remove if: (a) it has no real visible content, OR
            //             (b) it is immediately adjacent to the wrapper (within 2 slots)
            //                 and has no visible content at all.
            const isAdjacent = Math.abs(idx - wrapperIdx) <= 2;
            if (!hasVisibleContent || isAdjacent) {
                sib.remove();
            }
        });

        // Safety sweep: catch any remaining empty structural orphans in the zone.
        zone.querySelectorAll('t, cy-qweb-t').forEach(el => {
            if (!el.textContent.trim() && el.children.length === 0) {
                el.remove();
            }
        });
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

        // Also register every box dropzone as a sortable target
        this._reportFrame.querySelectorAll('.box-dropzone').forEach(dz => {
            this._createBoxDropzoneSortable(dz);
        });

        // Re-wire resize handles for all box wrappers
        this._reportFrame.querySelectorAll('.box-section-wrapper').forEach(bw => {
            this._setupBoxResizeHandles(bw);
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
        if (component.state.isSaving) return;
        component.state.isSaving = true;
        try {
            document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
            document.querySelectorAll('[class="/"], [class=""]').forEach(el => el.removeAttribute('class'));
            $('[t-if], [t-elif], [t-else]').removeAttr('style');
            if (component.editor) component.editor.destroy();
            component.editor = null;

            // Ensure any pending DOM updates are finished
            await new Promise(r => setTimeout(r, 100));

            const editedHTML = component.reportFrameRef.el.innerHTML;
            console.log('[Cyllo Studio] Serializing HTML...', editedHTML.length, 'bytes');
            const parser = new DOMParser();
            const editedDoc = parser.parseFromString(editedHTML, 'text/html');
            const originalDoc = parser.parseFromString(component._loadedArch || '', 'text/html');

            const changes = component.getChangedElements(originalDoc, editedDoc);
            console.log('[Cyllo Studio] Changes detected:', changes.length, changes);

            if (changes.length === 0) {
                component.state.isSaving = false;
                return;
            }

            const newTemplates = component.buildInheritanceXML(changes);
            console.log('[Cyllo Studio] Sending templates:', newTemplates);

            const result = await component.rpc('/cyllo_studio/create/inherited_view', {
                all_arch: newTemplates,
            });
            console.log('[Cyllo Studio] Save result:', result);

            if (result && result['success'] === true) {
                component.notification.add("Report saved successfully", { type: "success" });

                // ── CAPTURE THUMBNAIL (Non-blocking, Only if missing) ────
                if (!component.state.hasThumbnail) {
                    setTimeout(async () => {
                        try {
                            const reportEl = component.reportFrameRef.el;
                            const containerEl = reportEl ? reportEl.closest('.cyllo-studio-report-container') : null;

                            if (containerEl && window.html2canvas) {
                                // Brief delay to ensure any final paint after RPC
                                await new Promise(r => setTimeout(r, 400));
                                containerEl.scrollTop = 0;

                                const canvas = await window.html2canvas(containerEl, {
                                    scale: 0.5, // Reduced scale for faster processing and smaller size
                                    useCORS: true,
                                    logging: false,
                                    allowTaint: true,
                                    backgroundColor: '#ffffff',
                                    width: containerEl.clientWidth,
                                    height: Math.min(containerEl.scrollHeight, 1200) // Limit height to capture only the relevant top part
                                });

                                const imgData = canvas.toDataURL('image/jpeg', 0.6); // Slightly lower quality for even faster save

                                await component.rpc('/cyllo_studio/save_report_thumbnail', {
                                    report_id: component._reportId,
                                    report_name: component._template,
                                    image_base64: imgData
                                });
                                console.log("[Cyllo Studio] Lazy thumbnail saved.");
                                component.state.hasThumbnail = true;
                            }
                        } catch (e) {
                            console.error("[Cyllo Studio] Background thumbnail capture failure:", e);
                        }
                    }, 100);
                }

                // ── PERSISTENT SAVE: Refresh local state instead of closing ────
                const resArch = await component.rpc('/cyllo_studio/get_arch', {
                    template: component._template,
                    show_placeholders: false
                });
                if (resArch && resArch.success) {
                    component._loadedArch = resArch.arch;
                    if (!component.state.previewMode) {
                        component._setupReportFrame(resArch.arch);
                        component._setupSortable();
                    } else {
                        await component._fetchPreviewData();
                    }

                    // If source editor is open, refresh it too (UI -> Source sync)
                    if (component.state.showSourceEditor) {
                        const refreshRes = await component.rpc('/cyllo_studio/get_report_source', {
                            template: component._template,
                        });
                        if (refreshRes.success) {
                            component.state.sourceCode = refreshRes.arch;
                            if (component.aceEditor) {
                                component.aceEditor.setValue(refreshRes.arch, -1);
                            }
                        }
                    }
                }
            } else {
                alert('Save failed: ' + result.error);
            }
        } finally {
            component.state.isSaving = false;
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
                allChanges.push({ el, xpath, template, structChanged });
            }
        });

        return allChanges.filter(change =>
            !allChanges.some(p => p !== change && change.xpath.startsWith(p.xpath + '/'))
        );
    }

    insertQrBlock(placeholderEl, qrConfig, mode = 'insert') {
        const type = qrConfig.type;
        const config = qrConfig.config;
        const align = config.align || 'center';
        const size = config.size || 100;

        placeholderEl.className = 's_qr_block c_new';
        placeholderEl.style.textAlign = align;
        placeholderEl.style.cursor = 'default';
        placeholderEl.style.opacity = '1';
        placeholderEl.setAttribute('cy-type', 'qr');
        placeholderEl.dataset.qrConfig = JSON.stringify(qrConfig);

        const previewImg = this._buildQrExpression().replace(/doc\./g, 'object.');
        const encoded = encodeURIComponent(previewImg);

        placeholderEl.innerHTML = `
            <div class="qr-handle-container" contenteditable="false" style="position:absolute; top:-10px; left:10px; background:#9ea700; border-radius:4px; padding:0 4px; display:flex; gap:6px; z-index:100;">
                <span class="fa fa-bars" style="color:white; font-size:10px; cursor:grab; padding:2px;"></span>
                <span class="qr-edit-btn fa fa-edit" style="color:white; font-size:10px; cursor:pointer; padding:2px;" title="Edit QR"></span>
                <span class="qr-delete fa fa-trash" style="color:#ffdce0; font-size:10px; cursor:pointer; padding:2px;" title="Delete QR"></span>
            </div>
            <div class="qr-content-wrapper" style="display:inline-block; position:relative;">
                <img src="/report/barcode/?barcode_type=QR&value=${encoded}&width=${size}&height=${size}" style="width:${size}px; height:${size}px; display:block; margin:0 auto;"/>
                ${config.caption ? `<div class="qr-caption" style="font-size:8pt; margin-top:3px; text-align:center;">${config.caption}</div>` : ''}
            </div>
        `;

        placeholderEl.querySelector('.qr-delete').onclick = (e) => {
            e.stopPropagation();
            if (confirm("Delete this QR code?")) placeholderEl.remove();
        };

        if (mode === 'insert') {
            setTimeout(() => placeholderEl.classList.add('selected'), 0);
        }
        this._refreshDragHandles();
    }

    _cleanStudioAttrs(node) {
        if (!node) return;
        const self = this;
        // Wrap in a temporary span to allow unwrapping the root itself
        const temp = document.createElement('span');
        const parent = node.parentNode;
        const next = node.nextSibling;
        temp.appendChild(node);

        const studioAttrs = ['cy-xpath', 'cy-template', 'cy-type', 'draggable', 'data-type', 'cy-config'];
        const clean = (el) => {
            if (!el || !el.removeAttribute) return;

            // ── QR Block Serialization ──
            if (el.classList && el.classList.contains('s_qr_block')) {
                const configStr = el.dataset.qrConfig;
                if (configStr) {
                    try {
                        const qr = JSON.parse(configStr);
                        const align = qr.config.align || 'center';
                        const size = qr.config.size || 100;
                        const qwebExpr = self._buildQrExpression(true, qr);

                        el.innerHTML = '';
                        el.style.textAlign = align;
                        el.style.cursor = '';
                        el.style.opacity = '';

                        const img = document.createElement('img');
                        // Use url_quote (now provided in the backend context) for safe path encoding
                        img.setAttribute('t-att-src', `'/report/barcode/?barcode_type=QR&value=%s&width=${size}&height=${size}' % url_quote(str(${qwebExpr}) or 'No Data')`);
                        img.style.width = size + 'px';
                        img.style.height = size + 'px';
                        el.appendChild(img);

                        if (qr.config.caption) {
                            const caption = document.createElement('div');
                            caption.style.fontSize = '8pt';
                            caption.style.marginTop = '3px';
                            caption.style.textAlign = 'center';
                            caption.innerText = qr.config.caption;
                            el.appendChild(caption);
                        }
                    } catch (e) {
                        console.error("[Cyllo Studio] QR Serialization failed", e);
                    }
                }
                el.classList.remove('s_qr_block', 'c_new', 'selected');
                el.removeAttribute('data-qr-config');
            }

            studioAttrs.forEach(a => el.removeAttribute(a));
            el.removeAttribute('onmouseover');
            el.removeAttribute('onmouseout');
            el.removeAttribute('onclick');
            el.removeAttribute('contenteditable');
            if (el.style) {
                if (el.style.cursor) el.style.removeProperty('cursor');
                if (el.style.outline) el.style.removeProperty('outline');
                if (el.style.opacity) el.style.removeProperty('opacity');
                if (el.getAttribute('style') === '') el.removeAttribute('style');
            }

            const handles = el.querySelectorAll ? Array.from(el.querySelectorAll('.table-handle, .box-handle, .box-toolbar, .box-resize-handles, .box-resize-handle, .field-handle, .tcm-delete-table, .table-toolbar, .text-handle, .resize-handle, .field-delete, .table-handle-container, .table-delete, .field-handle-container, .qr-handle-container')) : [];
            handles.forEach(h => h.remove());

            // Unwrap wrappers
            if (el.classList && el.classList.contains('table-wrapper')) {
                const table = el.querySelector('table');
                if (table && el.parentNode) {
                    el.parentNode.replaceChild(table, el);
                    clean(table);
                    return;
                }
            }
            // ── Box Section Container Serialization ──
            if (el.classList && el.classList.contains('box-section-wrapper')) {
                let cfg = {};
                try { cfg = JSON.parse(el.dataset.boxConfig || '{}'); } catch (ex) { }
                const s = cfg.style || {};
                const layoutMode = cfg.layoutMode || 'free';

                // Build the output <div class="report-section">
                const section = document.createElement('div');
                section.className = 'report-section';
                section.setAttribute('data-box-id', cfg.id || '');
                section.setAttribute('data-layout-mode', layoutMode);

                let styleStr = 'position:relative;';
                styleStr += 'box-sizing:border-box;';
                if (s.width) styleStr += `width:${s.width}px;`;
                if (s.height) styleStr += `height:${s.height}px;`;
                styleStr += `background-color:${s.backgroundColor || 'transparent'};`;
                if (s.border && s.border !== 'none') styleStr += `border:${s.border};`;
                if (s.borderRadius) styleStr += `border-radius:${s.borderRadius}px;`;
                if (s.padding) styleStr += `padding:${s.padding}px;`;
                if (layoutMode === 'flow') styleStr += 'display:flex;flex-direction:column;gap:8px;align-items:flex-start;';
                section.setAttribute('style', styleStr);

                // Move children from the dropzone into the section
                const dropzone = el.querySelector('.box-dropzone');
                if (dropzone) {
                    Array.from(dropzone.children).forEach(child => {
                        const childClone = child.cloneNode(true);
                        section.appendChild(childClone);
                    });
                }

                if (el.parentNode) {
                    el.parentNode.replaceChild(section, el);
                    // Recursively clean the children inside the new section
                    Array.from(section.children).forEach(child => clean(child));
                }
                return;
            }

            // Legacy box-wrapper (old format) compat
            if (el.classList && el.classList.contains('box-wrapper')) {
                const span = el.querySelector('span');
                if (span && el.parentNode) {
                    el.parentNode.replaceChild(span, el);
                    clean(span);
                    return;
                }
            }
            if (el.classList && (el.classList.contains('dynamic-field-wrapper') || el.classList.contains('field-block'))) {
                const span = el.querySelector('span[t-field]');
                if (span && el.parentNode) {
                    el.parentNode.replaceChild(span, el);
                    clean(span);
                    return;
                }
            }

            // Cleanup residual classes
            if (el.classList) {
                el.classList.remove('c_new', 'selected', 'bg-white');
                if (el.classList.length === 0) el.removeAttribute('class');
            }

            if (el.children) {
                Array.from(el.children).forEach(child => clean(child));
            }
        };
        clean(node);

        // Return to original position if it had one
        if (parent) {
            parent.insertBefore(temp.firstChild, next);
        }
        return temp.firstChild;
    }

    _isStructuralNode(el) {
        if (!el || !el.hasAttribute) return false;
        const tagName = el.tagName ? el.tagName.toLowerCase() : '';
        if (tagName === 't' || tagName === 'cy-qweb-t') return true;
        const qwebAttrs = ['t-foreach', 't-if', 't-elif', 't-else', 't-field', 't-esc', 't-out', 't-call'];
        return qwebAttrs.some(attr => el.hasAttribute(attr));
    }

    _enrichReportDOM(container) {
        // ── Enrich existing report-section boxes saved from previous edits ──
        container.querySelectorAll('div.report-section:not(.box-section-wrapper *)').forEach(section => {
            if (section.closest('.box-section-wrapper')) return;
            // Extract stored config from data attrs or build default
            let cfg;
            try { cfg = section.dataset.boxConfig ? JSON.parse(section.dataset.boxConfig) : null; } catch (e) { cfg = null; }
            if (!cfg) {
                const boxId = section.dataset.boxId || ('box_' + Math.random().toString(36).slice(2, 10));
                cfg = {
                    id: boxId, label: section.dataset.boxLabel || 'Section',
                    style: {
                        width: section.offsetWidth || 300,
                        height: section.offsetHeight || 200,
                        backgroundColor: section.style.backgroundColor || 'transparent',
                        border: section.style.border || '1px solid #ccc',
                        borderRadius: parseInt(section.style.borderRadius) || 4,
                        padding: parseInt(section.style.padding) || 8,
                    },
                    layoutMode: section.dataset.layoutMode || 'free',
                    children: [],
                };
            }

            // Grab all children before replace
            const childNodes = Array.from(section.children);

            const wrapper = document.createElement('div');
            wrapper.className = 'box-section-wrapper';
            wrapper.setAttribute('cy-type', 'box');
            wrapper.setAttribute('data-box-id', cfg.id);
            wrapper.setAttribute('data-box-config', JSON.stringify(cfg));
            wrapper.style.width = (cfg.style.width || 300) + 'px';
            wrapper.style.height = (cfg.style.height || 200) + 'px';
            wrapper.innerHTML = this._buildBoxInnerHTML(cfg);

            section.parentNode.insertBefore(wrapper, section);
            section.remove();

            // Move original children into the new dropzone
            const dropzone = wrapper.querySelector('.box-dropzone');
            childNodes.forEach(child => dropzone.appendChild(child));

            // Wire delete
            wrapper.querySelector('.box-delete-btn').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: 'Delete this section container and all its contents?',
                    confirm: () => {
                        if (this._selectedBoxEl === wrapper) this.closeBoxProps();
                        wrapper.remove();
                    },
                    cancel: () => { },
                });
            };
            this._setupBoxResizeHandles(wrapper);
        });

        const tables = container.querySelectorAll('table:not(.table-wrapper table)');
        tables.forEach(table => {
            if (table.closest('.table-wrapper')) return;
            let targetNode = table;
            while (targetNode.parentElement && this._isStructuralNode(targetNode.parentElement) &&
                targetNode.parentElement.children.length === 1 &&
                !targetNode.parentElement.classList.contains('page')) {
                targetNode = targetNode.parentElement;
            }
            const wrapper = document.createElement('div');
            wrapper.className = 'table-wrapper';
            wrapper.innerHTML = `
                <div class="table-handle-container" contenteditable="false">
                    <div class="table-handle fa fa-bars" title="Drag to move"></div>
                    <div class="table-delete fa fa-trash" title="Delete Table"></div>
                </div>`;
            targetNode.parentNode.insertBefore(wrapper, targetNode);
            wrapper.appendChild(targetNode);
            wrapper.querySelector('.table-delete').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this table?",
                    confirm: async () => {
                        this._removeOrphanedQwebElements && this._removeOrphanedQwebElements(wrapper);
                        wrapper.remove();
                        await this.save_changes(this);
                    },
                    cancel: () => { },
                });
            };
        });

        const fields = container.querySelectorAll('[t-field]:not(.field-block [t-field]):not(.field-container [t-field]), [t-esc]:not(.field-block [t-esc]):not(.field-container [t-esc])');
        fields.forEach(field => {
            if (field.closest('.field-block') || field.closest('table')) return;
            let targetNode = field;
            while (targetNode.parentElement && this._isStructuralNode(targetNode.parentElement) &&
                targetNode.parentElement.children.length === 1 &&
                !targetNode.parentElement.classList.contains('page')) {
                targetNode = targetNode.parentElement;
            }
            const wrapper = document.createElement('div');
            wrapper.className = 'field-block dynamic-field-wrapper';
            wrapper.innerHTML = `
                <div class="field-handle-container" contenteditable="false">
                    <span class="field-handle fa fa-bars" title="Drag to move"></span>
                    <span class="field-delete fa fa-trash" title="Delete Field"></span>
                </div>
                <div class="field-container d-inline-flex gap-1"></div>
            `;
            targetNode.parentNode.insertBefore(wrapper, targetNode);
            wrapper.querySelector('.field-container').appendChild(targetNode);
            wrapper.querySelector('.field-delete').onclick = (e) => {
                e.stopPropagation();
                if (confirm("Delete this field?")) wrapper.remove();
            };
        });

        container.querySelectorAll('.text-node').forEach(n => n.setAttribute('contenteditable', 'false'));
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Box Section: Resize Handles
    // ──────────────────────────────────────────────────────────────────────────

    /**
     * Wire up pointer-based resize logic for all 8 handles on a box wrapper.
     * Stores result back into data-box-config.
     */
    _setupBoxResizeHandles(boxEl) {
        // Remove previous listeners by replacing handle container
        const oldHandles = boxEl.querySelectorAll('.box-resize-handle');
        oldHandles.forEach(h => {
            // Clone replaces to remove old listeners
            const clone = h.cloneNode(true);
            h.parentNode && h.parentNode.replaceChild(clone, h);
        });

        const self = this;
        boxEl.querySelectorAll('.box-resize-handle').forEach(handle => {
            const dir = handle.dataset.dir;
            let startX, startY, startW, startH;

            const onMove = (e) => {
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                let newW = startW;
                let newH = startH;

                if (dir.includes('e')) newW = Math.max(80, startW + dx);
                if (dir.includes('w')) newW = Math.max(80, startW - dx);
                if (dir.includes('s')) newH = Math.max(80, startH + dy);
                if (dir.includes('n')) newH = Math.max(80, startH - dy);

                boxEl.style.width = newW + 'px';
                boxEl.style.height = newH + 'px';

                // Live-update config
                try {
                    const cfg = JSON.parse(boxEl.dataset.boxConfig || '{}');
                    cfg.style = cfg.style || {};
                    cfg.style.width = Math.round(newW);
                    cfg.style.height = Math.round(newH);
                    boxEl.dataset.boxConfig = JSON.stringify(cfg);
                    // Update props panel if this box is selected
                    if (self._selectedBoxEl === boxEl) {
                        self.state.boxConfig.width = cfg.style.width;
                        self.state.boxConfig.height = cfg.style.height;
                    }
                } catch (ex) { }
            };

            const onUp = () => {
                document.removeEventListener('pointermove', onMove);
                document.removeEventListener('pointerup', onUp);
            };

            handle.addEventListener('pointerdown', (e) => {
                if (self.state.previewMode) return;
                e.stopPropagation();
                e.preventDefault();
                startX = e.clientX;
                startY = e.clientY;
                startW = boxEl.offsetWidth;
                startH = boxEl.offsetHeight;
                document.addEventListener('pointermove', onMove);
                document.addEventListener('pointerup', onUp);
            });
        });
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Box Properties Panel – OWL event handlers
    // ──────────────────────────────────────────────────────────────────────────

    /**
     * Open the box properties panel for a given box wrapper element.
     */
    openBoxProps(boxEl) {
        this._selectedBoxEl = boxEl;
        let cfg = {};
        try { cfg = JSON.parse(boxEl.dataset.boxConfig || '{}'); } catch (e) { }
        const s = cfg.style || {};
        this.state.boxConfig = {
            label: cfg.label || 'Section',
            width: s.width || boxEl.offsetWidth || 300,
            height: s.height || boxEl.offsetHeight || 200,
            backgroundColor: s.backgroundColor || 'transparent',
            border: s.border || '1px solid #ccc',
            borderRadius: s.borderRadius !== undefined ? s.borderRadius : 4,
            padding: s.padding !== undefined ? s.padding : 8,
            layoutMode: cfg.layoutMode || 'free',
        };
        this.state.showBoxProps = true;
    }

    closeBoxProps() {
        this._selectedBoxEl = null;
        this.state.showBoxProps = false;
    }

    /**
     * Called when any box property input changes.
     */
    onBoxConfigChange(field, value) {
        const boxEl = this._selectedBoxEl;
        if (!boxEl) return;
        this.state.boxConfig[field] = value;

        let cfg = {};
        try { cfg = JSON.parse(boxEl.dataset.boxConfig || '{}'); } catch (e) { }
        cfg.style = cfg.style || {};

        if (field === 'label') {
            cfg.label = value;
            const labelEl = boxEl.querySelector('.box-label-text');
            if (labelEl) labelEl.textContent = value;
        } else if (field === 'width') {
            const v = Math.max(80, parseInt(value) || 80);
            cfg.style.width = v;
            boxEl.style.width = v + 'px';
        } else if (field === 'height') {
            const v = Math.max(80, parseInt(value) || 80);
            cfg.style.height = v;
            boxEl.style.height = v + 'px';
        } else if (field === 'backgroundColor') {
            cfg.style.backgroundColor = value;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.backgroundColor = value;
        } else if (field === 'border') {
            cfg.style.border = value;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.border = value;
        } else if (field === 'borderRadius') {
            const v = parseInt(value) || 0;
            cfg.style.borderRadius = v;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.borderRadius = v + 'px';
        } else if (field === 'padding') {
            const v = parseInt(value) || 0;
            cfg.style.padding = v;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.padding = v + 'px';
        }

        boxEl.dataset.boxConfig = JSON.stringify(cfg);
    }

    onBoxLayoutModeChange(mode) {
        const boxEl = this._selectedBoxEl;
        if (!boxEl) return;
        this.state.boxConfig.layoutMode = mode;

        let cfg = {};
        try { cfg = JSON.parse(boxEl.dataset.boxConfig || '{}'); } catch (e) { }
        cfg.layoutMode = mode;
        boxEl.dataset.boxConfig = JSON.stringify(cfg);

        const dz = boxEl.querySelector('.box-dropzone');
        if (dz) {
            dz.classList.remove('layout-free', 'layout-flow');
            dz.classList.add('layout-' + mode);
        }
        const badge = boxEl.querySelector('.box-layout-badge');
        if (badge) badge.textContent = mode;
    }

    deleteSelectedBox() {
        const boxEl = this._selectedBoxEl;
        if (!boxEl) return;
        this.closeBoxProps();
        boxEl.remove();
    }

    buildInheritanceXML(changes) {
        let new_inherits = [];
        for (const [key, items] of Object.entries(groupBy(changes, 'template'))) {
            let xpathBlock = "";
            items.forEach(change => {
                const newNodes = Array.from(change.el.children)
                    .filter(child => !child.hasAttribute('cy-xpath') && child.classList.contains('c_new'));

                if (change.structChanged) {
                    const clonedZone = change.el.cloneNode(true);
                    const cleaned = this._cleanStudioAttrs(clonedZone);
                    let content = new XMLSerializer().serializeToString(cleaned).replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                    xpathBlock += `<xpath expr="${change.xpath}" position="replace">${content}</xpath>`;
                    return;
                }

                if (newNodes.length) {
                    newNodes.forEach(node => {
                        const cloned = node.cloneNode(true);
                        const cleaned = this._cleanStudioAttrs(cloned);
                        let content = new XMLSerializer().serializeToString(cleaned).replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                        xpathBlock += `<xpath expr="${change.xpath}" position="inside">${content}</xpath>`;
                    });
                    return;
                }

                if (this._isStructuralNode(change.el)) return;
                const cloned = change.el.cloneNode(true);
                const cleaned = this._cleanStudioAttrs(cloned);
                let content = new XMLSerializer().serializeToString(cleaned).replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                xpathBlock += `<xpath expr="${change.xpath}" position="replace">${content}</xpath>`;
            });
            if (xpathBlock.trim()) {
                new_inherits.push({ key, xpathBlocks: `<data>\n${xpathBlock}\n</data>` });
            }
        }
        return new_inherits;
    }

    _removeTableToolbar() {
        document.querySelectorAll('.table-toolbar').forEach(t => t.remove());
    }

    _setupTextNodeEvents(textNode) { }
}

EditReport.template = "custom_report.edit_report";
registry.category("actions").add("edit_report", EditReport);
