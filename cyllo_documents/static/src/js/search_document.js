/** @odoo-module **/
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { patch } from "@web/core/utils/patch";

patch(SearchPanel.prototype, {
    setup() {
        super.setup();
    },
    async toggleCategory(category, value) {
        /*method working while toggle search panel and trigger 'searchPanel_toggle' with id of search panel */
        if (value.childrenIds.length) {
            const categoryState = this.state.expanded[category.id];
            if (categoryState[value.id] && category.activeValueId === value.id) {
                delete categoryState[value.id];
            } else {
                categoryState[value.id] = true;
            }
        }
        if (category.activeValueId !== value.id) {
            this.env.searchModel.toggleCategoryValue(category.id, value.id);
        }
        this.env.bus.trigger('searchPanel_toggle', {
            Id: value.id,
            workspace: value,
            category: category
        })
    }
});