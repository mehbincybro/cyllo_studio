/** @odoo-module **/
/**
 * PageProperties
 *
 * Component for editing the properties of a notebook page in Odoo Studio.
 * Provides functionality to:
 *   - Edit page title, visibility, and autofocus settings
 *   - Add or edit invisible domain expressions
 *   - Update or remove pages via RPC calls
 *   - Track undo/redo operations for changes
 *
 * Methods:
 *   - onDomainRadioClick(event): Handles click events for "autofocus" and "invisible" radio buttons.
 *   - pageInvisibleDomain(): Opens a dialog to edit the domain expression for page invisibility.
 *   - handleListener(isAdd=true): Adds or removes global click/mousedown listeners for autosave.
 *   - updatePage(): Sends RPC call to update page properties and triggers undo/redo storage.
 *   - removePage(): Sends RPC call to delete the page and triggers undo/redo storage.
 *
 * Props:
 *   - properties: Object containing page properties such as cyXpath, title, autofocus, invisible.
 *   - viewDetails: Object containing view metadata like viewId, model, viewType, activeFields, and allFields.
 *
 * Components:
 *   - MultiRecordSelector: For selecting multiple records in page configuration.
 *
 * Usage:
 *   Used inside Studio notebook page editor to allow users to manage page-specific configurations.
 */

import {
  Component,
  useState,
  onWillStart,
  onWillUpdateProps,
  useExternalListener,
  onWillUnmount,
} from "@odoo/owl";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import {_t} from "@web/core/l10n/translation";
import { handleUndoRedo } from "@cyllo_studio/js/utils/undo_redo_utils";
import {
    CylloExpressionEditorDialog
} from "@cyllo_studio/js/view_editor/components/expression_editor_dialog/expression_editor_dialog";


export class PageProperties extends Component {
  setup() {
    const self = this;
    this.rpc = useService("rpc");
    this.action = useService("action");
    this.addDialog = useOwnedDialogs();
    this.notification = useService("effect");
    this.state = useState({
      pageProperties: this.props.properties,
      group_ids: [],
    });
    onWillUpdateProps((nextProps) => {
      this.state.pageProperties = nextProps.properties;
        });
    }

onDomainRadioClick = ({ target }) => {
    if (target.name === "autofocus") {
        if (target.checked && this.props.autofocus) {


            this.notification.add({
                title: _t("Action cannot be performed"),
                message: "Already AutoFocus Been Used",
                type: "notification_panel",
                notificationType: "warning",
            });

            // Revert the visual state and stop execution
            target.checked = false;
            return;
        }
        this.state.pageProperties[target.name] = target.checked ? "autofocus" : "";

    } else if (target.name === "invisible") {
        // Handle invisible field logic
        this.state.pageProperties.invisible = target.checked ? "True" : "False";
    }
}

  pageInvisibleDomain() {
    var resModel = this.action.currentController.props.resModel;
    this.addDialog(ExpressionEditorDialog, {
      resModel,
      fields: this.props.viewDetails.allFields,
      expression: this.state.pageProperties.invisible,
      onConfirm: (domain) => (this.state.pageProperties.invisible = domain),
    });
  }
    handleListener(isAdd=true){
        if(isAdd){
            document.addEventListener("click", this.AutoSave, { capture: true });
            document.addEventListener("mousedown", this.AutoSave, { capture: true });
        }else {
            document.removeEventListener("click", this.AutoSave, { capture: true });
            document.removeEventListener("mousedown", this.AutoSave, { capture: true });
        }
    }

  async updatePage() {
    const view_id = this.props.viewDetails.viewId;
    //@error invisible domain with not existing field
   const response = await this.rpc("cyllo_studio/update/page", {
      method: "update_page",
      model: this.props.viewDetails.model,
      view_id: this.props.viewDetails.viewId,
      view_type: "form",
      args: [],
      kwargs: {
        view_id: view_id ? view_id : null,
        model: this.action.currentController.props.resModel,
        path: this.state.pageProperties.cyXpath,
        string: this.state.pageProperties.title,
        autofocus: this.state.pageProperties.autofocus ||'',
        invisible: this.state.pageProperties.invisible ||'',
        viewType: "form",
        active_fields: this.props.viewDetails.activeFields || this.props.viewDetails.allFields,
      },
    });
   if(response){
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr)
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
    }
    this.env.bus.trigger('resetProperties');
    this.action.doAction("studio_reload");
  }
  async removePage() {
    const view_id = this.props.viewDetails.viewId;
    const path =  this.props.properties.cyXpath;
    const response = await this.rpc("cyllo_studio/delete/existing_page", {
      method: "delete_existing_page",
      model: this.props.viewDetails.model,
      view_id: this.props.viewDetails.viewId,
      view_type: this.props.viewDetails.viewType,
      args: [
        {
          path: path ? path : this.props.properties.cyXpath,
          pageName: this.props.properties.title,
          model: this.action.currentController.action.res_model,
        },
      ],
      kwargs: { view_id:this.props.viewDetails.viewId},
    });
       if(response){
            handleUndoRedo(response);
        }
    this.action.doAction("studio_reload");
    this.env.bus.trigger("CLEAR-MENU");
  }

}

PageProperties.components = {
  MultiRecordSelector,
};
PageProperties.template = "cyllo_studio.PageProperties";
