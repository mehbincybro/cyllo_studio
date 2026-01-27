/** @odoo-module **/
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, useExternalListener, useState, onWillStart, useRef } from "@odoo/owl";
import { StickyNoteAdd } from "./sticky_notes_add";
import { StickyNoteCreate } from "./sticky_notes_create";
import { StickyNoteItem } from "./sticky_notes_item";
import { StickyNoteUpdate } from "./sticky_notes_update";
import { session } from "@web/session";
export class StickyNotes extends Component {
    /**
    * @extends Component
    */
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.state = useState({
            isEdit: false,
            notes: [],
            update:false,
            edit_note:false,
        })
        this.menuRef = useRef("menuRef")
        useExternalListener(document, "keydown", this.onKeyDown);
        useExternalListener(window, "click", this.onWindowClick);
        useBus(this.env.bus, 'note_updates', ({detail})  => {
            this.state.notes.unshift(detail)
            this.state.isEdit = !this.state.isEdit
        });
        useBus(this.env.bus, 'note_remove', ({detail})  => {
            const indexToRemove = this.state.notes.findIndex(note => note.id === detail);
            /**
            * Check if a note with a specific ID exists in the 'notes'
            array and remove it if found.
            */
            if (indexToRemove !== -1) {
                this.state.notes.splice(indexToRemove, 1);
            }
        });
        useBus(this.env.bus, 'note_update', ({detail})  => {
            this.state.update = true
            this.state.edit_note = detail
            this.state.isEdit = !this.state.isEdit
        });
        useBus(this.env.bus, 'note_edit', ({ detail }) => {
            const noteIndex = this.state.notes.findIndex((note) => note.id === detail.id);
            /**
            * Update or add a note to the 'notes' array based on the 'detail.id'.
            */
            if (noteIndex !== -1) {
                this.state.notes[noteIndex] = detail;
            } else {
                this.state.notes.push(detail);
            }
            this.state.edit_note = false
            this.state.isEdit = false
        });
        var self = this;
        var current_user = session.uid;

        onWillStart(async () => {
            // It performs a search operation in 'sticky.note' model using the ORM to retrieve notes
            await this.orm.call(
                "sticky.note",
                "search_read",
                [[['create_uid', '=', current_user]]],
                { order : 'id desc'}
            ).then(function(result  ) {
                self.state.notes = result;
            });
        });
    }
    async _close_note() {
        // Closes the note by triggering an event on the bus.
        this.env.noteClose()
    }
    onWindowClick(ev) {
        if (!$(this.menuRef.el).is(ev.target) && $(this.menuRef.el).has(ev.target).length === 0 && !this.state.isEdit == true) {
            this._close_note();
        }
    }
    onKeyDown(ev) {
        if (ev.key === 'Escape' && !this.state.isEdit == true) {
            this._close_note()
        }
    }
}
StickyNotes.template = "StickyNotes";
StickyNotes.components = { StickyNoteAdd, StickyNoteCreate, StickyNoteItem, StickyNoteUpdate};