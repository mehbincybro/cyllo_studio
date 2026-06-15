/** @odoo-module **/
import {
    Component,
    useState,
    onWillUpdateProps,
    onRendered
} from "@odoo/owl";
import {
    useService
} from "@web/core/utils/hooks";
import {
    FieldProperties
} from "@cyllo_studio/js/view_editor/aside_bar/properties/field_properties/field_properties";
import {
    ButtonProperties
} from "@cyllo_studio/js/view_editor/aside_bar/properties/button_properties/button_properties";
import {
    OverallView
} from "@cyllo_studio/js/view_editor/aside_bar/overall_view/overall_view";
import {
    ExistingFieldProperties
} from "@cyllo_studio/js/view_editor/aside_bar/properties/existing_field_properties/existing_field_properties";
import {
    KanbanFieldProperties
} from "@cyllo_studio/js/view_editor/aside_bar/properties/field_properties/kanban_field_details";
import {
    RibbonProperties
} from "@cyllo_studio/js/view_editor/kanban/ribbon_properties";
import {
    TextProperties
} from "@cyllo_studio/js/view_editor/kanban/text_properties";
import {
    DivProperties
} from '@cyllo_studio/js/view_editor/kanban/div_properties';
import {
    StatusBarButtons
} from '@web/views/form/status_bar_buttons/status_bar_buttons';
import {
    MultiRecordSelector
} from "@web/core/record_selectors/multi_record_selector";
import {
    PageProperties
} from "@cyllo_studio/js/views/cyllo_form/page/page_properties";
import {
    SmartButtonProperties
} from "@cyllo_studio/js/view_editor/aside_bar/properties/smart_button/smart_button_properties";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    ExistingFieldDialog
} from "@cyllo_studio/js/view_editor/aside_bar/dialog/existing_field_dialog";

/**
 * AsideBar Component
 *
 * This component represents the properties sidebar in Odoo Studio. It dynamically
 * renders property panels for different elements such as fields, buttons, Kanban,
 * ribbons, smart buttons, and existing fields depending on the selected item
 * in the editor.
 */

export class AsideBar extends Component {
    static template = "cyllo_studio.AsideBar";
    static props = {
        type: {
            type: String
        },
        handleView: {
            type: Function,
            optional: true
        },
        updateState: {
            type: Function,
            optional: true
        },
        overall: {
            type: Object,
            optional: true
        },
        viewDetails: {
            type: Object,
            optional: true
        },
        fieldProperties: {
            type: Object,
            optional: true
        },
        ExistingFieldProperties: {
            type: Object,
            optional: true
        },
        kanbanComponent: {
            type: Object,
            optional: true
        },
        noteBookProperties: {
            type: Object,
            optional: true
        },
        SmartButtonProperties: {
            type: Object,
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
        ButtonDetails: {
            type: Object,
            optional: true
        },
        KanbanDivProperties: {
            type: Object,
            optional: true
        },
        KanbanSpanProperties: {
            type: Object,
            optional: true
        },
        isX2Many: {
            type: [Boolean, String],
            optional: true
        },
        x2Manylist: {
            type: Object,
            optional: true
        },
        editButton: {
            type: Boolean,
            optional: true
        },
        sibling: {
            type: Object,
            optional: true
        },
    };
    setup() {
        this.actionService = useService("action");
        this.action = useService("action");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.state = useState({
            viewProperty: this.props.type,
            type: this.props.type,
            is_edit: false,
        });
        onWillUpdateProps((props) => {
            if (props.type) {
                this.state.type = props.type
            }
        })
    }

    /**
     * Determine whether the type dropdown should be shown
     */
    get showTypeDropdown() {
        if (this.props.fieldProperties.create) return true;
        if (this.props.ButtonDetails?.newButton && this.props.viewDetails.viewType != 'form' || this.props.sibling?.sibling) return true;
        return false;
    }

    /**
     * Returns combined props for the OverallView component
     */
    get OverallProps() {
        return {
            ...(this.props.overall || {}),
            ...(this.props.viewDetails || {}),
        };
    }

    /**
     * Returns combined props for FieldProperties component
     */
    get fieldPropertiesProps() {
        return {
            ...(this.props.overall || {}),
            ...(this.props.viewDetails || {}),
            ...(this.props.fieldProperties || {}),
            ...(this.props.sibling || {}),
        };
    }

    /**
     * Returns combined props for ExistingFieldProperties component
     */
    get ExistingFieldPropertiesProps() {
        return {
            ...(this.props.viewDetails || {}),
            ...(this.props.ExistingFieldProperties || {}),
        };
    }

    // NEW GETTERS FOR RIBBON VIEW TYPE DIFFERENTIATION
    get showFormRibbon() {
        return (
            this.state.type === "ribbon" &&
            this.props.viewDetails?.view_type === "form"
        );
    }

    get showKanbanRibbon() {
        return (
            this.state.type === "ribbon" &&
            this.props.viewDetails?.view_type === "kanban"
        );
    }

    get FormRibbonProps() {
        return {
            ...(this.props.kanbanComponent || {}),
            viewDetails: {
                ...(this.props.viewDetails || {})
            },

        };
    }

    get KanbanRibbonProps() {
        return {
            ...(this.props.kanbanComponent || {}),
            viewDetails: {
                ...(this.props.viewDetails || {}),
                view_type: 'kanban',
            },
        };
    }


    get KanbanDivPropertiesProps() {
        return {
            ...(this.props.viewDetails || {}),
            ...(this.props.KanbanDivProperties || {}),
        };
    }
    get KanbanFieldPropertiesProps() {
        return {
            viewDetails: {
                ...(this.props.viewDetails || {})
            },
            ...(this.props.overall || {}),
            ...(this.props.fieldProperties || {}),
        };
    }
    get SiblingTextProps() {
        this.props.sibling.type = 'text'
        return {
            ...(this.props.kanbanComponent || {}),
            ...(this.props.sibling || {}),
            viewDetails: {
                ...(this.props.viewDetails || {})
            },

        };
    }
    get KanbanComponentProps() {
        return {
            ...(this.props.kanbanComponent || {}),
            viewDetails: {
                ...(this.props.viewDetails || {})
            },

        };
    }

    //    get KanbanSpanProps() {
    //        console.log("12121")
    //        return {
    //            ...(this.props.overall || {}),
    //            ...(this.props.kanbanComponent || {}),
    //            span_properties: {
    //            ...(this.props.KanbanSpanProperties || {})},
    //            viewDetails: {
    //                ...(this.props.viewDetails || {})
    //            }
    //        }
    //    }


    get KanbanSpanProps() {
        return {
            ...(this.props.overall || {}),
            ...(this.props.kanbanComponent || {}),
            span_properties: {
                ...(this.props.KanbanSpanProperties || {}),
                properties: {
                    ...(this.props.KanbanSpanProperties?.properties || {}),
                    elementInfo: {
                        ...(this.props.KanbanSpanProperties?.properties?.elementInfo || {}),
                        path: this.props.KanbanSpanProperties?.properties?.elementInfo?.path ||
                            this.props.kanbanComponent?.path ||
                            this.props.KanbanSpanProperties?.path
                    }
                }
            },
            viewDetails: {
                ...(this.props.viewDetails || {})
            }
        }
    }

    /**
     * Closes the sidebar and updates parent state
     */
    async closeSidebar() {
        this.env.bus.trigger('CLEAR-MENU', {
            fromClose: true
        });
        this.props.updateState("editButton", true);
        this.props.updateState("isAnimatingSidebar", true);
        this.props.updateState("edit", false);
        this.action.doAction('studio_reload')
    }
    get noteBookPropertiesProps() {
        return {
            ...(this.props.noteBookProperties || {}),
            viewDetails: {
                ...(this.props.viewDetails || {})
            },

        };
    }
    get SmartButtonPropertiesProps() {
        return {
            ...(this.props.SmartButtonProperties || {}),
            ...(this.props.overall || {}),
            viewDetails: {
                ...(this.props.viewDetails || {})
            },

        };
    }
    get ButtonPropertiesProps() {
        return {
            ...(this.props.ButtonDetails || {}),
            ...(this.props.sibling || {}),
            viewDetails: {
                ...(this.props.viewDetails || {}),

            },

        };
    }

    get viewDetails() {
        return {
            ...(this.props.viewDetails ?? {})
        };
    }
    /**
    * Determines which type of property editor to render
    */
    get propsType() {
        return (
            this.state.type === "Properties" ||
            this.state.type === "ButtonProperties" ||
            this.state.type === "text" ||
            this.state.type === "SmartButtonProperties" ||
            this.state.type === "KanbanFieldProperties" ||
            this.state.type === "KanbanDivProperties"
        );
    }

    /**
     * Returns default field type based on sidebar state and view type
     */
    get defaultFieldType() {
        if (this.state.type == 'ButtonProperties') {
            return "button_prop"
        }
        else if (this.viewDetails?.viewType === 'tree' && !this.OverallProps.mode?.editable) {
            this.createButton()
            return "button_prop";
        }

        else if (this.state.type == 'Properties') {
            return "new_field"
        }
        else if (this.state.type == 'text') {
            return "string"
        }
        else if (this.state.type = 'ExistingFieldProperties') {
            return "existing_field"
        }
    }

    /**
     * Returns selectable field type options based on view and sibling conditions
     */
    get fieldType() {
        const options = [
            { value: 'new_field', label: 'New Field' },
            { value: 'button_prop', label: 'Button' },
            { value: 'existing_field', label: 'Existing Field' },
            { value: 'string', label: 'String' },
        ];

        if (this.viewDetails?.viewType === 'form' && !this.props.sibling?.sibling) {
            return options.filter(opt => opt.value !== 'button_prop' && opt.value !== 'string');
        }
        if (this.viewDetails?.viewType === 'form' && this.props.sibling?.sibling) {
            return options;
        }
        if (this.viewDetails?.viewType === 'tree' && !this.OverallProps.mode?.editable) {
            return options.filter(opt => opt.value !== 'new_field' && opt.value !== 'string');
        }

        return options.filter(opt => opt.value !== 'string');
    }

    get isTreeNew() {
        return (
            this.props.viewDetails.viewType == "tree" && this.props.fieldProperties.create
        )
    }

    /**
     * Handles selection of field type from dropdown
     * @param {String} ev - Selected type value
     */
    FieldTypeChange(ev) {
        if (ev == 'button_prop') {
            this.state.type = 'ButtonProperties';
            this.createButton();
        } else if (ev == 'new_field') {
            this.state.type = 'Properties';
        } else if (ev == 'existing_field') {
            this.dialogService.add(ExistingFieldDialog, {
                fields: this.props.viewDetails?.allFields || {},
                path: this.props.fieldProperties.path,
                model: this.props.viewDetails?.model,
                view_type: this.props.viewDetails?.viewType,
                viewId: this.props.viewDetails?.viewId,
                onClose: () => {
                    this.state.type = "Properties";
                    this.props.updateState("edit", true);
                }

            });
            this.state.type = 'ExistingFieldProperties';
        }
        else if (ev == 'string') {
            this.state.type = 'text'
        }

    }

    /**
    * Triggers creation of a new button in the current view
    */
    async createButton() {
        this.env.bus.trigger("BUTTON_DETAILS", {
            type: "ButtonProperties",
            path: "/tree",
            position: "inside",
            newButton: true,
        });
    }
}

// Register components used inside AsideBar
AsideBar.components = {
    FieldProperties,
    OverallView,
    ButtonProperties,
    ExistingFieldProperties,
    KanbanFieldProperties,
    RibbonProperties,
    TextProperties,
    MultiRecordSelector,
    PageProperties,
    SmartButtonProperties,
    CylloStudioDropdown,
    ExistingFieldDialog,
    DivProperties
};