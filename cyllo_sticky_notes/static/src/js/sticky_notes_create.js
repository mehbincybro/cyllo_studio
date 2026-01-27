/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
const { useRef } = owl;
export class StickyNoteCreate extends Component {
    /**
     * @extends Component
    */
    setup() {
        this.orm = useService("orm");
        this.notificationService = useService("notification");
        this.title = useRef("noteTitle")
        this.description = useRef("noteDescription")
        this.pallet = useRef("colorRef")
        this.state = useState({
            note_color : "rgb(255, 230, 110)"
        });
        super.setup(...arguments);
        /**
        * Function executed when the component is mounted.
        */
        onMounted(() => {
            this.title.el.value = this.props.title || '';
            this.description.el.value = this.props.description || '';
            this.pallet.el.value = this.props.colour ||'';
            if (!this.pallet.el.value) {
                this.pallet.el.children[0].classList.add('select')
            }
            else {
                const childrenArray = [...this.pallet.el.children];
                childrenArray.forEach((item) => {
                    if (item.style.backgroundColor == this.pallet.el.value) {
                        item.classList.add('select')
                    }
                });
            }
        });
    }
    click_pallet(ev) {
        // Handles click events on a pallet element and adds or removes the 'select' class for choosing the color
        const childrenArray = [...this.pallet.el.children];
        childrenArray.forEach((item) => {
            if (item.contains(ev.target)) {
                item.classList.add('select');
            }
            if (!item.contains(ev.target)) {
                item.classList.remove('select');
            }
        });
    }
    async _note_save (ev) {
        // saves a note with the provided title and description.
        const childrenArray = [...this.pallet.el.children];
        const selectedColorElement = childrenArray.find(item => item.classList.contains('select'));
        this.state.note_color = String(selectedColorElement.style.backgroundColor);
        // Assuming today is defined as a Date object
        var today = new Date();
        var userTimeZoneOffset = today.getTimezoneOffset();
        var utcTime = today.getTime() + (userTimeZoneOffset * 60 * 1000);
        var userDateTime = new Date(utcTime);
        var userDate = userDateTime.getFullYear() + '-' + (userDateTime.getMonth() + 1) + '-' + userDateTime.getDate();
        var userTime = userDateTime.getHours() + ':' + userDateTime.getMinutes() + ':' + userDateTime.getSeconds();
        var userDateTimeFormatted = userDate + ' ' + userTime;
        const title = this.title.el.value;
        const description = this.description.el.value;
        if (title.trim() === '') {
            this.notificationService.add(
            _t("please add the title to save ..."), { type: "warning" });
            return;
        }
        if (description.trim() === '') {
            this.notificationService.add(_t("please add the description to save ..."),
                { type: "warning" }
            );
            return;
        }
        var args = {
            title: title,
            description: description,
            colour: this.state.note_color,
            create_date : userDateTimeFormatted,
        };
        if (this.props.id) {
            args['id'] = this.props.id
            await this.orm.call("sticky.note", "edit_note", [args]);
            this.env.bus.trigger("note_edit", args)
        }
        else {
            var datas = await this.orm.call("sticky.note","create",[args],);
            args['id'] = datas
            this.env.bus.trigger("note_updates", args);
        }
    }

    async _note_cancel(ev){
        $('.o_button_close').click()
    }
    onKeydown(ev) {
        // Handles the 'keydown' event and triggers a function for saving the note
        if (ev.key === 'Enter') {
            this._note_save();
        }
    }
}
StickyNoteCreate.template = "StickyNotesCreate";