/** @odoo-module **/

/**
 * ListOverall
 *
 * Component to manage overall settings and properties of a list (tree) view
 * in Cyllo Studio.
 *
 * Features:
 * 1. Field Management:
 *    - Filters and validates fields based on `activeFields` and `allFields` props.
 *    - Sorts fields alphabetically and stores them in `this.fields`.
 *    - Generates unique field names for dynamically created fields.
 *
 * 2. Position & Sorting:
 *    - Provides options for record insertion positions: top, bottom, or open form view.
 *    - Exposes default sorting and position values for the list view.
 *
 * 3. State Handling:
 *    - Tracks session-based visibility with `this.state.invisible`.
 *    - Updates fields dynamically when component props change.
 *
 * 4. Components:
 *    - Integrates `CylloStudioDropdown` for field selection and sorting.
 *
 * Purpose:
 * Enables users to configure and customize the list view in Studio mode,
 * including field visibility, sorting, and record insertion positions.
 */
import {
	Component,
	onWillStart,
	useEffect,
	onWillUpdateProps,
	useState
} from "@odoo/owl";
import {
	CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
	_t
} from "@web/core/l10n/translation";
import {
	sortBy
} from "@web/core/utils/arrays";
import {
	validateField
} from "@cyllo_studio/js/actions/utils";

export class ListOverall extends Component {
	static template = "cyllo_studio.ListOverall";
	setup() {
        this.state = useState({
            invisible : false
        })
		onWillStart(() => {
            this.state.invisible =  sessionStorage.getItem('invisible');
			const {
				activeFields = {}, allFields = {}
			} = this.props;
			if (Object.keys(activeFields).length && Object.keys(allFields).length) {
				this.currentField = Object.keys(activeFields).reduce(
					(acc, fieldName) => {
						acc[fieldName] = allFields[fieldName];
						return acc;
					}, {}
				);
				const fields = Object.entries(this.currentField)
					.filter(([fieldName, field]) => validateField(fieldName, field))
					.map(([fieldName, field]) => ({
						name: fieldName,
						...field
					}));
				this.fields = sortBy(fields, "string");
			}
		});
		onWillUpdateProps(async (nextProps) => {
			const {
				activeFields = {}, allFields = {}
			} = this.props;
			if (Object.keys(activeFields).length && Object.keys(allFields).length) {
				this.currentField = Object.keys(activeFields).reduce(
					(acc, fieldName) => {
						acc[fieldName] = allFields[fieldName];
						return acc;
					}, {}
				);
				const fields = Object.entries(this.currentField)
					.filter(([fieldName, field]) => validateField(fieldName, field))
					.map(([fieldName, field]) => ({
						name: fieldName,
						...field
					}));
				this.fields = sortBy(fields, "string");
			}

		});

	}
      /**
     * Getter: Provides insertion position options for records in the list view.
     * - Options: "top", "bottom", or "open form view".
     * - Used in dropdowns for configuring default record insertion behavior.
     *
     * @returns {Array<{value: string, label: string}>}
     */
	get position() {
		const value = ["top", "bottom", ""];
		const position = [
			" Add Record At Top",
			" Add Record At Bottom",
			" Open Form View",
		];
		const arr = [];
		for (let i = 0; i < value.length; i++) {
			const obj = {
				value: value[i],
				label: position[i],
			};
			arr.push(obj);
		}
		return arr;
	}

    /**
     * Getter: Returns the default sort field for the list view.
     * - Extracts the first field from `mode.defaultOrder` if available.
     *
     * @returns {string|null} Field name or null
     */
	get defaultSortValue() {
		return this.props.mode.defaultOrder?.[0]?.name || null;
	}

	/**
     * Getter: Returns the default record insertion position.
     * - Based on the `editable` property in view mode.
     *
     * @returns {string} "top" | "bottom" | ""
     */
	get defaultPosition() {
		return this.props.mode.editable || "";
	}

	/**
     * Utility: Generates a unique random field name.
     * - Uses timestamp, random number, and alphanumeric string for uniqueness.
     * - Typically used when creating new custom fields in Studio mode.
     *
     * @returns {string} Example: "x_studio_1695632649000_457_ab12c"
     */
	generateRandomFieldName() {
		const timestamp = Date.now();
		const randomChars = Math.random().toString(36).substring(2, 7); // Random alphanumeric string of length 5
		const randomNum = Math.floor(Math.random() * 1000);
		return `x_studio_${timestamp}_${randomNum}_${randomChars}`;
	}

    /**
     * Getter: Provides field options for sorting configuration.
     * - Uses the current list of validated and sorted fields.
     * - Prepends a "Default" option.
     *
     * @returns {Array<{value: string, label: string}>}
     */
	get sortValues() {
		const arr = [];
		for (let value in this.fields) {
			const obj = {
				value: this.fields[value].name,
				label: this.fields[value].string,
			};
			arr.push(obj);
		}
		return [{
			value: "",
			label: "Default"
		}, ...arr];
	}
}
ListOverall.components = {
	CylloStudioDropdown,
};