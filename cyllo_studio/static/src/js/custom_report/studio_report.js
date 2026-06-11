/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useRef, onMounted, onWillUnmount, useState, onWillStart, onPatched } from "@odoo/owl";
import { StudioFieldSelectorPopover } from "@cyllo_studio/js/studio_field_selector_popover";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { usePopover } from "@web/core/popover/popover_hook";
import { groupBy } from "@web/core/utils/arrays";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { QrMixin } from "@cyllo_studio/js/custom_report/studio_report_qr";
import { BoxMixin } from "@cyllo_studio/js/custom_report/studio_report_box";
import { SignMixin } from "@cyllo_studio/js/custom_report/studio_report_sign";
import { RemoveSessions } from "@cyllo_studio/js/root/studio_wrapper";

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
            previewUrl: false,
            showSourceEditor: false,
            sourceCode: "",
            showResetDialog: false,
            showActionsMenu: false,
            showTemplateDialog: false,
            templateForm: {
                name: "",
                description: "",
                category: "",
            },
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
            // ── Signature Properties Panel state ──
            showSignProps: false,
            signConfig: {
                role: 'customer',
                label: 'Authorized Signature',
                required: true,
                show_date: false,
                show_name: false,
                width: 200,
                height: 100,
                alignment: 'left',
            },
            analytics: {
                total_scans: 0,
                recent_scans: [],
            },
            hasQr: false,
            hasSign: false,
            hasOverflow: false
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
            console.log('params',params,this)

            // Hide the Cyllo sidebar logic per user request
            this._cyElsToRestore = [];

            // 1. Hide the exact submenu box requested (and firmly use !important to block OWL patches)
            const submenuBox = document.querySelector('.cy-submenu-box');
            if (submenuBox) {
                this._cyElsToRestore.push({ el: submenuBox, display: submenuBox.style.display || '' });
                submenuBox.style.setProperty('display', 'none', 'important');

                // 2. Hide the sibling wrapper / parent container that holds the dark sidebar
                const parentNav = submenuBox.parentElement;
                if (parentNav) {
                    this._cyElsToRestore.push({ el: parentNav, display: parentNav.style.display || '' });
                    parentNav.style.setProperty('display', 'none', 'important');

                    // 3. Find the closest flex/grid ancestor
                    let layoutContainer = parentNav.parentElement;
                    while (layoutContainer && layoutContainer.tagName !== 'BODY') {
                        const style = window.getComputedStyle(layoutContainer);
                        if (style.display.includes('flex') || style.display.includes('grid')) {
                            break;
                        }
                        layoutContainer = layoutContainer.parentElement;
                    }

                    // 4. Force the content sibling to take full width
                    if (layoutContainer && layoutContainer.tagName !== 'BODY') {
                        Array.from(layoutContainer.children).forEach(child => {
                            if (!child.contains(parentNav) && child !== parentNav && !child.classList.contains('o_navbar')) {
                                this._cyElsToRestore.push({
                                    el: child,
                                    width: child.style.width || '',
                                    flex: child.style.flex || '',
                                    maxWidth: child.style.maxWidth || '',
                                    marginLeft: child.style.marginLeft || '',
                                    paddingLeft: child.style.paddingLeft || ''
                                });
                                child.style.setProperty('width', '100%', 'important');
                                child.style.setProperty('flex', '1 1 auto', 'important');
                                child.style.setProperty('max-width', '100%', 'important');
                                child.style.setProperty('margin-left', '0', 'important');
                                child.style.setProperty('padding-left', '0', 'important');
                            }
                        });
                    }
                }

                // Fallback direct kills for sticky buttons that might escape
                const sideItems = document.querySelectorAll('.cy_dashboard_back-btn, .cy-left-sidebar, .cy-submenu-logo, #accordionSidebar, .cy-NavHeader');
                sideItems.forEach(el => {
                    this._cyElsToRestore.push({ el: el, display: el.style.display || '' });
                    el.style.setProperty('display', 'none', 'important');
                });

                // 5. Shift Action Manager down to respect Cyllo's 50px top navbar
                const actionManager = document.querySelector('.o_action_manager');
                if (actionManager) {
                    const isAlreadyTracked = this._cyElsToRestore.some(item => item.el === actionManager);
                    if (!isAlreadyTracked) {
                        this._cyElsToRestore.push({
                            el: actionManager,
                            width: actionManager.style.width || '',
                            marginLeft: actionManager.style.marginLeft || '',
                            paddingLeft: actionManager.style.paddingLeft || ''
                        });
                    }
                    actionManager.style.setProperty('width', '100%', 'important');
                    actionManager.style.setProperty('height', '100%', 'important');
                    actionManager.style.setProperty('margin-left', '0', 'important');
                    actionManager.style.setProperty('padding-left', '0', 'important');
                    actionManager.style.setProperty('margin-top', '0', 'important');
                }

                // 6. Force the main content container to take full height
                const content = document.querySelector('.o_content');
                if (content) {
                    this._cyElsToRestore.push({
                        el: content,
                        height: content.style.height || '',
                        maxHeight: content.style.maxHeight || '',
                        overflow: content.style.overflow || ''
                    });
                    content.style.setProperty('height', '100vh', 'important');
                    content.style.setProperty('max-height', '100vh', 'important');
                    content.style.setProperty('overflow', 'hidden', 'important');
                }
            }

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
            await this._fetchPreviewData();
        });

        onWillUnmount(() => {
            if (this._cyElsToRestore && this._cyElsToRestore.length > 0) {
                this._cyElsToRestore.forEach(item => {
                    if (item.display !== undefined) item.el.style.display = item.display;
                    if (item.width !== undefined) item.el.style.width = item.width;
                    if (item.flex !== undefined) item.el.style.flex = item.flex;
                    if (item.maxWidth !== undefined) item.el.style.maxWidth = item.maxWidth;
                    if (item.marginLeft !== undefined) item.el.style.marginLeft = item.marginLeft;
                    if (item.paddingLeft !== undefined) item.el.style.paddingLeft = item.paddingLeft;
                });
                this._cyElsToRestore = [];
            }
        });

        onPatched(() => {
            // Re-setup sortable if the component was patched (e.g. after modal close)
            // to ensure listeners are still attached to the live DOM elements.
            this._setupSortable();
        });
    }

    _setupReportFrame(arch) {
        this._loadedArch = arch;
        this._updateHasQr(arch);
        this._updateHasSign(arch);
        this.reportFrameRef.el.innerHTML = arch;
        const editableArea = this.reportFrameRef.el;

        // Enrich existing DOM with Studio wrappers/handles
        this._enrichReportDOM(editableArea);

        // Re-check sign presence after enrichment (o_sign_placeholder → sign-wrapper)
        this._updateHasSign();

        this._startOverflowGuardObserver();

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

            // ── Settings Button Click Handler ──
            if (el.closest('.box-settings-btn, .table-settings, .field-settings, .sign-settings-btn')) {
                e.preventDefault();
                e.stopPropagation();
                let targetEl = el.closest('.box-section-wrapper, .table-wrapper, .field-block, .sign-wrapper');
                const btnEl = el.closest('.box-settings-btn, .table-settings, .field-settings, .sign-settings-btn');
                if (targetEl && window.SettingsButton) {
                    const sb = new window.SettingsButton();
                    sb.base = { options: { owner: self } };
                    sb.showPopup(targetEl, btnEl);
                }
                return;
            }

            // ── Box toolbar / resize handle – ignore for selection ──
            if (el.closest('.box-toolbar') || el.closest('.box-resize-handles') || el.closest('.table-handle-container') || el.closest('.field-handle-container') || el.closest('.sign-toolbar')) {
                return;
            }

            // ── Box drop zone click logic ──
            const boxWrapper = el.closest('.box-section-wrapper');
            const boxDropzone = el.closest('.box-dropzone');
            if (boxWrapper) {
                if (el === boxWrapper || el === boxDropzone) {
                    e.stopPropagation();
                    el = boxWrapper;
                } else {
                    e.stopPropagation();
                }
            }

            // ── Sign click logic ──
            const signWrapper = el.closest('.sign-wrapper');
            if (signWrapper) {
                e.stopPropagation();
                el = signWrapper;
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

            // For .text-node: skip wasSelected gate — always open editor on any click
            const isTextNode = el.classList.contains('text-node');

            // ── Issue 5: Check if this element was just dropped (data-needs-edit flag) ──
            const isNewDrop = el.dataset && el.dataset.needsEdit === '1';
            if (isNewDrop) {
                delete el.dataset.needsEdit;
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
            // text-node: ALWAYS open editor on any click (no wasSelected gate)
            // other elements: open editor only if already selected (or just dropped)
            // Allow MediumEditor for all elements
            const shouldSkipEditor = false;

            const isAlwaysOpenElement = isTextNode ||
                el.classList.contains('box-section-wrapper') ||
                el.classList.contains('table-wrapper') ||
                el.classList.contains('sign-wrapper') ||
                el.classList.contains('s_qr_block') ||
                el.classList.contains('field-block');

            const isMediumEditorElement = (element) => {
                return element && (
                    element.classList.contains('text-node') ||
                    element.classList.contains('box-section-wrapper') ||
                    element.classList.contains('table-wrapper') ||
                    element.classList.contains('sign-wrapper') ||
                    element.classList.contains('s_qr_block') ||
                    element.classList.contains('field-block')
                );
            };

            if (shouldSkipEditor || (!isAlwaysOpenElement && !wasSelected && !isNewDrop)) {
                if (self.editor) {
                    const prevEl = self.editor.elements[0];
                    self.editor.destroy();
                    self.editor = null;
                    if (isMediumEditorElement(prevEl)) {
                        prevEl.setAttribute('contenteditable', 'false');
                    }
                }
                return;
            }

            if (self.editor) {
                const prevEl = self.editor.elements[0];
                self.editor.destroy();
                if (isMediumEditorElement(prevEl)) {
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

            // Bug fix: enable contenteditable before MediumEditor init for structural blocks
            if (isMediumEditorElement(el)) {
                el.setAttribute('contenteditable', 'true');
            }

            self.editor = new MediumEditor(el, {
                toolbar: {
                    buttons: [
                        'settingsButton', 'bold', 'italic', 'underline', 'strikethrough',
                        'h1', 'h3', 'quote', 'anchor', 'deleteElement',
                    ],
                    // No relativeContainer — let MediumEditor float near the selected text
                },
                extensions: {
                    'deleteElement': new window.DeleteButton(),
                    'undoButton': new window.UndoButton(),
                    'redoButton': new window.RedoButton(),
                    'settingsButton': window.SettingsButton ? new window.SettingsButton() : null,
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
            // Clear preview state so the editable frame is shown
            this.state.previewUrl = false;
            this.state.previewHtml = false;
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
        this._updateHasQr();
        this._updateHasSign();
        const data = await this.rpc("/cyllo_studio/get_report_preview_data", {
            template: this._template,
            res_model: this._resModel,
        });
        if (data.success) {
            this.state.records = data.record_ids;
            this.state.reportInfo = data.report;
            this.state.paperFormats = data.paper_formats;
            this.state.analytics = data.analytics || { total_scans: 0, recent_scans: [], tracking_enabled: false };

            // Rely purely on the DOM/arch to decide visibility.
            this._updateHasQr();

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
            // Use the URL-based preview so Odoo's CSS/JS assets load correctly
            // inside the iframe (srcdoc breaks relative asset bundle paths).
            this.state.previewUrl = res.preview_url || false;
            this.state.previewHtml = false;
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
        else {
            // Paper format changed — re-evaluate overflow boundary immediately
            requestAnimationFrame(() => this._updateOverflowGuard());
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
            if (hasChanges && this.reportFrameRef.el) {
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

    async _savePendingDesignIfMounted() {
        const hasChanges = $('.c_new').length > 0 || (this.undoManager && this.undoManager.canUndo());
        if (hasChanges && this.reportFrameRef.el) {
            await this.save_changes(this);
        }
    }

    async saveReportFromActions() {
        this.state.showActionsMenu = false;
        if (!this.reportFrameRef.el) {
            this.notification.add("Switch off Preview before saving report layout changes.", { type: "warning" });
            return;
        }
        await this.save_changes(this);
    }

    openSaveTemplateDialog() {
        this.state.showActionsMenu = false;
        this.state.templateForm = {
            name: this.state.reportInfo.name ? `${this.state.reportInfo.name} Template` : "",
            description: "",
            category: "",
        };
        this.state.showTemplateDialog = true;
    }

    closeSaveTemplateDialog() {
        this.state.showTemplateDialog = false;
    }

    async saveAsTemplate() {
        const form = this.state.templateForm;
        if (!form.name || !form.name.trim()) {
            this.notification.add("Template Name is required.", { type: "warning" });
            return;
        }

        try {
            await this._savePendingDesignIfMounted();
            this.state.isSaving = true;
            const res = await this.rpc('/cyllo_studio/save_report_template', {
                template: this._template,
                name: form.name,
                description: form.description,
                category: form.category,
            });
            if (res.success) {
                this.state.showTemplateDialog = false;
                this.notification.add("Template saved successfully.", { type: "success" });
            } else {
                this.notification.add(res.error || "Template save failed.", { type: "danger" });
            }
        } finally {
            this.state.isSaving = false;
        }
    }

    async exportTemplate() {
        this.state.showActionsMenu = false;
        try {
            await this._savePendingDesignIfMounted();
            this.state.isSaving = true;
            const res = await this.rpc('/cyllo_studio/export_report_template', {
                template: this._template,
            });
            if (!res.success) {
                this.notification.add(res.error || "Template export failed.", { type: "danger" });
                return;
            }
            const blob = new Blob([JSON.stringify(res.payload, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = res.filename || "report_template.json";
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        } finally {
            this.state.isSaving = false;
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
                active_id: activeId,
                active_model: report.model,
                report_pdf_no_attachment: true,
                cyllo_studio_pdf: true,
            }
        });
    }

    async onSignReport() {
        const report = this.state.reportInfo;
        const activeId = this.state.records[this.state.currentIndex];
        if (!report.id || !activeId) return;

        this.state.isSaving = true;
        try {
            // First save to ensure the node is persisted
            await this.save_changes(this);

            try {
                // Call the universal backend action
                const action = await this.orm.call(
                    'ir.actions.report',
                    'action_send_for_signature',
                    [[report.id], [activeId]]
                );

                if (action) {
                    this.action.doAction(action);
                }
            } catch (err) {
                if (err && err.message && (err.message.includes('AttributeError') || err.message.includes('action_send_for_signature'))) {
                    this.notification.add(
                        "The 'Sign' module is required to use this feature. Please install the 'cyllo_sign' module.",
                        { type: "warning", sticky: true }
                    );
                } else {
                    throw err;
                }
            }
        } finally {
            this.state.isSaving = false;
        }
    }


    onOpenFullAnalytics() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'QR Scan Analytics',
            res_model: 'qr.scan.event',
            view_mode: 'tree,form,pivot,graph',
            views: [[false, 'tree'], [false, 'form'], [false, 'pivot'], [false, 'graph']],
            domain: [['report_id', '=', this.state.reportInfo.id]],
            target: 'current',
        });
    }

    _updateHasSign(arch = null) {
        const targetArch = arch || this._loadedArch || '';
        // Check in arch string
        const hasSignInArch = /cy-type=['"]sign['"]|o_sign_placeholder|sign-wrapper|\[\[SIGN:/.test(targetArch);
        // Check in live DOM
        const signEls = this.reportFrameRef.el?.querySelectorAll('.sign-wrapper, [cy-type="sign"], .o_sign_placeholder');
        const hasSignInDom = signEls && signEls.length > 0;
        this.state.hasSign = hasSignInArch || hasSignInDom;
    }

    _updateHasQr(arch = null) {
        const targetArch = arch || this._loadedArch || '';
        const qrRegex = /cy-type=['"]qr['"]|s_qr_block|symbology['"]\s*:\s*['"]QR['"]|['"]QR['"]\s*:\s*symbology/;
        const hasQrInArch = qrRegex.test(targetArch);

        // Check for Studio-managed QR blocks
        const qrBlocks = this.reportFrameRef.el?.querySelectorAll('.s_qr_block, [cy-type="qr"]');
        const hasQrInDom = qrBlocks && qrBlocks.length > 0;

        // Also check for raw Odoo barcode widgets (img or svg) that might be QRs
        const rawBarcodes = this.reportFrameRef.el?.querySelectorAll('img[src*="barcode"][src*="QR"], img[src*="barcode"][src*="qr"], svg[data-code-type="QR"]');
        const hasRawQrInDom = rawBarcodes && rawBarcodes.length > 0;

        if (hasQrInDom) {
            let tracked = false;
            qrBlocks.forEach(el => {
                try {
                    const cfg = JSON.parse(el.dataset.qrConfig || '{}');
                    // Assume tracked unless explicitly disabled in config
                    if (cfg.config && cfg.config.trackAnalytics !== false) tracked = true;
                } catch (e) { }
            });
            this.state.hasQr = tracked;
        } else if (hasRawQrInDom) {
            // If we see a raw QR barcode in the DOM, show analytics if tracking was ever enabled for this report
            this.state.hasQr = !!(this.state.analytics && this.state.analytics.tracking_enabled);
        } else {
            // If no QR is rendered in the current view, hide the analytics panel.
            this.state.hasQr = false;
        }

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
                <span class="box-drag-handle ri-drag-move-line" title="Drag to move"></span>
                <span class="box-settings-btn ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                <span class="box-label-text">${label}</span>
                <span class="box-layout-badge">${layoutMode}</span>
                <span class="box-delete-btn ri-delete-bin-line" title="Delete Section"></span>
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
            draggable: '.table-wrapper, .box-section-wrapper, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="dynamic"]:not(.dynamic-field-wrapper *), [cy-type="qr"], [cy-type="sign"]',
            handle: '.table-handle, .box-drag-handle, .box-toolbar, .field-handle, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="qr"], .sign-toolbar',
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
                    // Transform dropped snippet into an immediately-editable text node
                    item.className = 'text-node c_new selected';
                    item.setAttribute('contenteditable', 'true');
                    item.innerHTML = 'Click to edit';
                    item.style.opacity = '1';

                    // Destroy any existing editor first
                    if (self.editor) {
                        try { self.editor.destroy(); } catch (_) { }
                        self.editor = null;
                    }

                    // Init MediumEditor immediately so the node is ready to type into
                    setTimeout(() => {
                        self.editor = new MediumEditor(item, {
                            toolbar: {
                                buttons: [
                                    'settingsButton', 'bold', 'italic', 'underline', 'strikethrough',
                                    'h1', 'h3', 'quote', 'anchor', 'deleteElement',
                                ],
                            },
                            extensions: {
                                'settingsButton': window.SettingsButton ? new window.SettingsButton() : null,
                                'deleteElement': new window.DeleteButton(),
                                'undoButton': new window.UndoButton(),
                                'redoButton': new window.RedoButton(),
                            },
                            owner: self,
                            placeholder: false,
                            disableExtraSpaces: true,
                        });
                        self.editor.selectElement(item);
                        item.focus();
                    }, 0);

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
                            <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="field-settings ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                            <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                        </div>
                        <div class="field-container">
                            <strong class="field-label" style="margin-right: 4px;">${fieldInfo.string}: </strong>
                            ${fieldInfo.type === 'binary' ? `<img t-if="doc.${fieldPath}" src="/web/static/src/img/mimetypes/image.svg" t-att-src="doc.env['ir.actions.report'].get_safe_image_data_uri(doc.${fieldPath})" style="max-width: 100%; width: 200px; height: auto; object-fit: contain;" title="${fieldInfo.string}" />` : `<span t-field="doc.${fieldPath}" title="${fieldInfo.string}">${fieldPath}</span>`}
                        </div>`;
                    item.setAttribute('cy-type', 'dynamic');
                    item.style.opacity = '1';
                    item.querySelector('.field-delete').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: "Are you sure you want to delete this field?",
                            confirm: () => item.remove(),
                            cancel: () => { },
                        });
                        // if (confirm('Delete this field?')) item.remove();
                    };
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
                            <div class="table-handle ri-drag-move-line" title="Drag to move"></div>
                            <div class="table-settings ri-settings-3-line" title="Settings" ></div>
                            <div class="table-delete ri-delete-bin-line" title="Delete Table"></div>
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

                if (type === 'sign') {
                    const signId = 'sign_' + Math.random().toString(36).slice(2, 10);
                    const defaultCfg = {
                        role: 'customer',
                        label: 'Authorized Signature',
                        required: true,
                        show_date: false,
                        show_name: false,
                        width: 200,
                        height: 100,
                        alignment: 'left',
                    };
                    item.className = 'sign-wrapper c_new';
                    item.setAttribute('cy-type', 'sign');
                    item.setAttribute('data-sign-id', signId);
                    item.setAttribute('data-sign-config', JSON.stringify(defaultCfg));
                    item.dataset.role = defaultCfg.role;
                    item.style.width = defaultCfg.width + 'px';
                    item.style.height = defaultCfg.height + 'px';
                    item.style.opacity = '1';
                    item.style.cursor = 'default';
                    item.style.textAlign = defaultCfg.alignment;

                    item.innerHTML = `
                        <div class="sign-toolbar" contenteditable="false">
                            <span class="sign-drag-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="sign-settings-btn ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                            <span class="sign-delete-btn ri-delete-bin-line" title="Delete Signature"></span>
                        </div>
                        <div class="sign-content-wrapper" style="pointer-events: none; border: 2px dashed #ccc; width: 100%; height: 100%; padding: 10px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; position: relative;">
                            <div class="sign-watermark" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.1; font-size: 40px; color: #9ea700;"><i class="fa fa-pencil"></i></div>
                            <div class="sign-role-badge" style="position: absolute; top: -10px; right: 10px; background: #9ea700; color: white; padding: 2px 6px; font-size: 10px; border-radius: 4px; text-transform: uppercase;">${defaultCfg.role}</div>
                            <div class="sign-empty-line" style="border-bottom: 1px solid #333; width: 80%; margin: 10px auto;"></div>
                            <p class="sign-label" style="font-weight: bold; font-size: 14px; margin: 0;">${defaultCfg.label}</p>
                        </div>
                        <div class="sign-resize-handles" contenteditable="false">
                            <div class="sign-resize-handle" data-dir="se"></div>
                        </div>
                    `;

                    item.querySelector('.sign-delete-btn').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: 'Delete this Signature?',
                            confirm: () => {
                                if (self.state.showSignProps && self._selectedSignEl === item) {
                                    self.closeSignProps();
                                }
                                item.remove();
                                self._updateHasSign();
                            },
                            cancel: () => { },
                        });
                    };

                    self._setupSignResizeHandles(item);
                    self._updateHasSign();
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

            draggable: '.table-wrapper, .box-wrapper, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="dynamic"]:not(.dynamic-field-wrapper *), [cy-type="qr"], [cy-type="sign"]',
            handle: '.table-handle, .box-handle, .field-handle, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="dynamic"], [cy-type="qr"], .sign-toolbar',
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
                const item = evt.item;
                const fromPanel = item.dataset._fromPanel === '1';

                if (!fromPanel) return;

                const type = item.dataset.type; // read BEFORE anything
                delete item.dataset._fromPanel;

                // hide while async runs
                item.style.opacity = '0.4';

                if (type === 'text') {
                    // Transform dropped snippet into an immediately-editable text node
                    item.className = 'text-node c_new selected';
                    item.setAttribute('contenteditable', 'true');
                    item.innerHTML = 'Click to edit';
                    item.style.position = '';
                    item.style.left = '';
                    item.style.top = '';
                    item.style.opacity = '1';

                    // Destroy any existing editor first
                    if (self.editor) {
                        try { self.editor.destroy(); } catch (_) { }
                        self.editor = null;
                    }

                    // Init MediumEditor immediately so the node is ready to type into
                    setTimeout(() => {
                        self.editor = new MediumEditor(item, {
                            toolbar: {
                                buttons: [
                                    'settingsButton', 'bold', 'italic', 'underline', 'strikethrough',
                                    'h1', 'h3', 'quote', 'anchor', 'deleteElement',
                                ],
                            },
                            extensions: {
                                'settingsButton': window.SettingsButton ? new window.SettingsButton() : null,
                                'deleteElement': new window.DeleteButton(),
                                'undoButton': new window.UndoButton(),
                                'redoButton': new window.RedoButton(),
                            },
                            owner: self,
                            placeholder: false,
                            disableExtraSpaces: true,
                        });
                        self.editor.selectElement(item);
                        item.focus();
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
                            <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                        </div>
                        <div class="field-container" style="display: inline-block;">
                            <strong class="field-label" style="margin-right: 4px;">${fieldInfo.string}: </strong>
                            ${fieldInfo.type === 'binary' ? `<img t-if="doc.${fieldPath}" src="/web/static/src/img/mimetypes/image.svg" t-att-src="doc.env['ir.actions.report'].get_safe_image_data_uri(doc.${fieldPath})" style="max-width: 100%; width: 200px; height: auto; object-fit: contain;" title="${fieldInfo.string}" />` : `<span t-field="doc.${fieldPath}" title="${fieldInfo.string}">${fieldPath}</span>`}
                        </div>`;
                    item.setAttribute('cy-type', 'dynamic');
                    item.style.cursor = 'default';
                    item.style.opacity = '1';

                    // Internal delete handler
                    item.querySelector('.field-delete').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: "Are you sure you want to delete this Field?",
                            confirm: () => item.remove(),
                            cancel: () => { },
                        });
                        // if (confirm("Delete this field?")) item.remove();
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
                                <div class="table-handle ri-drag-move-line" title="Drag to move"></div>
                                <div class="table-delete ri-delete-bin-line" title="Delete Table"></div>
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

                if (type === 'sign') {
                    const signId = 'sign_' + Math.random().toString(36).slice(2, 10);
                    const defaultCfg = {
                        role: 'customer',
                        label: 'Authorized Signature',
                        required: true,
                        show_date: false,
                        show_name: false,
                        width: 200,
                        height: 100,
                        alignment: 'left',
                    };
                    item.className = 'sign-wrapper c_new';
                    item.setAttribute('cy-type', 'sign');
                    item.setAttribute('data-sign-id', signId);
                    item.setAttribute('data-sign-config', JSON.stringify(defaultCfg));
                    item.dataset.role = defaultCfg.role;
                    item.style.width = defaultCfg.width + 'px';
                    item.style.height = defaultCfg.height + 'px';
                    item.style.opacity = '1';
                    item.style.cursor = 'default';
                    item.style.textAlign = defaultCfg.alignment;

                    item.innerHTML = `
                        <div class="sign-toolbar" contenteditable="false">
                            <span class="sign-drag-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="sign-delete-btn ri-delete-bin-line" title="Delete Signature"></span>
                        </div>
                        <div class="sign-content-wrapper" style="pointer-events: none; border: 2px dashed #ccc; width: 100%; height: 100%; padding: 10px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; position: relative;">
                            <div class="sign-watermark" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.1; font-size: 40px; color: #9ea700;"><i class="fa fa-pencil"></i></div>
                            <div class="sign-role-badge" style="position: absolute; top: -10px; right: 10px; background: #9ea700; color: white; padding: 2px 6px; font-size: 10px; border-radius: 4px; text-transform: uppercase;">${defaultCfg.role}</div>
                            <div class="sign-empty-line" style="border-bottom: 1px solid #333; width: 80%; margin: 10px auto;"></div>
                            <p class="sign-label" style="font-weight: bold; font-size: 14px; margin: 0;">${defaultCfg.label}</p>
                        </div>
                        <div class="sign-resize-handles" contenteditable="false">
                            <div class="sign-resize-handle" data-dir="se"></div>
                        </div>
                    `;

                    item.querySelector('.sign-delete-btn').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: 'Delete this Signature?',
                            confirm: () => {
                                if (self.state.showSignProps && self._selectedSignEl === item) {
                                    self.closeSignProps();
                                }
                                item.remove();
                                self._updateHasSign();
                            },
                            cancel: () => { },
                        });
                    };

                    self._setupSignResizeHandles(item);
                    self._updateHasSign();
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
        if (!this._reportFrame) return;

        // Destroy existing zone sortables (keep panel sortable alive – index 0)
        const [panelSortable, ...zoneSortables] = this._sortableInstances;
        zoneSortables.forEach(s => { try { s.destroy(); } catch (_) { } });
        this._sortableInstances = panelSortable ? [panelSortable] : [];

        // Recreate for every cy-template zone (main canvas zones)
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
        const action = {
            name: 'Reports',
            type: 'ir.actions.act_window',
            res_model: 'ir.actions.report',
            target: 'current',
            views: [[false, 'kanban']],
            context: {
                default_model: this._resModel,
                search_default_model: this._resModel,
            }
        };

        if (this._resModel) {
            action.domain = [['model', '=', this._resModel]];
        }

        component.action.doAction(action);
    }

    async save_changes(component) {
        if (component.state.hasOverflow) {
            component.notification.add(
                "Cannot save: content exceeds the page boundary. " +
                "Remove or resize elements above the red line first.",
                { type: "danger", sticky: true }
            );
            // this.action.doAction("studio_reload");
            return;
        }
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

            // SAFETY: If a c_new element landed inside a zone, we should move it to the
            // nearest .oe_structure anchor. This is especially critical for zones
            // containing tables or loops, where the browser mangles the DOM structure.
            // By moving new nodes to safe anchors, we ensure the parent zone remains
            // structurally identical to the original, preventing a position="replace"
            // that would corrupt QWeb directive chains.
            const frameEl = component.reportFrameRef.el;
            frameEl.querySelectorAll('[cy-template]').forEach(zone => {
                const newNodes = Array.from(zone.children).filter(
                    c => !c.hasAttribute('cy-xpath') && c.classList.contains('c_new')
                );
                if (!newNodes.length) return;

                // Find a safe anchor (.oe_structure) in this zone or its parents
                let anchor = zone.querySelector('.oe_structure[cy-xpath]') || zone.querySelector('.oe_structure');

                // If this zone IS an oe_structure, or we found one, we are good.
                if (zone.classList.contains('oe_structure') || anchor) {
                    if (anchor && anchor !== zone) {
                        newNodes.forEach(node => anchor.appendChild(node));
                    }
                } else {
                    // If no anchor in zone, move to the global page anchor if possible
                    const pageAnchor = frameEl.querySelector('.page > .oe_structure') || frameEl.querySelector('.oe_structure');
                    if (pageAnchor && pageAnchor !== zone) {
                        newNodes.forEach(node => pageAnchor.appendChild(node));
                    }
                }
            });

            const editedHTML = component.reportFrameRef.el.innerHTML;


            console.log('[Cyllo Studio] Serializing HTML...', editedHTML.length, 'bytes');
            const parser = new DOMParser();
            const editedDoc = parser.parseFromString(editedHTML, 'text/html');
            const originalDoc = parser.parseFromString(component._loadedArch || '', 'text/html');

            // Normalize editedDoc by unwrapping UI shells to match originalDoc structure
            component._cleanStudioAttrs(editedDoc.body, true);

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
        let allChanges = []
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

            // A zone is a "loop container" if any of its children (direct or nested)
            // in the ORIGINAL document are QWeb structural nodes (t-foreach, t-set,
            // t-if, t-elif, t-else, t-call). These structural nodes create loop
            // variable scope — replacing the container in full would lose that context
            // and cause "NoneType is not subscriptable" in QWeb at render time.
            const hasStructuralNodes = (node) => {
                if (!node || !node.hasAttribute) return false;
                const attrs = ['t-foreach', 't-set', 't-if', 't-elif', 't-else', 't-call', 't-as', 't-value', 't-field', 't-esc', 't-out'];

                // Check the node itself first
                if (attrs.some(a => node.hasAttribute(a))) return true;
                const tag = (node.tagName || '').toLowerCase();
                if (tag === 't' || tag === 'cy-qweb-t') return true;

                // Check all descendants using a broad selector that catches both t and cy-qweb-t
                const selector = attrs.map(a => `t[${a}], cy-qweb-t[${a}]`).join(',') + ',t,cy-qweb-t';
                try {
                    return !!(node.querySelector && node.querySelector(selector));
                } catch (e) {
                    // Fallback for extremely large zones if querySelector fails
                    return Array.from(node.getElementsByTagName('*')).some(el => {
                        const etag = (el.tagName || '').toLowerCase();
                        if (etag === 't' || etag === 'cy-qweb-t') return true;
                        return attrs.some(a => el.hasAttribute(a));
                    });
                }
            };


            // Check whether ANY direct child of this zone (in original) contains a
            // t-if/t-elif/t-else chain. If a sibling carries t-elif or t-else, then
            // replacing the zone with position="replace" would orphan those directives
            // from their t-if, causing the QWeb SyntaxError.
            const hasTIfElIfChainInChildren = (node) => {
                return Array.from(node.children).some(c => {
                    const tag = (c.tagName || '').toLowerCase();
                    if (tag !== 'cy-qweb-t' && tag !== 't') return false;
                    if (c.hasAttribute('t-if')) return true;
                    if (c.hasAttribute('t-elif') || c.hasAttribute('t-else')) return true;
                    return Array.from(c.children).some(gc => {
                        const gtag = (gc.tagName || '').toLowerCase();
                        if (gtag !== 'cy-qweb-t' && gtag !== 't') return false;
                        return gc.hasAttribute('t-if') || gc.hasAttribute('t-elif') || gc.hasAttribute('t-else');
                    });
                });
            };

            // Also block replace if the zone contains ANY table. Tables are dangerous
            // because browser HTML parser hoists QWeb directives out of tbody,
            // breaking t-if/t-elif sibling chains and loop scopes.
            const containsTable = (node) => {
                return !!(node.querySelector && node.querySelector('table'));
            };

            const textChanged = text(original) !== text(el);
            const innerChanged = inner(original) !== inner(el);
            const rawStructChanged = cyXpathChildren(original) !== cyXpathChildren(el);

            const structChanged = rawStructChanged
                && !hasStructuralNodes(original)
                && !hasTIfElIfChainInChildren(original)
                && !containsTable(original)
                && !original.classList.contains('page')
                && !original.hasAttribute('name'); // Zones with names are often anchors in Odoo layouts

            if (textChanged || innerChanged || structChanged) {
                console.log(`[Cyllo Studio] Change detected in ${xpath}: text=${textChanged}, inner=${innerChanged}, struct=${structChanged} (rawStruct=${rawStructChanged})`);
                if (structChanged) {
                    console.log(`[Cyllo Studio]   - Struct check for ${xpath}: hasStructural=${hasStructuralNodes(original)}, hasChain=${hasTIfElIfChainInChildren(original)}, hasTable=${containsTable(original)}`);
                }
                allChanges.push({ el, xpath, template, structChanged });
            }

            // ── Detect attribute-only changes on cy-xpath children ──
            // When d-print-none / t-if is toggled via the editor wrappers,
            // _cleanStudioAttrs pushes those attributes down to the underlying cy-xpath children.
            // The inner/text comparison misses them because those nodes are excluded from diffs.
            // We generate separate change entries directly targeting the child xpath.
            Array.from(el.children)
                .filter(c => c.hasAttribute('cy-xpath') && !c.classList.contains('c_new'))
                .forEach(editedChild => {
                    const childXpath = editedChild.getAttribute('cy-xpath');
                    const childTemplate = editedChild.getAttribute('cy-template') || template;
                    const originalChild = originalDoc.querySelector(
                        `[cy-template="${childTemplate}"][cy-xpath="${childXpath}"]`
                    ) || originalDoc.querySelector(`[cy-xpath="${childXpath}"]`);
                    if (!originalChild) return;

                    const editedHasHidden = editedChild.classList.contains('d-print-none');
                    const originalHasHidden = originalChild.classList.contains('d-print-none');
                    const editedTif = editedChild.getAttribute('t-if');
                    const originalTif = originalChild.getAttribute('t-if');

                    const attrChanged = (editedHasHidden !== originalHasHidden) || (editedTif !== originalTif);
                    if (attrChanged) {
                        console.log(`[Cyllo Studio] Attribute change on child ${childXpath}: hidden=${originalHasHidden}->${editedHasHidden}, t-if=${originalTif}->${editedTif}`);
                        allChanges.push({
                            el: editedChild,
                            xpath: childXpath,
                            template: childTemplate,
                            structChanged: false,
                            attrOnly: true,
                            isHidden: editedHasHidden,
                            tif: editedTif,
                        });
                    }
                });
        });


        return allChanges.filter(change =>
            !allChanges.some(p => p !== change && change.xpath.startsWith(p.xpath + '/'))
        );
    }


    _cleanStudioAttrs(node, keepStudioAttrs = false) {
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

                        el.classList.add('report-qr');
                    } catch (e) {
                        console.error("[Cyllo Studio] QR Serialization failed", e);
                    }
                }
                el.classList.remove('s_qr_block', 'c_new', 'selected');
            }

            if (!keepStudioAttrs) {
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
            }

            const handles = el.querySelectorAll ? Array.from(el.querySelectorAll('.table-handle, .box-handle, .box-toolbar, .box-resize-handles, .box-resize-handle, .field-handle, .tcm-delete-table, .table-toolbar, .text-handle, .resize-handle, .field-delete, .table-handle-container, .table-delete, .field-handle-container, .qr-handle-container')) : [];
            handles.forEach(h => h.remove());

            // Unwrap wrappers
            if (el.classList && el.classList.contains('table-wrapper')) {
                if (el.parentNode) {
                    const children = Array.from(el.childNodes);
                    const promotedChildren = [];

                    const isHidden = el.classList.contains('cy-block-hidden');
                    const isInactive = el.getAttribute('t-if') === 'False';
                    const isPbBefore = el.classList.contains('page-break-before');
                    const isPbAfter = el.classList.contains('page-break-after');

                    children.forEach(child => {
                        // Skip whitespace nodes introduced by the wrapper's HTML template
                        if (child.nodeType === 3 && !child.textContent.trim()) return;

                        if (child.tagName === 'TABLE' || (child.classList && child.classList.contains('table'))) {
                            if (isHidden) child.classList.add('d-print-none');
                            if (isInactive) child.setAttribute('t-if', 'False');
                            if (isPbBefore) child.classList.add('page-break-before');
                            if (isPbAfter) child.classList.add('page-break-after');
                        }

                        promotedChildren.push(child);
                        el.parentNode.insertBefore(child, el);
                    });
                    el.remove();
                    promotedChildren.forEach(child => clean(child));
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

                const isHidden = el.classList.contains('cy-block-hidden');
                const isInactive = el.getAttribute('t-if') === 'False';
                const isPbBefore = el.classList.contains('page-break-before');
                const isPbAfter = el.classList.contains('page-break-after');

                if (isHidden) section.classList.add('d-print-none');
                if (isInactive) section.setAttribute('t-if', 'False');
                if (isPbBefore) section.classList.add('page-break-before');
                if (isPbAfter) section.classList.add('page-break-after');

                if (el.hasAttribute('cy-xpath')) section.setAttribute('cy-xpath', el.getAttribute('cy-xpath'));
                if (el.hasAttribute('cy-template')) section.setAttribute('cy-template', el.getAttribute('cy-template'));
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

            // ── Sign Node Serialization ──
            if (el.classList && el.classList.contains('sign-wrapper')) {
                let cfg = {};
                try { cfg = JSON.parse(el.dataset.signConfig || '{}'); } catch (ex) { }

                const role = cfg.role || 'customer';
                const label = cfg.label || 'Authorized Signature';
                const alignment = cfg.alignment || 'left';
                const width = cfg.width || 200;

                const section = document.createElement('div');
                section.className = 'o_sign_placeholder';

                const isHidden = el.classList.contains('cy-block-hidden');
                const isInactive = el.getAttribute('t-if') === 'False';
                const isPbBefore = el.classList.contains('page-break-before');
                const isPbAfter = el.classList.contains('page-break-after');

                if (isHidden) section.classList.add('d-print-none');
                if (isInactive) section.setAttribute('t-if', 'False');
                if (isPbBefore) section.classList.add('page-break-before');
                if (isPbAfter) section.classList.add('page-break-after');
                if (el.hasAttribute('cy-xpath')) section.setAttribute('cy-xpath', el.getAttribute('cy-xpath'));
                if (el.hasAttribute('cy-template')) section.setAttribute('cy-template', el.getAttribute('cy-template'));
                section.setAttribute('data-role', role);

                // Style: width + alignment, clear box-model for PDF
                let styleStr = `display:inline-block; width:${width}px; text-align:${alignment}; vertical-align:top; padding:4px 0;`;
                section.setAttribute('style', styleStr);

                // Invisible backend-detection anchor ([[SIGN:role]] in 2pt white text)
                const anchor = document.createElement('span');
                anchor.setAttribute('style', 'color:white;font-size:2pt;line-height:1px;display:block;overflow:hidden;height:1px;');
                anchor.textContent = `[[SIGN:${role}]]`;
                section.appendChild(anchor);

                // Signature line (underscores) — clean static line, no t-if/t-else
                const sigLine = document.createElement('div');
                sigLine.setAttribute('style', 'border-bottom:1px solid #333;width:80%;margin:8px auto 4px;min-height:40px;');
                section.appendChild(sigLine);

                // Label
                const labelP = document.createElement('p');
                labelP.setAttribute('style', 'font-weight:bold;font-size:11pt;margin:2px 0 0;');
                labelP.textContent = label;
                section.appendChild(labelP);

                if (cfg.show_date) {
                    const dateP = document.createElement('p');
                    dateP.setAttribute('style', 'font-size:9pt;margin:2px 0 0;color:#555;');
                    dateP.textContent = 'Date: _______________';
                    section.appendChild(dateP);
                }

                if (cfg.show_name) {
                    const nameP = document.createElement('p');
                    nameP.setAttribute('style', 'font-size:9pt;margin:2px 0 0;color:#555;');
                    nameP.textContent = 'Name: _______________';
                    section.appendChild(nameP);
                }

                if (el.parentNode) {
                    el.parentNode.replaceChild(section, el);
                    Array.from(section.children).forEach(child => clean(child));
                }
                return;
            }

            // Legacy box-wrapper (old format) compat
            if (el.classList && el.classList.contains('box-wrapper')) {
                if (el.parentNode) {
                    const children = Array.from(el.childNodes);
                    children.forEach(child => el.parentNode.insertBefore(child, el));
                    el.remove();
                    children.forEach(child => clean(child));
                    return;
                }
            }
            if (el.classList && (el.classList.contains('dynamic-field-wrapper') || el.classList.contains('field-block') || el.classList.contains('field-container'))) {
                if (el.parentNode) {
                    const children = Array.from(el.childNodes);
                    const promotedChildren = [];

                    const isHidden = el.classList.contains('cy-block-hidden');
                    const isInactive = el.getAttribute('t-if') === 'False';
                    const isPbBefore = el.classList.contains('page-break-before');
                    const isPbAfter = el.classList.contains('page-break-after');

                    children.forEach(child => {
                        // Skip whitespace nodes introduced by the wrapper's HTML template
                        if (child.nodeType === 3 && !child.textContent.trim()) return;

                        if (child.classList && child.classList.contains('field-container')) {
                            child.classList.remove('d-inline-flex', 'gap-1');
                        }

                        if (child.nodeType === 1 && !child.classList.contains('field-handle-container')) {
                            if (isHidden) child.classList.add('d-print-none');
                            if (isInactive) child.setAttribute('t-if', 'False');
                            if (isPbBefore) child.classList.add('page-break-before');
                            if (isPbAfter) child.classList.add('page-break-after');
                        }

                        promotedChildren.push(child);
                        el.parentNode.insertBefore(child, el);
                    });
                    el.remove();
                    promotedChildren.forEach(child => clean(child));
                    return;
                }
            }

            // Cleanup residual classes; convert editor-side hidden marker to real d-print-none
            if (!keepStudioAttrs && el.classList) {
                // cy-block-hidden is the editor-side marker; save as d-print-none in XML
                if (el.classList.contains('cy-block-hidden')) {
                    el.classList.add('d-print-none');
                    el.classList.remove('cy-block-hidden');
                }
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
            if (section.hasAttribute('cy-xpath')) wrapper.setAttribute('cy-xpath', section.getAttribute('cy-xpath'));
            if (section.hasAttribute('cy-template')) wrapper.setAttribute('cy-template', section.getAttribute('cy-template'));
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

        // ── Enrich existing report-qr from previous edits ──
        container.querySelectorAll('div.report-qr:not(.s_qr_block)').forEach(qrDiv => {
            let qrConfig = null;
            try {
                if (qrDiv.dataset.qrConfig) {
                    qrConfig = JSON.parse(qrDiv.dataset.qrConfig);
                }
            } catch (e) { }

            if (qrConfig) {
                this.insertQrBlock(qrDiv, qrConfig, 'enrich');
            }
        });

        // ── Enrich existing o_sign_placeholder from previous saves ──
        container.querySelectorAll('div.o_sign_placeholder:not(.sign-wrapper)').forEach(placeholder => {
            if (placeholder.closest('.sign-wrapper')) return;
            const role = placeholder.dataset.role || 'customer';
            // Parse existing cfg from style
            const existingStyle = placeholder.getAttribute('style') || '';
            const widthMatch = existingStyle.match(/width:\s*(\d+)px/);
            const alignMatch = existingStyle.match(/text-align:\s*(\w+)/);
            // Look for label in existing children
            const labelEl = placeholder.querySelector('p');
            const labelText = labelEl ? labelEl.textContent.trim() : 'Authorized Signature';

            const signId = 'sign_' + Math.random().toString(36).slice(2, 10);
            const cfg = {
                role,
                label: labelText,
                required: true,
                show_date: false,
                show_name: false,
                width: widthMatch ? parseInt(widthMatch[1]) : 200,
                height: 100,
                alignment: alignMatch ? alignMatch[1] : 'left',
            };

            const wrapper = document.createElement('div');
            wrapper.className = 'sign-wrapper';
            wrapper.setAttribute('cy-type', 'sign');
            if (placeholder.hasAttribute('cy-xpath')) wrapper.setAttribute('cy-xpath', placeholder.getAttribute('cy-xpath'));
            if (placeholder.hasAttribute('cy-template')) wrapper.setAttribute('cy-template', placeholder.getAttribute('cy-template'));
            wrapper.setAttribute('data-sign-id', signId);
            wrapper.setAttribute('data-sign-config', JSON.stringify(cfg));
            wrapper.dataset.role = role;
            wrapper.style.width = cfg.width + 'px';
            wrapper.style.height = cfg.height + 'px';
            wrapper.style.cursor = 'default';
            wrapper.style.textAlign = cfg.alignment;

            wrapper.innerHTML = `
                <div class="sign-toolbar" contenteditable="false">
                    <span class="sign-drag-handle ri-drag-move-line" title="Drag to move"></span>
                    <span class="sign-settings-btn ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                    <span class="sign-delete-btn ri-delete-bin-line" title="Delete Signature"></span>
                </div>
                <div class="sign-content-wrapper" style="pointer-events: none; border: 2px dashed #ccc; width: 100%; height: 100%; padding: 10px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; position: relative;">
                    <div class="sign-watermark" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.1; font-size: 40px; color: #9ea700;"><i class="fa fa-pencil"></i></div>
                    <div class="sign-role-badge" style="position: absolute; top: -10px; right: 10px; background: #9ea700; color: white; padding: 2px 6px; font-size: 10px; border-radius: 4px; text-transform: uppercase;">${role}</div>
                    <div class="sign-empty-line" style="border-bottom: 1px solid #333; width: 80%; margin: 10px auto;"></div>
                    <p class="sign-label" style="font-weight: bold; font-size: 14px; margin: 0;">${labelText}</p>
                </div>
                <div class="sign-resize-handles" contenteditable="false">
                    <div class="sign-resize-handle" data-dir="se"></div>
                </div>
            `;

            wrapper.querySelector('.sign-delete-btn').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: 'Delete this Signature?',
                    confirm: () => {
                        if (this.state.showSignProps && this._selectedSignEl === wrapper) {
                            this.closeSignProps();
                        }
                        wrapper.remove();
                        this._updateHasSign();
                    },
                    cancel: () => { },
                });
            };

            placeholder.parentNode.insertBefore(wrapper, placeholder);
            placeholder.remove();
            this._setupSignResizeHandles(wrapper);
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

            // Re-hydrate visibility state from the saved table onto the wrapper
            const tblHidden = targetNode.classList.contains('d-print-none');
            const tblInactive = targetNode.getAttribute('t-if') === 'False';
            const tblPbBefore = targetNode.classList.contains('page-break-before');
            const tblPbAfter = targetNode.classList.contains('page-break-after');
            if (tblHidden) { wrapper.classList.add('cy-block-hidden'); targetNode.classList.remove('d-print-none'); }
            if (tblInactive) { wrapper.setAttribute('t-if', 'False'); }
            if (tblPbBefore) { wrapper.classList.add('page-break-before'); targetNode.classList.remove('page-break-before'); }
            if (tblPbAfter) { wrapper.classList.add('page-break-after'); targetNode.classList.remove('page-break-after'); }

            wrapper.innerHTML = `
                <div class="table-handle-container" contenteditable="false">
                    <div class="table-handle ri-drag-move-line" title="Drag to move"></div>
                    <div class="table-settings ri-settings-3-line" title="Settings"></div>
                    <div class="table-delete ri-delete-bin-line" title="Delete Table"></div>
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

            // Re-hydrate visibility from saved element
            const fldHidden = targetNode.classList.contains('d-print-none');
            const fldInactive = targetNode.getAttribute('t-if') === 'False';
            if (fldHidden) { wrapper.classList.add('cy-block-hidden'); targetNode.classList.remove('d-print-none'); }
            if (fldInactive) { wrapper.setAttribute('t-if', 'False'); }

            wrapper.innerHTML = `
                <div class="field-handle-container" contenteditable="false">
                    <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                    <span class="field-settings ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                    <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                </div>
                <div class="field-container"></div>
            `;
            targetNode.parentNode.insertBefore(wrapper, targetNode);
            wrapper.querySelector('.field-container').appendChild(targetNode);
            wrapper.querySelector('.field-delete').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this field?",
                    confirm: () => wrapper.remove(),
                    cancel: () => { },
                });
                // if (confirm("Delete this field?")) wrapper.remove();
            };
        });

        const fieldContainers = container.querySelectorAll('.field-container:not(.field-block .field-container)');
        fieldContainers.forEach(fc => {
            if (fc.closest('.field-block') || fc.closest('table')) return;
            let targetNode = fc;
            while (targetNode.parentElement && this._isStructuralNode(targetNode.parentElement) &&
                targetNode.parentElement.children.length === 1 &&
                !targetNode.parentElement.classList.contains('page')) {
                targetNode = targetNode.parentElement;
            }
            const wrapper = document.createElement('div');
            wrapper.className = 'field-block dynamic-field-wrapper';

            // Re-hydrate visibility from saved fieldContainer
            const fcHidden = targetNode.classList.contains('d-print-none');
            const fcInactive = targetNode.getAttribute('t-if') === 'False';
            if (fcHidden) { wrapper.classList.add('cy-block-hidden'); targetNode.classList.remove('d-print-none'); }
            if (fcInactive) { wrapper.setAttribute('t-if', 'False'); }

            wrapper.innerHTML = `
                <div class="field-handle-container" contenteditable="false">
                    <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                    <span class="field-settings ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                    <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                </div>
            `;
            targetNode.parentNode.insertBefore(wrapper, targetNode);
            wrapper.appendChild(targetNode);
            wrapper.querySelector('.field-delete').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this field?",
                    confirm: () => wrapper.remove(),
                    cancel: () => { },
                });
                // if (confirm("Delete this field?")) wrapper.remove();
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

    _buildNewNodesXpath(change, newNodes) {
        if (!newNodes || !newNodes.length) return "";
        const children = Array.from(change.el.children);
        let xpathBlock = "";
        let currentGroup = [];

        const processGroup = (group) => {
            if (!group.length) return;
            let groupContent = "";
            group.forEach(node => {
                const cloned = node.cloneNode(true);
                const cleaned = this._cleanStudioAttrs(cloned);
                let content = new XMLSerializer().serializeToString(cleaned).replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                groupContent += content;
            });

            const firstNodeIndex = children.indexOf(group[0]);
            const lastNodeIndex = children.indexOf(group[group.length - 1]);

            // Find next sibling with cy-xpath
            let nextSibling = null;
            for (let i = lastNodeIndex + 1; i < children.length; i++) {
                if (children[i].hasAttribute('cy-xpath') && !children[i].classList.contains('c_new')) {
                    nextSibling = children[i];
                    break;
                }
            }

            if (nextSibling) {
                xpathBlock += `<xpath expr="${nextSibling.getAttribute('cy-xpath')}" position="before">${groupContent}</xpath>`;
                return;
            }

            // Find prev sibling with cy-xpath
            let prevSibling = null;
            for (let i = firstNodeIndex - 1; i >= 0; i--) {
                if (children[i].hasAttribute('cy-xpath') && !children[i].classList.contains('c_new')) {
                    prevSibling = children[i];
                    break;
                }
            }

            if (prevSibling) {
                xpathBlock += `<xpath expr="${prevSibling.getAttribute('cy-xpath')}" position="after">${groupContent}</xpath>`;
                return;
            }

            // Fallback to parent inside
            xpathBlock += `<xpath expr="${change.xpath}" position="inside">${groupContent}</xpath>`;
        };

        children.forEach(child => {
            if (child.classList.contains('c_new') && !child.hasAttribute('cy-xpath')) {
                currentGroup.push(child);
            } else {
                processGroup(currentGroup);
                currentGroup = [];
            }
        });
        processGroup(currentGroup);
        return xpathBlock;
    }

    buildInheritanceXML(changes) {
        let new_inherits = [];
        for (const [key, items] of Object.entries(groupBy(changes, 'template'))) {
            let xpathBlock = "";
            items.forEach(change => {
                const newNodes = Array.from(change.el.children)
                    .filter(child => !child.hasAttribute('cy-xpath') && child.classList.contains('c_new'));

                if (change.structChanged) {
                    // Secondary guard: never do a full position="replace" on a zone that still has
                    // QWeb structural (t-foreach / t-set / t-if / t-elif / t-else)
                    // descendants in the live DOM.
                    const structuralAttrs = [
                        't-foreach', 't-set', 't-if', 't-elif', 't-else', 't-call', 't-as', 't-value'
                    ];
                    const hasStructuralDescendant = structuralAttrs.some(attr =>
                        change.el.querySelector(`cy-qweb-t[${attr}], t[${attr}]`)
                    );

                    // Extra check: if ANY direct child of this zone is a t-if/t-elif/
                    // t-else node, never replace the zone — the sibling chain would break.
                    const hasConditionalChainChild = Array.from(change.el.children).some(c => {
                        const tag = (c.tagName || '').toLowerCase();
                        if (tag !== 'cy-qweb-t' && tag !== 't') return false;
                        return c.hasAttribute('t-if') || c.hasAttribute('t-elif') || c.hasAttribute('t-else');
                    });

                    // CRITICAL: If zone contains a table with QWeb directives, the browser HTML
                    // parser hoists <t t-foreach/t-if> out of <tbody>, breaking the t-if/t-elif
                    // sibling chain. A position="replace" on such a zone produces invalid QWeb.
                    // Always fall back to position="inside" for c_new nodes in this case.
                    const hasQwebTable = !!(change.el.querySelector && change.el.querySelector(
                        'table t[t-foreach], table t[t-if], table t[t-elif], ' +
                        'table cy-qweb-t[t-foreach], table cy-qweb-t[t-if], table cy-qweb-t[t-elif]'
                    ));

                    if (hasStructuralDescendant || hasConditionalChainChild || hasQwebTable) {
                        // Fall back to saving only genuinely new user-added nodes with precise sibling positioning
                        xpathBlock += this._buildNewNodesXpath(change, newNodes);
                        return;
                    }

                    const clonedZone = change.el.cloneNode(true);
                    const cleaned = this._cleanStudioAttrs(clonedZone);
                    let content = new XMLSerializer().serializeToString(cleaned).replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                    xpathBlock += `<xpath expr="${change.xpath}" position="replace">${content}</xpath>`;
                    return;
                }


                if (newNodes.length) {
                    xpathBlock += this._buildNewNodesXpath(change, newNodes);
                    return;
                }

                // ── Attribute-only change (visibility/t-if on existing cy-xpath element) ──
                if (change.attrOnly) {
                    // change.isHidden = cy-block-hidden was on wrapper (maps to d-print-none in saved XML)
                    // change.tif = t-if value on the wrapper
                    if (change.isHidden) {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="class" add="d-print-none" separator=" "/></xpath>`;
                    } else {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="class" remove="d-print-none" separator=" "/></xpath>`;
                    }
                    if (change.tif === 'False') {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="t-if">False</attribute></xpath>`;
                    } else {
                        // Clear t-if if previously set to False
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="t-if"/></xpath>`;
                    }
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

    // ─────────────────────────────────────────────────────────────────────────
    // Overflow Guard – Page Boundary Indicator
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Inject (or move) the red page-boundary line inside the paper container
     * and show/hide the sticky overflow warning based on whether content
     * exceeds the boundary.
     *
     * The boundary is calculated from the current paper format height minus
     * the top padding (20mm default), converted to pixels via the container's
     * own pixel height / mm ratio so it is always accurate regardless of zoom.
     */

    _updateOverflowGuard() {
        if (this.state.previewMode) return;

        const container = this.reportFrameRef.el?.closest('.cyllo-studio-report-container');
        const editableArea = this.reportFrameRef.el;
        if (!container || !editableArea) return;

        // ── 1. Calculate boundary position in px ────────────────────────────
        const fmt = this.currentPaperFormat;
        const pageHeightMm = fmt ? fmt.page_height : 297;

        // The container is sized in mm via inline style; measure its rendered height
        // to derive the px-per-mm ratio reliably (handles any zoom/dpi).
        const containerRect = container.getBoundingClientRect();
        const containerHeightPx = containerRect.height;

        // Guard: container must have been laid out already
        if (containerHeightPx < 10) return;

        // Ratio: px per mm inside this container element
        const pxPerMm = containerHeightPx / pageHeightMm;

        // Top padding of the editable area (20mm as set in the template inline style)
        const PADDING_MM = 20;
        const paddingPx = PADDING_MM * pxPerMm;

        // Usable content height in px (page height minus top+bottom padding)
        const contentHeightPx = (pageHeightMm - PADDING_MM * 2) * pxPerMm;

        // Boundary Y measured from the TOP of the container element
        const boundaryFromContainerTopPx = paddingPx + contentHeightPx;

        // ── 2. Create / update the boundary line DOM element ─────────────────
        let line = container.querySelector('.cy-page-overflow-line');
        if (!line) {
            line = document.createElement('div');
            line.className = 'cy-page-overflow-line';
            // Insert at the beginning of the container so it sits behind content
            container.insertBefore(line, container.firstChild);
        }
        line.style.top = `${boundaryFromContainerTopPx}px`;

        // ── 3. Determine if any content crosses the boundary ─────────────────
        const editableAreaRect = editableArea.getBoundingClientRect();
        const boundaryAbsoluteY = containerRect.top + boundaryFromContainerTopPx;

        let overflowing = false;
        const allNodes = editableArea.querySelectorAll(
            '[cy-template], table, .table-wrapper, .field-block, .text-node, p, h1, h2, h3, h4, h5, h6, div[cy-xpath]'
        );

        allNodes.forEach(node => {
            const rect = node.getBoundingClientRect();
            const crossesBoundary = rect.bottom > boundaryAbsoluteY + 2; // 2px tolerance
            if (crossesBoundary) {
                node.classList.add('cy-overflowing');
                overflowing = true;
            } else {
                node.classList.remove('cy-overflowing');
            }
        });

        // ── 4. Show / hide the sticky warning banner ──────────────────────────
        const mainArea = container.closest('.flex-grow-1.overflow-auto') ||
            container.parentElement;
        if (!mainArea) return;

        let warning = mainArea.querySelector('.cy-overflow-warning');
        if (!warning) {
            warning = document.createElement('div');
            warning.className = 'cy-overflow-warning hidden';
            warning.innerHTML = `
                <span class="cy-overflow-warning-icon">
                    <i class="fa fa-exclamation-triangle"></i>
                </span>
                <div class="cy-overflow-warning-text">
                    Content exceeds the page boundary
                    <div class="cy-overflow-warning-sub">
                        Some elements extend beyond the printable area and may be cut off in the PDF.
                        Reduce content or switch to a larger paper format.
                    </div>
                </div>`;
            // Insert the warning just after the paper container
            container.insertAdjacentElement('afterend', warning);
        }
        this.state.hasOverflow = overflowing;
        if (overflowing) {
            warning.classList.remove('hidden');
        } else {
            warning.classList.add('hidden');
        }
    }

    /**
     * Attach a MutationObserver to the report frame so the overflow guard
     * re-evaluates automatically whenever content changes.
     * Called once from _setupReportFrame.
     */
    _startOverflowGuardObserver() {
        if (this._overflowObserver) {
            this._overflowObserver.disconnect();
        }

        const editableArea = this.reportFrameRef.el;
        if (!editableArea) return;

        // Debounce to avoid flooding on heavy DOM mutations
        let debounceTimer = null;
        const check = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => this._updateOverflowGuard(), 150);
        };

        this._overflowObserver = new MutationObserver(check);
        this._overflowObserver.observe(editableArea, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ['style', 'class'],
        });

        // Also re-check whenever the window is resized (zoom change, etc.)
        if (this._overflowResizeHandler) {
            window.removeEventListener('resize', this._overflowResizeHandler);
        }
        this._overflowResizeHandler = check;
        window.addEventListener('resize', this._overflowResizeHandler);

        // Initial check after the frame is painted
        requestAnimationFrame(() => this._updateOverflowGuard());
    }
}

// ── Apply focused mixins ─────────────────────────────────────────────────────
// QR wizard and Box section methods live in dedicated files to keep
// studio_report.js under a manageable size.
Object.assign(EditReport.prototype, QrMixin, BoxMixin, SignMixin);

EditReport.template = "custom_report.edit_report";
registry.category("actions").add("edit_report", EditReport);
