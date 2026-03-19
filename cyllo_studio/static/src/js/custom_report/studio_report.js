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
            if (!wasSelected || el.classList.contains('table-wrapper') || el.classList.contains('field-block')) {
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
                    item.className = 'box rounded-2 c_new box-wrapper';
                    item.innerHTML = '<div class="box-handle" contenteditable="false"></div><span>New box</span>';
                    item.setAttribute('cy-type', 'box');
                    item.style.border = '1px solid #000';
                    item.style.padding = '10px';
                    item.style.cursor = 'default';
                    item.style.opacity = '1';
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

                    item.querySelector('.table-delete').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            title: "Delete Table",
                            body: "Are you sure you want to delete this table?",
                            confirm: async () => {
                                // Remove orphaned <t> siblings BEFORE removing the wrapper
                                // (HTML foster-parenting leaves them stranded in the zone).
                                self._removeOrphanedQwebElements(item);
                                item.remove();
                                await self.save_changes(self);
                            },
                            cancel: () => { },
                        });
                    };
                }

                // ── LIVE SYNC: UI -> Source ──────────────────────────────────
                // If source editor is open, refresh its content to show the
                // newly added element XML immediately.
                if (self.state.showSourceEditor) {
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
                // Data rows — use t-foreach with the model
                html += `
                    <t t-set="section_records" t-value="docs.filtered(lambda r: r.account_type in ${this._pythonDomainValues(section.domain)})"/>
                    <t t-foreach="section_records" t-as="rec">
                        <tr class="data-row" style="border-bottom: 1px solid #eee;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    if (col.fieldType === 'many2one') {
                        html += `<td style="${colStyle(col, align)}"><span t-field="rec.${col.field}"/></td>`;
                    } else if (isNumeric(col.fieldType)) {
                        html += `<td style="${colStyle(col, align)}"><span t-field="rec.${col.field}" t-att-class="rec.${col.field} &lt; 0 and 'text-danger' or ''"/></td>`;
                    } else {
                        html += `<td style="${colStyle(col, align)}"><span t-field="rec.${col.field}"/></td>`;
                    }
                });
                html += `
                        </tr>
                    </t>`;
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
                html += `<td style="${colStyle(col, align)}"><span t-field="line.${col.field}"/></td>`;
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
                    html += `<td style="${colStyle(col, align)}"><span t-field="line.${col.field}"/></td>`;
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
                <t t-foreach="docs" t-as="rec">
                    <tr style="border-bottom: 1px solid #f8f9fa;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    if (col.field) {
                        html += `<td style="${colStyle(col, align)}"><span t-field="rec.${col.field}"/></td>`;
                    } else {
                        html += `<td style="padding: 8px;">${col.label || ''}</td>`;
                    }
                });
                html += `
                    </tr>
                </t>`;
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

    _cleanStudioAttrs(el) {
        const studioAttrs = ['cy-xpath', 'cy-template', 'cy-type', 'draggable', 'data-type', 'cy-config'];
        const clean = (node) => {
            studioAttrs.forEach(a => node.removeAttribute && node.removeAttribute(a));
            if (node.removeAttribute) {
                node.removeAttribute('onmouseover');
                node.removeAttribute('onmouseout');
                node.removeAttribute('onclick');
                node.removeAttribute('contenteditable');
            }
            if (node.style) {
                if (node.style.cursor) node.style.removeProperty('cursor');
                if (node.style.outline) node.style.removeProperty('outline');
                if (node.style.opacity) node.style.removeProperty('opacity');
                if (node.getAttribute && node.getAttribute('style') === '') node.removeAttribute('style');
            }

            // Remove handles!
            const handles = node.querySelectorAll ? Array.from(node.querySelectorAll('.table-handle, .box-handle, .field-handle, .tcm-delete-table, .table-toolbar, .text-handle, .resize-handle, .field-delete, .table-handle-container, .table-delete, .field-handle-container')) : [];
            handles.forEach(h => h.remove());

            // Unwrap wrappers if they are purely studio constructs
            // We always unwrap these to keep the final XML clean and prevent redundant nesting.
            const wrappers = node.querySelectorAll ? Array.from(node.querySelectorAll('.table-wrapper, .field-block, .field-container, .dynamic-field-wrapper, .table-handle-container, .field-handle-container')) : [];
            wrappers.forEach(w => {
                while (w.firstChild) {
                    w.parentNode.insertBefore(w.firstChild, w);
                }
                w.remove();
            });

            // Safety net: strip any residual empty structural <t>/<cy-qweb-t> nodes that
            // survived foster-parenting and were not caught by _removeOrphanedQwebElements.
            const structOrphans = node.querySelectorAll ? Array.from(node.querySelectorAll('t, cy-qweb-t')) : [];
            structOrphans.forEach(el => {
                if (!el.textContent.trim() && el.children.length === 0) el.remove();
            });

            // Remove remaining layout classes and attributes from logical blocks
            if (node.classList) {
                node.classList.remove('field-block', 'dynamic-field-wrapper', 'table-wrapper', 'c_new', 'bg-white', 'selected');
                if (node.classList.length === 0) node.removeAttribute('class');
            }

            // Bug 2: Remove layout placeholders (Address block, etc.)
            // These are injected by Odoo during rendering if content is empty.
            // We should NOT save them back into the architecture.
            const placeholders = node.querySelectorAll ? Array.from(node.querySelectorAll('.bg-light.border-1.rounded')) : [];
            placeholders.forEach(p => {
                if (p.textContent.includes('Address block') ||
                    p.textContent.includes('Information block') ||
                    p.textContent.includes('Company address block') ||
                    p.textContent.includes('Company details block')) {
                    p.remove();
                }
            });

            // If the node ITSELF is a handle, remove its content or itself if possible
            // but usually we are cleaning a branch.
            if (node.classList && (node.classList.contains('table-handle') || node.classList.contains('box-handle') || node.classList.contains('field-handle') || node.classList.contains('text-handle') || node.classList.contains('resize-handle') || node.classList.contains('field-delete'))) {
                node.innerHTML = '';
            }

            Array.from(node.children || []).forEach(clean);
        };
        clean(el);
    }

    _isStructuralNode(el) {
        if (!el) return false;
        const tagName = el.tagName ? el.tagName.toLowerCase() : '';
        // Known structural tags
        if (tagName === 't' || tagName === 'cy-qweb-t') return true;
        // Any node with QWeb control directives is structural
        if (
            el.hasAttribute('t-foreach') ||
            el.hasAttribute('t-set') ||
            el.hasAttribute('t-call') ||
            el.hasAttribute('t-if') ||
            el.hasAttribute('t-elif') ||
            el.hasAttribute('t-else')
        ) return true;
        return false;
    }

    /**
     * Finds existing tables and fields in the report and adds the necessary
     * wrappers and handles for Studio manipulation.
     */
    _enrichReportDOM(container) {
        // 1. Wrap existing tables
        const tables = container.querySelectorAll('table:not(.table-wrapper table)');
        tables.forEach(table => {
            if (table.closest('.table-wrapper')) return;

            // Check if table is wrapped in structural nodes (t-foreach, t-set, etc)
            // We wrap ALL consecutive structural parents that only contain this table
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

            //            wrapper.querySelector('.table-delete').onclick = (e) => {
            //                e.stopPropagation();
            //                if (confirm("Delete this table?")) wrapper.remove();
            //            };
            wrapper.querySelector('.table-delete').onclick = (e) => {
                e.stopPropagation();

                this.dialog.add(ConfirmationDialog, {
                    title: "Delete Table",
                    body: "Are you sure you want to delete this table?",
                    confirm: async () => {
                        // Remove orphaned <t> siblings BEFORE removing the wrapper
                        // (HTML foster-parenting leaves them stranded in the zone).
                        this._removeOrphanedQwebElements(wrapper);
                        wrapper.remove();
                        await this.save_changes(this);
                    },
                    cancel: () => { },
                });
            };
        });

        // 2. Wrap existing fields (t-field or t-esc with specific paths)
        // We look for spans/divs with t-field, excluding those already wrapped or in tables
        const fields = container.querySelectorAll('[t-field]:not(.field-block [t-field]):not(.field-container [t-field]), [t-esc]:not(.field-block [t-esc]):not(.field-container [t-esc])');
        fields.forEach(field => {
            if (field.closest('.field-block') || field.closest('table')) return;

            // Check if field is wrapped in structural nodes (t-foreach, etc)
            let targetNode = field;
            while (targetNode.parentElement && this._isStructuralNode(targetNode.parentElement) &&
                targetNode.parentElement.children.length === 1 &&
                !targetNode.parentElement.classList.contains('page')) {
                targetNode = targetNode.parentElement;
            }

            // For simple fields (like in an address block), wrap them
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

        // 3. Mark salvaged text nodes as ready
        // (No handles needed, just ensure they are targetable)
        const textNodes = container.querySelectorAll('.text-node');
        textNodes.forEach(textNode => {
            textNode.setAttribute('contenteditable', 'false');
        });
    }

    buildInheritanceXML(changes) {
        let new_inherits = [];

        for (const [key, items] of Object.entries(groupBy(changes, 'template'))) {
            let xpathBlock = "";

            items.forEach(change => {
                const newNodes = Array.from(change.el.children)
                    .filter(child => !child.hasAttribute('cy-xpath') && child.classList.contains('c_new'));

                // ── STRUCTURAL CHANGE / DELETION DETECTION ──────────────────
                // If the zone has structural changes (deletions or reorders),
                // we MUST emit a zone-level 'replace' to reflect the final state.
                // Partial inside/replace logic won't capture the absence of a node.
                if (change.structChanged) {
                    const clonedZone = change.el.cloneNode(true);
                    this._cleanStudioAttrs(clonedZone);
                    clonedZone.classList.remove('selected', 'c_new', 'table-wrapper', 'box-wrapper', 'dynamic-field-wrapper', 'field-block');
                    if (clonedZone.classList.length === 0) clonedZone.removeAttribute('class');

                    let content = new XMLSerializer()
                        .serializeToString(clonedZone)
                        .replace(/ xmlns="[^"]*"/g, "")
                        .replace(/<br>/gi, '<br/>');

                    xpathBlock += `
                    <xpath expr="${change.xpath}" position="replace">
                        ${content}
                    </xpath>`;
                    return;
                }

                // If only additions (no deletions/reorders), use relative "inside" XPath.
                if (newNodes.length) {
                    newNodes.forEach(node => {
                        const cloned = node.cloneNode(true);
                        this._cleanStudioAttrs(cloned);
                        cloned.classList.remove('selected', 'c_new', 'table-wrapper', 'box-wrapper', 'dynamic-field-wrapper', 'field-block');
                        if (cloned.classList.length === 0) cloned.removeAttribute('class');

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

                // Text-only edit or attribute edit: replace the element
                // We skip replacing structural nodes (t-foreach, etc.) directly
                // unless it is a structural change (handled above).
                if (this._isStructuralNode(change.el)) {
                    console.warn("[Cyllo Studio] Skipping replacement of structural node:", change.xpath);
                    return;
                }

                const cloned = change.el.cloneNode(true);
                this._cleanStudioAttrs(cloned);
                cloned.classList.remove('selected', 'c_new', 'table-wrapper', 'box-wrapper', 'dynamic-field-wrapper', 'field-block');
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

    _removeTableToolbar() {
        document.querySelectorAll('.table-toolbar').forEach(t => t.remove());
    }

    _setupTextNodeEvents(textNode) {
        // No manual listeners needed anymore as we switched to MediumEditor-first interaction
    }
}

EditReport.template = "custom_report.edit_report";

registry.category("actions").add("edit_report", EditReport);
