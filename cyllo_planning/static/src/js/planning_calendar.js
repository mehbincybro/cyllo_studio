/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarModel } from "@web/views/calendar/calendar_model";

patch(CalendarModel.prototype, {
    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        const result = super.normalizeRecord(...arguments);
        if (rawRecord.is_conflict) {
            result.isStriked = true;
            result.classNames = [...(result.classNames || []), "o_event_striked"];
        }
        return result;
    }
});
