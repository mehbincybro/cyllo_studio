/** @odoo-module **/
import {
    NavBar
} from "@web/webclient/navbar/navbar";
import {
    useService,
    useBus
} from "@web/core/utils/hooks";
import {
    ViewSelectionDropDown
} from "@cyllo_studio/js/navbar/view_selection_dropdown/view_selection_dropdown";
import {
    useState,
    useRef,
    onMounted,onPatched,onWillUnmount
} from "@odoo/owl";
import {
    FirstPage
} from '@cyllo_studio/js/new_app/new_app_templates';
import { RemoveSessions } from '@cyllo_studio/js/root/studio_utils';

/**
 * CylloNavBar extends the standard Odoo NavBar to integrate
 * Cyllo Studio functionality, including undo/redo support,
 * view switching, and studio-specific UI controls.
 */

export class CylloNavBar extends NavBar {
    static template = "cyllo_studio.CylloNavBar";
    setup() {
        this.orm = useService("orm");
        this.root = useRef("cy_nav_bar");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
        this.menuService = useService("menu")
        this.notification = useService("notification")
        const prevForm = this._readPrevForm();
        this.state = useState({
            studioEditableList: false,
            lightMode: false,
            isStudioEdit: false,
            canUndo: JSON.parse(sessionStorage.getItem('UndoRedo') || '[]').length > 0, //starlin
            canRedo: JSON.parse(sessionStorage.getItem('ReDO') || '[]').length > 0, //starlin
            configOpen: false,
            // x2many drill-down breadcrumb (e.g. "Quotations > Order Lines").
            // Mirrors the studio wrapper's own state, driven by the same bus
            // event — reliable, unlike sessionStorage which RemoveSessions clears.
            bcActive: sessionStorage.getItem('CyX2ManyTriggered') === 'true',
            bcPrev: prevForm?.ModelName || "",
            bcField: prevForm?.FieldName || "",
        });
        useBus(this.env.bus, 'studio_editable_list', (res) => {
            this.state.studioEditableList = res.detail;
            this.props.updateState("edit", false);
        });
        useBus(this.env.bus, 'X2Many-Breadcrumbs', ({ detail }) => {
            this.state.bcPrev = detail.ModelName || "";
            this.state.bcField = detail.FieldName || "";
            this.state.bcActive = true;
        });
        // The navbar isn't reactive to controller swaps, so the model-name label
        // and breadcrumb go stale on menu navigation. UI-UPDATED fires after every
        // action UI change: re-render to refresh currentModelName, and clear the
        // x2many breadcrumb whenever the action itself changes (menu nav). An x2many
        // drill re-sets the breadcrumb via X2Many-Breadcrumbs, which fires after the
        // drill's doAction resolves, so the trail survives.
        useBus(this.env.bus, 'ACTION_MANAGER:UI-UPDATED', () => {
            const actionId = this.action.currentController?.action?.jsId;
            if (actionId && this._lastActionId !== null && this._lastActionId !== actionId) {
                this._clearBreadcrumb();
            }
            if (actionId) {
                this._lastActionId = actionId;
            }
            this.render();
        });
                useBus(this.env.bus, 'PREVIEW_MODE_CHANGED', ({detail}) => {
    this.state.isPreviewMode = detail.isPreviewMode;
    });
        useBus(this.env.bus, "STUDIO_EDIT_BUTTON_HIDE", () => {
            this.props.updateState("editButton", false);
        });

        this.viewChange = this.viewChange.bind(this);
        // The x2many drill-down is an in-app view swap with no history entry,
        // so any browser back/forward (popstate) leaves the drill. Reset the
        // breadcrumb then — it re-appears via the bus event on a fresh drill.
        this._lastActionId = null;
        this._onPopState = () => this._clearBreadcrumb();
        // Close the (click-opened) Configuration dropdown on any outside click.
        this._onDocClick = (ev) => {
            if (!this.state.configOpen) {
                return;
            }
            const btn = this.root.el?.querySelector('.cy-nav-Menu-button');
            if (btn && !btn.contains(ev.target)) {
                this.state.configOpen = false;
            }
        };
        onMounted(() => {
            this.updateUndoRedoState();
            setInterval(() => this.updateUndoRedoState(), 500);
            window.addEventListener('popstate', this._onPopState);
            document.addEventListener('click', this._onDocClick);
        });
        onWillUnmount(() => {
            window.removeEventListener('popstate', this._onPopState);
            document.removeEventListener('click', this._onDocClick);
        });
        onPatched(() => {
            let studioViews = this.root?.el.querySelector('.cy-studio-views');
            if (studioViews) {
                studioViews.style.display = this.state.studioEditableList ? 'none' : 'block';
            }
            if (this.state.configOpen) {
                this.ShowMiscellaneousDrop();
            }
            });
    }

    /**
     * Update undo/redo button states based on sessionStorage.
     * Automatically triggers edit mode if 'cyllo_auto_edit' is set.
     */
    updateUndoRedoState() {
        this.state.canUndo = JSON.parse(sessionStorage.getItem('UndoRedo') || '[]').length > 0;
        this.state.canRedo = JSON.parse(sessionStorage.getItem('ReDO') || '[]').length > 0;
        if (sessionStorage.getItem("cyllo_auto_edit") === "1") {
            this.handleEdit();
            sessionStorage.removeItem("cyllo_auto_edit");
        }
    }

    /**
     * Open the Cyllo Studio app creation dialog.
     */
    createApp() {
        this.dialogService.add(FirstPage, {
            title: 'Cyllo Studio',
        })
    }

        /** Open the Access Rights view for the current model. */
    async AccessRightsClick(){
        this.state.configOpen = false;
        const [modelId, viewId] = await this.orm.call("ir.model", "cyllo_get_studio_action_acl", [this.action.currentController.action.res_model, 'ir.model.access']);
        this.action.doAction({
            name: 'Access Rights',
            type: 'ir.actions.act_window',
            res_model: 'ir.model.access',
            views: [[viewId, 'list']],
            target: 'current',
            context: {
                default_model_id: modelId,
                search_default_model_id: modelId,
            },
        });
    }
    async EmailTemplateClick(){}

    /** Open Record Rules view for the current model. */
    async RecordRuleClick() {
        this.state.configOpen = false;
        const model_id = await this.orm.call("ir.model", "cyllo_get_studio_action_acl", [this.action.currentController.action.res_model, 'ir.rule']);
        this.action.doAction({
            name: 'Record Rules',
            type: 'ir.actions.act_window',
            res_model: 'ir.rule',
            views: [[model_id[1], 'list']],
            context: {
                default_model_id: model_id[0],
                search_default_model_id: model_id[0],
            },
        });
    }

    /** Toggle the Configuration dropdown (click-driven, not hover). */
    toggleConfig(ev) {
        ev.stopPropagation();
        this.state.configOpen = !this.state.configOpen;
    }
    /** Close the Configuration dropdown. */
    closeConfig() {
        this.state.configOpen = false;
    }
    /** Show the miscellaneous menu dropdown aligned properly. */
    ShowMiscellaneousDrop() {
        const menuContainer = this.root.el?.querySelector('.cy-nav-Menu-button');
        const menuCard = this.root.el?.querySelector('.cy-miscellaneous_card');
        if (!menuContainer || !menuCard) return;
        const containerRect = menuContainer.getBoundingClientRect();
        const cardRect = menuCard.getBoundingClientRect();
        const spaceToRight = window.innerWidth - containerRect.right;
        const spaceToLeft = containerRect.left;
        menuCard.classList.remove('menu-right');
        menuCard.style.left = '0';
        menuCard.style.right = 'auto';
        menuCard.style.zIndex = 999;
        if (spaceToRight < cardRect.width) {
            menuCard.style.left = 'auto';
            menuCard.style.right = '0';
            menuCard.classList.add('menu-right');
        }
    }
    /** Open report view for the current model. */
    async ReportClick() {
        this.state.configOpen = false;
        const currentController = this.action.currentController;
        console.log('hiiii',currentController)
        const resModel = currentController.action.res_model;
        if (resModel && resModel !== 'ir.actions.report') {
            sessionStorage.setItem('cy_report_editor_origin', JSON.stringify({
                res_model: resModel,
                view_type: currentController.env?.config?.viewType || 'list',
            }));
        }
        const [modelId, viewId] = await this.orm.call("ir.model", "cyllo_get_studio_action_acl", [resModel, 'ir.actions.report']);
        
        const action = {
            name: 'Reports',
            type: 'ir.actions.act_window',
            res_model: 'ir.actions.report',
            target: 'current',
            views: [[viewId, 'kanban']],
            context: {
                default_model: resModel,
                search_default_model: resModel,
            }
        };

        if (resModel) {
            action.domain = [['model', '=', resModel]];
        }

        this.action.doAction(action);
    }

    /** Toggle light/dark mode for studio UI. */
    handleDarkMode() {
        this.state.lightMode = !this.state.lightMode;
        if (this.state.lightMode) {
            document.body.classList.add("light-studio-mode");
            localStorage.setItem("lightModeStudio", this.state.lightMode);
        } else {
            document.body.classList.remove("light-studio-mode");
            localStorage.removeItem("lightModeStudio");
        }
        this.render();
    }

    /** Activate studio edit mode. */
    async handleEdit() {
        this.state.isStudioEdit = true;
        this.env.bus.trigger('STUDIO_EDIT_STARTED',{
             isStudioEdit : this.state.isStudioEdit
        });
        this.props.updateState("edit", true);
        this.props.updateState("editButton", false);
    }
    get viewSelectionProps() {
        return {
            view: this.props.view,
            viewChange: this.viewChange,
        };
    }
    /** Human-readable name of the model/action currently being edited. */
    get currentModelName() {
        const ctrl = this.action.currentController;
        return ctrl?.action?.name || this.props.viewDetails?.model || "";
    }
    /** Safely parse the persisted x2many parent-form descriptor. */
    _readPrevForm() {
        try {
            return JSON.parse(sessionStorage.getItem('PrevForm') || 'null');
        } catch (_) {
            return null;
        }
    }
    /** Reset the x2many drill-down breadcrumb state. */
    _clearBreadcrumb() {
        this.state.bcActive = false;
        this.state.bcPrev = "";
        this.state.bcField = "";
    }
    /** Navigate back from the x2many breadcrumb (handled by the wrapper). */
    breadcrumbBack(e) {
        e.preventDefault();
        this._clearBreadcrumb();
        this.env.bus.trigger("STUDIO_BREADCRUMB_BACK");
    }
    viewChange(attr, value) {
        // Switching the top-level view (via the view icons) leaves any x2many
        // drill, so the "Parent > Field" breadcrumb must reset.
        this._clearBreadcrumb();
        this.props.updateState("editButton", false);
        this.props.updateState(attr, value);
    }
    /** Close the studio session and reload the page. */
    handleClose() {
        const appId = this.menuService.getCurrentApp().id
        localStorage.setItem("cy_selected_app", appId || false)
        sessionStorage.removeItem("invisible");
        const currentUrl = new URL(window.location.href);
        const currentModel = this.action.currentController?.action?.res_model;
        if (currentModel === 'ir.actions.report') {
            let origin = null;
            try {
                origin = JSON.parse(sessionStorage.getItem('cy_report_editor_origin') || 'null');
            } catch (_) {
                origin = null;
            }
            if (origin?.res_model) {
                const hashParams = new URLSearchParams(currentUrl.hash.replace(/^#/, ""));
                hashParams.set("model", origin.res_model);
                hashParams.set("view_type", origin.view_type || "list");
                hashParams.delete("id");
                hashParams.delete("action");
                currentUrl.hash = hashParams.toString();
            }
            sessionStorage.removeItem('cy_report_editor_origin');
        }
        const studio = currentUrl.searchParams.get("studio");
        if (studio === "1") {
            currentUrl.searchParams.delete("studio");
            history.replaceState(null, "", currentUrl.toString());
        }
        currentUrl.searchParams.set("studio", "");
        window.location.href = currentUrl.toString();
        RemoveSessions()
        setTimeout(() => window.location.reload(), 500);
    }
    async undoChange() {
        const storage = JSON.parse(sessionStorage.getItem('UndoRedo') || '[]');
        if (!storage.length) {
            return; // nothing to undo
        }
        let view_type = this.props.viewDetails?.viewType;
        let view_id = this.props.viewDetails?.viewId;
        const model = this.props.viewDetails?.model;
        const searchViewId = sessionStorage.getItem("searchViewId");
        if (searchViewId) {
            view_type = 'search';
            view_id = searchViewId;
        }
        // Guard: a valid editable view must be open, else the server would try
        // to build a Studio view from an empty model / view id and crash.
        if (!view_id || !view_type || (!model && !searchViewId)) {
            this.notification.add("Open the view you want to undo changes on first.", {
                title: "Nothing to undo here",
                type: "warning",
            });
            return;
        }
        const undoElement = storage[storage.length - 1];
        let xPaths = false;
        const count = (undoElement.match(/<xpath /g) || []).length;
        if (count >= 2) {
            xPaths = true;
        }
        try {
            await this.rpc('cyllo_studio/undo_action', {
                model: model,
                view_type: view_type,
                view_id: view_id,
                xPaths: xPaths,
            });
        } catch (e) {
            this.notification.add("Could not undo the last change.", {
                title: "Undo failed",
                type: "danger",
            });
            return; // keep stacks intact so the action isn't lost
        }
        // Success: move the element from the undo stack onto the redo stack.
        storage.pop();
        sessionStorage.setItem('UndoRedo', JSON.stringify(storage));
        const redoStack = JSON.parse(sessionStorage.getItem('ReDO') || '[]');
        redoStack.push(undoElement);
        sessionStorage.setItem('ReDO', JSON.stringify(redoStack));
        this.action.doAction("studio_reload");
        this.env.bus.trigger('resetProperties');
        window.location.reload();
    }

    async redoChange() {
        const storage = JSON.parse(sessionStorage.getItem('ReDO') || '[]');
        if (!storage.length) {
            return; // nothing to redo
        }
        let view_type = this.props.viewDetails?.viewType;
        let view_id = this.props.viewDetails?.viewId;
        const model = this.props.viewDetails?.model;
        const searchViewId = sessionStorage.getItem("searchViewId");
        if (searchViewId) {
            view_type = 'search';
            view_id = searchViewId;
        }
        // Guard: a valid editable view must be open (see undoChange).
        if (!view_id || !view_type || (!model && !searchViewId)) {
            this.notification.add("Open the view you want to redo changes on first.", {
                title: "Nothing to redo here",
                type: "warning",
            });
            return;
        }
        const redoElement = storage[storage.length - 1];
        try {
            await this.rpc('cyllo_studio/redo_action', {
                model: model,
                view_type: view_type,
                view_id: view_id,
                arch: redoElement,
            });
        } catch (e) {
            this.notification.add("Could not redo the change.", {
                title: "Redo failed",
                type: "danger",
            });
            return; // keep stacks intact
        }
        // Success: move the element from the redo stack back onto the undo stack.
        storage.pop();
        sessionStorage.setItem('ReDO', JSON.stringify(storage));
        const undoStack = JSON.parse(sessionStorage.getItem('UndoRedo') || '[]');
        undoStack.push(redoElement);
        sessionStorage.setItem('UndoRedo', JSON.stringify(undoStack));
        this.action.doAction("studio_reload");
        this.env.bus.trigger('resetProperties');
        window.location.reload();
    }


}
CylloNavBar.props = {
    edit: {
        type: Boolean,
        optional: true
    },
    view: {
        type: Boolean,
        optional: true
    },
    editButton: {
        type: Boolean,
        optional: true
    },
    viewChanged: {
        type: Boolean,
        optional: true
    },
    updateState: {
        type: Function,
        optional: true
    },
    isAnimatingSidebar: {
        type: Boolean,
        optional: true
    },
    activity_view: {
        type: Boolean,
        optional: true
    },
    viewDetails: {
        type: Object,
        optional: true
    },
};
CylloNavBar.components = {
    ViewSelectionDropDown,
};
