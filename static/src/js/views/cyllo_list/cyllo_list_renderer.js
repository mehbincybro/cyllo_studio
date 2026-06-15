/** @odoo-module */

/**
 * CylloListRenderer
 *
 * Custom List (Tree) view renderer for Cyllo Studio, extending the default Odoo
 * listView.Renderer. Provides enhanced capabilities for dynamic field manipulation,
 * drag-and-drop reordering, session-based visibility, and interactive UI behaviors.
 *
 * Features:
 * 1. Field Management:
 *    - Handles adding new fields dynamically to the list view.
 *    - Triggers "FIELDS_DETAILS" events with field metadata for side panels.
 *    - Tracks edit state using sessionStorage to prevent concurrent edits.
 *
 * 2. Drag-and-Drop:
 *    - Integrates dragula for reordering columns in non-grouped lists.
 *    - Supports custom drag constraints to prevent moving non-draggable elements.
 *    - Sends updated field positions to the server via RPC calls.
 *
 * 3. Column Visibility:
 *    - Respects session-based visibility toggles using 'invisible' flag.
 *    - Evaluates column_invisible attributes using evalViewModifier.
 *
 * 4. Mouse Hover Effects:
 *    - Highlights columns on hover for better UX during list editing.
 *
 * 5. Column Width Management:
 *    - Computes and sets default widths for columns based on relative or absolute sizes.
 *    - Adjusts widths dynamically depending on whether selectors are enabled.
 *
 * 6. Integration with Cyllo Studio:
 *    - Triggers "LIST_DETAILS" event with list configuration for the Studio sidebar.
 *    - Tracks new elements and edits using sessionStorage flags for undo/redo consistency.
 *
 * Services Used:
 * - rpc: For server communication when moving fields.
 * - action: For triggering client-side actions like 'studio_reload'.
 * - effect: For showing notifications to the user.
 *
 * Components and Templates:
 * - template: "cyllo_studio.CylloListRenderer"
 * - rowsTemplate: "cyllo_studio.CylloListRenderer.Rows"
 * - recordRowTemplate: "cyllo_studio.CylloListRenderer.RecordRow"
 *
 * Purpose:
 * Enables a fully interactive list view editor within Cyllo Studio, allowing
 * drag-and-drop field reordering, dynamic visibility toggling, and live field
 * property editing.
 */
import { listView } from "@web/views/list/list_view";
import { onMounted,useRef,useState ,onWillRender} from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import {useService} from "@web/core/utils/hooks";


export class CylloListRenderer extends listView.Renderer {
  setup() {

    super.setup();
       this.list_trRef = useRef("list-tr");
       this.rpc = useService('rpc');
       this.action = useService("action");
       this.notification = useService("effect");
       this.state = useState({
            ...this.state,
            invisible_session: false,
            editable_field: false
       })
       this.state.invisible_session = sessionStorage.getItem("invisible");
       document.body.classList.toggle("cy-hide-invisible", !this.state.invisible_session);
//       try {
//    this.env.bus.trigger("CYLLO:SHOW_INVISIBLE_TOGGLED", !!this.state.invisible_session);
//} catch (e) {}
    onWillRender(()=>{
        this.state.invisible_session = sessionStorage.getItem('invisible')
    })
    onMounted(() => {
      console.log('thato',this.env.config.viewType)
      const checked = !!sessionStorage.getItem("invisible");
      document.body.classList.toggle("cy-hide-invisible", !checked);
      // Listen for invisible toggle and update state instantly
      try {
 useBus(this.env.bus, "CYLLO:SHOW_INVISIBLE_TOGGLED", (ev) => {
                const isChecked = ev.detail ? ev.detail[0] : ev;
                console.log("is chck",isChecked)
                this.state.invisible_session = isChecked;
                });
      } catch(e){
       console.warn("Bus listener setup failed:", e);
      }
      sessionStorage.removeItem("newListElement");
      this.env.bus.trigger("LIST_DETAILS", {
        mode: this.props.archInfo,
        model: this.env.model?.config.resModel,
        viewId: this.env.config.viewId,
        viewType: "tree",
        allFields: this.props.list.fields,
        activeFields: this.props.list.activeFields,
      });
      const isGrouped = this.props.list.isGrouped;
       const self = this
       const treeEl = self.list_trRef.el
       if (self.props.activeActions.type === "view" && !isGrouped && treeEl) {
       let originalOrder = Array.from(treeEl.children);
    const sortableInstance = Sortable.create(treeEl, {
      animation: 150,
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      dragClass: 'sortable-drag',

      filter: function(evt, item) {
        const el = evt.target;
        return (
          el.classList.contains("add-fields") ||
          item.classList.contains('add-fields') ||
          item.classList.contains('o_list_open_form_view') ||
          el.classList.contains('o_list_open_form_view') ||
          item.classList.contains('o_list_controller')
        );
      },

      onStart: function(evt) {
        // Snapshot the current order when drag starts
        originalOrder = Array.from(treeEl.children);
      },

      onEnd: async function(evt) {
        const el = evt.item;

        // No movement — nothing to do
        if (evt.oldIndex === evt.newIndex) return;

        // --- KEY FIX: Read the sibling AFTER Sortable has moved the element ---
        // At this point, Sortable has already rearranged the DOM.
        // The next o_column_* or th sibling after el is our "before" target.
        const allThs = Array.from(treeEl.children);
        const droppedIdx = allThs.indexOf(el);

        // Find the next real column th after the dropped position
        let siblingEl = null;
        for (let i = droppedIdx + 1; i < allThs.length; i++) {
          const th = allThs[i];
          // Skip non-column headers (optional button, open form view, etc.)
          if (
            th.classList.contains('add-fields') ||
            th.classList.contains('o_list_open_form_view') ||
            th.classList.contains('o_list_controller') ||
            th.classList.contains('o_list_record_selector')
          ) continue;
          siblingEl = th;
          break;
        }

        // --- IMMEDIATELY revert DOM to original order ---
        // This prevents visual glitch since studio_reload will re-render correctly
        originalOrder.forEach(child => treeEl.appendChild(child));

        // Resolve paths
        const fieldPath =
          el.getAttribute('cy-xpath') ||
          el.querySelector('.cy-listBtn')?.getAttribute('cyxpath');

        const siblingField = siblingEl
          ? (siblingEl.getAttribute('cy-xpath') ||
             siblingEl.querySelector('.cy-listBtn')?.getAttribute('cyxpath'))
          : null;

        // If no sibling found, we're dropping at the end → position 'inside' parent
        // If sibling found → position 'before' that sibling
        const sourceField = evt.from?.getAttribute('cy-xpath');
        const path = siblingField || sourceField;
        const position = siblingField ? 'before' : 'inside';

        if (!fieldPath) {
          console.error('Could not resolve fieldPath for dragged column', el);
          return;
        }

        if (self.state.drop === true) {
          self.env.bus.trigger("CLEAR-MENU");
        }

        const view_id = self.env.config.viewId;

        try {
          const response = await self.rpc("/cyllo_studio/move/tree", {
            method: 'move_tree',
            model: self.props.list.model.config.resModel,
            view_id: self.env.config.viewId,
            view_type: self.env.config.viewType === 'list'
              ? 'tree'
              : self.env.config.viewType,
            args: [],
            kwargs: {
              path,
              position,
              fieldPath,
              viewType: self.env.config.viewType,
              view_id: view_id ?? null,
              model: self.props.list.model.config.resModel
            }
          });

          if (response) {
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr);
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
          }
        } finally {
          self.env.services.ui.unblock();
        }

        self.action.doAction('studio_reload');
      }
    });
  }

    });
  }

    /**
   * Clears hover-based highlight styles when leaving the table.
   */
  tableLeave(ev) {
    const elements = document.querySelectorAll(".border-class-list");
    elements.forEach((e) => {
      e.classList.remove("border-class-list");
    });
  }

    /**
   * Computes active columns for rendering.
   *
   * @param {Object} list - List view object.
   * @returns {Array} - Array of active/visible columns.
   */
    getActiveColumns(list) {
//        const invisible_session = sessionStorage.getItem('invisible');
//        return this.allColumns.filter((col) => {
//            if (!invisible_session) {
//                if (list.isGrouped && col.widget === "handle") {
//                    return false; // no handle column if the list is grouped
//                }
//                if (col.optional === 'hide') {
//                    return false
//                }
//                if (col.optional && !this.optionalActiveFields[col.name]) {
//                    return false;
//                }
//                if (this.evalColumnInvisible(col.column_invisible)) {
//                    return false;
//                }
//            }
//            return true;
//        });
//    }
    return this.allColumns.filter((col) => {
        if (list.isGrouped && col.widget === "handle") {
            return false; // no handle column if the list is grouped
        }

        // Don't filter out optional or invisible columns
        // Let them render with the cy-studio-striped class

        return true;
    });
}

    /**
   * Safely evaluates column invisibility expressions.
   *
   * @param {String} columnInvisible - Expression for column visibility.
   * @returns {Boolean} - Whether the column should be invisible.
   */

    evalColumnInvisible(columnInvisible) {
          try {
                return this.props.evalViewModifier(columnInvisible);
          } catch (e) {
                console.warn("Column invisible eval failed:", e.message, columnInvisible);

                if (columnInvisible && columnInvisible.includes("parent")) {
                    return false; // keep column visible
                }
                throw e;
          }
    }
     /**
   * Highlights the hovered column across the entire table.
   *
   * @param {Event} ev - Mouseover event.
   */
  onMouseHover(ev) {
    const elements = document.querySelectorAll(".border-class-list");
    elements.forEach((e) => {
      e.classList.remove("border-class-list");
    });

    const currentElement = ev.target.closest("th") || ev.target.closest("td");
    const headers = ev.target
      .closest("tr")
      .querySelectorAll(currentElement.tagName);
    const colIndex = Array.from(headers).indexOf(currentElement);
    const rows = document.querySelectorAll("tr");
    rows.forEach((row) => {
      let cells = row.querySelectorAll("td");
      cells = cells.length ? cells : row.querySelectorAll("th");
      if (
        cells[colIndex] &&
        parseInt(cells[colIndex].getAttribute("colspan") || 0) <= 1
      ) {
        cells[colIndex].classList.add("border-class-list");
      }
    });
  }

  /**
   * Triggers FIELDS_DETAILS event for the selected column.
   * Ensures no concurrent edit is active before opening the sidebar.
   *
   * @param {Event} ev - Click event.
   * @param {Object} column - Selected column metadata.
   */
  listFieldDetails(ev,column) {
    let Edit = sessionStorage.getItem("newListElement");
    if (Edit){
        return this.notification.add({
            title: "Validation Error",
            message: "Edit is in progress.",
            description: "Please save or cancel the current process.",
            type: "notification_panel",
            notificationType: "warning",
            animation: false,
        });
    }

    const fieldType = this.props.list._config.fields[column.name]?.type || "";
    const relational_fields =  this.props.list._config.fields[column.name]?.relation || "";
    this.env.bus.trigger("FIELDS_DETAILS", {
      mode: column.attrs || {},
      name: column.name || "",
      label: column.label || "",
      widget: column.widget || "",
      options: column.options || "",
      fieldType: fieldType || "",
      context: column?.context || "",
      related_model:relational_fields || "",
      type: "Properties",
      edit:true,
      cy_path:column.attrs["cy-xpath"],
      help: column.help || "",
      placeholder: column.attrs["placeholder"] || "",
      dynamic_placeholder: column.attrs["dynamic_placeholder"] || "",
      column_invisible: column.column_invisible || 'false',
      invisible: column.invisible || 'false',
      readonly: column.readonly || 'false',
      required: column.required || 'false',
    });
  }

  /**
   * Creates a placeholder "new field" column in the list.
   * Used when the user initiates adding a new field from the UI.
   *
   * @param {Event} ev - Click event on add-field trigger.
   */
    itemOnClick(ev) {
        sessionStorage.setItem("newListElement", true);

        const newth = document.createElement('th');
        const newtd = document.createElement('td');

        newth.setAttribute('data-tooltip-delay', '1000');

        newth.setAttribute('tabindex', '-1');
        newtd.setAttribute('tabindex', '-1');
        newth.setAttribute('data-name', 'tax_id');
        newth.className = 'add-fields align-middle cursor-default o_many2many_tags_cell opacity-trigger-hover';
        newth.style.width = '150px';
        newth.innerHTML = `
            <div class="d-flex">
                <span class="d-block min-w-0 text-truncate flex-grow-1">Select Field</span>
                <i class="d-none fa-angle-down opacity-0 opacity-75-hover"></i>
            </div>
            <span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span>
        `;
        let targetContainer = ev.target.parentElement;
        let specificElement = ev.target
        let parentXpath = '/tree'
        const viewArch = this.env.config.viewArch.attributes
        let truncatedPath = ""
        const path = ev.target.parentElement.parentElement.children[0].getAttribute('cy-xpath');
        if (targetContainer) {
            this.env.bus.trigger("FIELDS_DETAILS", {
                type: "Properties",
                create: true,
                cy_path :'/tree',
            })
        }
    }
   /**
   * Sets default column widths based on their type (absolute/relative).
   * Handles proportional distribution for relative widths.
   */
  setDefaultColumnWidths() {
    const widths = this.state.columns.map((col) =>
      this.calculateColumnWidth(col)
    );
    const sumOfRelativeWidths = widths
      .filter(({ type }) => type === "relative")
      .reduce((sum, { value }) => sum + value, 0);

    const columnOffset = this.hasSelectors ? 2 : 1;
    widths.forEach(({ type, value }, i) => {
      const headerEl = this.tableRef.el.querySelector(
        `th:nth-child(${i + columnOffset})`
      );
      if (type === "absolute" && headerEl) {
        if (this.isEmpty) {
          headerEl.style.width = value;
        } else {
          headerEl.style.minWidth = value;
        }
      } else if (type === "relative" && this.isEmpty) {
        headerEl.style.width = `${((value / sumOfRelativeWidths) * 100).toFixed(
          2
        )}%`;
      }
    });
  }
  getCellClass(column, record) {
    		let classes = super.getCellClass(...arguments)
    		    if (column.widget == "handle") {
    		        classes += ' pe-none';
    		    }
    		return classes
    	}
}
CylloListRenderer.template = "cyllo_studio.CylloListRenderer";
CylloListRenderer.rowsTemplate = "cyllo_studio.CylloListRenderer.Rows";
CylloListRenderer.recordRowTemplate =
  "cyllo_studio.CylloListRenderer.RecordRow";

CylloListRenderer.components = {
  ...listView.Renderer.components,
};
