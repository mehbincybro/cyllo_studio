/** @odoo-module */

/**
 * CylloInnerGroup & StudioOuterGroup
 *
 * These components extend the default Odoo form InnerGroup and OuterGroup
 * to provide Studio editing capabilities, including hover effects,
 * adding/deleting fields, panel menus, and sibling elements.
 *
 * Features:
 *  - Hover effects to highlight editable areas.
 *  - Add sibling fields with proper field metadata.
 *  - Delete form elements with Undo/Redo support.
 *  - Trigger bus events to update properties in the Studio panel.
 *
 * Props:
 *  - cy-xpath (optional): The xpath of the group/element for Studio tracking.
 *
 * Services:
 *  - rpc: Server-side calls for adding/deleting elements.
 *  - action: Trigger client-side actions like reloading the view.
 *
 * Methods:
 *  - over / overoff: Toggle hover state.
 *  - onAddClick: Toggle add field button icon.
 *  - addSibling: Add a sibling field in the form.
 *  - handlePanelMenu: Toggle panel menu visibility.
 *  - deleteElement: Remove a form element with Undo/Redo support.
 *  - itemOnDelete: Remove a component programmatically from the server.
 */
const {
    useState,
    useRef,
    onMounted
} = owl
import {
    InnerGroup, OuterGroup
} from "@web/views/form/form_group/form_group";
import {
    registry
} from "@web/core/registry";
import {
    patch
} from '@web/core/utils/patch';
import {
    useService
} from "@web/core/utils/hooks";
import {
    EventBus
} from "@odoo/owl";
import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import {SelectionField} from "@web/views/fields/selection/selection_field";
import {
    Many2ManyTagsFieldColorEditable
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { StatInfoField } from "@web/views/fields/stat_info/stat_info_field";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { CharField, charField} from '@web/views/fields/char/char_field';
import { LabelSelectionField } from '@web/views/fields/label_selection/label_selection_field';
import { ListActivity } from '@mail/views/web/fields/list_activity/list_activity';
import { BadgeField } from "@web/views/fields/badge/badge_field";
import { HandleField } from "@web/views/fields/handle/handle_field";
import { ListSectionAndNoteText } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { KanbanActivity } from "@mail/views/web/fields/kanban_activity/kanban_activity";

OuterGroup.props = [
    ...OuterGroup.props,
    "cy-xpath?"];
OuterGroup.template = "cyllo_studio.Form.StudioOuterGroup";

export class CylloInnerGroup extends InnerGroup {
    static template = "cyllo_studio.Form.StudioInnerGroup";
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.state = useState({
            hover: false,
            addField: true,
            panelMenu: '',
            sibling: '',
        });
        this.action = useService("action");
        onMounted(() => {
            this.env.bus.trigger("allWidgets", {
                widgets: this.content,
            });
        });
    }

    /** Hover effect */
    over(ev) {
        this.state.hover = true
    }

    /** Remove hover effect */
    overoff(ev) {
        this.state.hover = false
    }

    /** Toggle add field icon */
    onAddClick(ev) {
        this.state.sibling = !this.state.sibling
        ev.target.classList.toggle('ri-add-circle-line');
        ev.target.classList.toggle('ri-close-circle-line');
    }

    /** Trigger adding sibling field */
    addSibling(ev, cell) {
        let parent = ev.target.closest(".o_wrap_field");
        let path = parent?.firstElementChild.getAttribute("cy-xpath");
        let itemType = 'normal'
        let field_info = {}
        if (!path) {
                itemType = ''
                let child = parent?.firstElementChild
                path = child.nextElementSibling?.firstElementChild.getAttribute('cy-xpath')
        }else{
            field_info = {
                string: cell.props.fieldInfo?.string,
                name: cell.props.fieldInfo?.name,
                help: cell.props.fieldInfo?.help,
                widget: cell.props.fieldInfo?.widget,
                placeholder: cell.props.fieldInfo?.placeholder,
                invisible: cell.props.fieldInfo?.invisible,
                readonly: cell.props.fieldInfo?.readonly,
                required: cell.props.fieldInfo?.required,
                context: cell.props.fieldInfo?.context,
                options: cell.props.fieldInfo?.options,
                domain: cell.props.fieldInfo?.domain,

            }

        }
        if (path) {
            this.env.bus.trigger("SIBLING_DETAILS", {
                type: "Properties",
                cy_path: path,
                sibling : true,
                item_type : itemType,
                field_info : field_info,
                create : true,
                sibling_edit: false,
                bold: false,
                italic : false,
                underline: false,
                classNames: "",
                string: "",
                is_edit: false,
                invisible: false,
            })
        }
    }

    /** Toggle panel menu */
    handlePanelMenu(ev) {
        if (ev.target.parentElement.nextElementSibling) {
            this.state.panelMenu = false
        } else {
            this.state.panelMenu = true
        }
        ev.target.classList.toggle('ri-arrow-left-s-fill');
        ev.target.classList.toggle('ri-arrow-right-s-fill');
    }
    /** Delete form element with undo support */
    async deleteElement(ev) {
        let parent = ev.target.closest(".o_wrap_field");
        let item_path = parent.firstElementChild.getAttribute("cy-xpath") || "";
        let has_multipath = false;
        if (!item_path) {
            let child = parent.firstElementChild;
            if (child.firstElementChild.nodeName == "BUTTON") {
                item_path = child.firstElementChild.getAttribute("cy-xpath");
            } else {
                has_multipath = true;
                item_path = {
                    first_path: child.firstElementChild.getAttribute("cy-xpath"),
                    second_path: child.nextElementSibling?.firstElementChild.getAttribute("cy-xpath"),
                };
            }
        }

        this.env.services.ui.block();
        try {
            const response = await this.rpc("/cyllo_studio/remove/form_element", {
                item_path,
                has_multipath,
                model: this.env.model.config.resModel,
                view_id: this.env.config.viewId,
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr)
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        } finally {
            this.env.services.ui.unblock();
        }
        this.env.bus.trigger('resetProperties');
        this.action.doAction("studio_reload");
    }

    /** Delete a specific component programmatically */
    async itemOnDelete(ev) {
        this.env.bus.trigger('resetProperties');
        const view_id = this.env.model.env.searchModel.env.config.viewId;
        const response = await this.env.model.rpc("cyllo_studio/delete/component", {
            method: "delete_component",
            model: this.env.model.config.resModel,
            view_id: this.env.model.env.searchModel.env.config.viewId,
            view_type: "form",
            args: [],
            kwargs: {
                viewType: "form",
                path: ev.target.parentElement.parentElement.attributes["cy-xpath"]
                    .value,
                model: this.env.model.config.resModel,
                view_id: view_id ? view_id : null,
            },
        });
        if (response) {
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr)
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }
        this.action.doAction("studio_reload");
    }

}
var value = window.location.href
var searchParams = new URLSearchParams(value.split("?")[1]);
CylloInnerGroup.props = [...InnerGroup.props, "cy-xpath?","striped?","cy-studio-striped?"];
patch(SelectionField, {
    props: {
        ...SelectionField.props,
        striped: { type: Boolean, optional: true }
    }
});
patch(Many2OneField, {
    props: {
        ...Many2OneField.props,
        striped: { type: Boolean, optional: true }
    }
});
patch(BooleanField, {
    props: {
        ...BooleanField.props,
        striped: { type: Boolean, optional: true }
    }
});
patch(Many2ManyTagsFieldColorEditable,{
    props: {
        ...Many2ManyTagsFieldColorEditable.props,
        striped: { type: Boolean, optional: true }
    }
});
patch(X2ManyField,{
    props: {
        ...X2ManyField.props,
        striped: { type: [Boolean,Number], optional: true },
        placeholder:{ type: [Boolean,String], optional: true}
    }
});
patch(StatusBarField,{
    props: {
        ...StatusBarField.props,
        striped: { type: [Boolean,Number], optional: true },
        placeholder: { type: String, optional: true}
    }
});
patch(StatInfoField,{
    props: {
        ...StatInfoField.props,
        striped: { type: [Boolean,Number], optional: true },
        placeholder: { type: String, optional: true}
    }
});
patch(DateTimeField,{
    props: {
        ...DateTimeField.props,
        striped: { type: [Boolean,Number], optional: true }
    }
});
patch(CharField,{
    props: {
        ...CharField.props,
        striped: { type: [Boolean,Number], optional: true }
    }
});
patch(LabelSelectionField,{
    props: {
        ...LabelSelectionField.props,
        placeholder: { type: String, optional: true}
    }
});
patch(ListActivity,{
    props: {
        ...ListActivity.props,
        placeholder: { type: String, optional: true}
    }
});
patch(BadgeField,{
    props: {
        ...BadgeField.props,
        placeholder: { type: String, optional: true}
    }
});
patch(HandleField,{
    props: {
        ...HandleField.props,
        placeholder: { type: String, optional: true}
    }
});
patch(ListSectionAndNoteText,{
    props: {
        ...ListSectionAndNoteText.props,
        placeholder: { type: String, optional: true}
    }
});
patch(KanbanActivity,{
    props: {
        ...KanbanActivity.props,
        placeholder: { type: String, optional: true}
    }
});