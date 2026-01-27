/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
export class StickyNoteItem extends Component {
    /**
    * @Extends Component
    */
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    }
    async _remove(id) {
        // Removes a note by calling the ORM method unlink and triggers an event.
        await this.orm.call(
            "sticky.note",
            "unlink",
            [id],
        );
        this.env.bus.trigger("note_remove", id);
    }
    async _edit (id, title, description, colour) {
        // edits a note by triggering an event with updated information.
        let item_dict = { id , title , description, colour}
        this.env.bus.trigger("note_update",item_dict);
    }
}
StickyNoteItem.template = "StickyNotesItem";