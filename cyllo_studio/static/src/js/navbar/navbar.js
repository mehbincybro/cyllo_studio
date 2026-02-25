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
    onMounted,onPatched
} from "@odoo/owl";
import {
    FirstPage
} from '@cyllo_studio/js/new_app/new_app_templates';
import { RemoveSessions } from '@cyllo_studio/js/root/studio_wrapper';

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
        this.state = useState({
            studioEditableList: false,
            lightMode: false,
            isStudioEdit: false,
            canUndo: JSON.parse(sessionStorage.getItem('UndoRedo') || '[]').length > 0, //starlin
            canRedo: JSON.parse(sessionStorage.getItem('ReDO') || '[]').length > 0, //starlin
        });
        useBus(this.env.bus, 'studio_editable_list', (res) => {
            this.state.studioEditableList = res.detail;
            this.props.updateState("edit", false);
        });
                useBus(this.env.bus, 'PREVIEW_MODE_CHANGED', ({detail}) => {
    this.state.isPreviewMode = detail.isPreviewMode;
    });
        useBus(this.env.bus, "STUDIO_EDIT_BUTTON_HIDE", () => {
            this.props.updateState("editButton", false);
        });

        this.viewChange = this.viewChange.bind(this);
        onMounted(() => {
            this.updateUndoRedoState();
            setInterval(() => this.updateUndoRedoState(), 500);
        });
        onPatched(() => {
            let studioViews = this.root?.el.querySelector('.cy-studio-views');
            if (studioViews) {
                studioViews.style.display = this.state.studioEditableList ? 'none' : 'block';
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

    /** Show the miscellaneous menu dropdown aligned properly. */
    ShowMiscellaneousDrop() {
        const menuContainer = this.root.el.querySelector('.cy-nav-Menu-button');
        const menuCard = this.root.el.querySelector('.cy-miscellaneous_card');
        //        menuCard.style.display = 'block';
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
    const [modelId, viewId] = await this.orm.call("ir.model", "cyllo_get_studio_action_acl",
    [this.action.currentController.action.res_model, 'ir.actions.report']);

    const currentAction = this.action.currentController.action;

    this.action.doAction({
        type: "ir.actions.client",
        tag: "report_view",
        name: `${currentAction.display_name || currentAction.name} `,
        context: {
            parent_model: currentAction.res_model,
            parent_name: currentAction.display_name || currentAction.name,
        }
    });
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
    viewChange(attr, value) {
        this.props.updateState("editButton", false);
        this.props.updateState(attr, value);
    }
    /** Close the studio session and reload the page. */
    handleClose() {
        const appId = this.menuService.getCurrentApp().id
        localStorage.setItem("cy_selected_app", appId || false)
        sessionStorage.removeItem("invisible");
        const currentUrl = new URL(window.location.href);
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
        try {
            const storage = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            const undoElement = storage.pop();
            let view_type = this.props.viewDetails.viewType
            let view_id = this.props.viewDetails.viewId
            sessionStorage.setItem('UndoRedo', JSON.stringify(storage));
            const searchViewId = sessionStorage.getItem("searchViewId");
            const element = document.querySelector('.o_content');
            if (searchViewId) {
                view_type = 'search'
                view_id = searchViewId
            }
            if (undoElement) {
                let redoStack = JSON.parse(sessionStorage.getItem('ReDO')) || [];
                redoStack.push(undoElement);
                sessionStorage.setItem('ReDO', JSON.stringify(redoStack));
                let xPaths = false
                const count = (undoElement.match(/<xpath /g) || []).length;
                if (count >= 2) {
                    xPaths = true
                }

                await this.rpc('cyllo_studio/undo_action', {
                    model: this.props.viewDetails.model,
                    view_type: view_type,
                    view_id: view_id,
                    xPaths: xPaths,
                });
            }
        } finally {
            this.action.doAction("studio_reload");
            this.env.bus.trigger('resetProperties')
            window.location.reload()
        }
    }

    async redoChange() {
        try {
            const storage = JSON.parse(sessionStorage.getItem('ReDO')) || [];
            const storage_undo = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            const redoElement = storage.pop();
            let view_type = this.props.viewDetails.viewType
            let view_id = this.props.viewDetails.viewId
            sessionStorage.setItem('ReDO', JSON.stringify(storage));
            const searchViewId = sessionStorage.getItem("searchViewId");
            const element = document.querySelector('.o_content');
            if (searchViewId) {
                view_type = 'search'
                view_id = searchViewId
            }
            if (redoElement) {
                let undoStack = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                undoStack.push(redoElement);
                sessionStorage.setItem('UndoRedo', JSON.stringify(undoStack));

                await this.rpc('cyllo_studio/redo_action', {
                    model: this.props.viewDetails.model,
                    view_type: view_type,
                    view_id: view_id,
                    arch: redoElement,
                });
            }
        } finally {
            this.action.doAction("studio_reload");
            this.env.bus.trigger('resetProperties')
            window.location.reload()
        }
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