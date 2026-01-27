/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import {Composer} from "@mail/core/common/composer";
import {VoiceToText} from "./voice_to_text";
import {VoiceRecorder} from "@mail/discuss/voice_message/common/voice_recorder";
import {useService} from '@web/core/utils/hooks';
import {useState} from "@odoo/owl";
// Patch the Composer to add recording and transcribe functionality
patch(Composer.prototype, {
    async setup() {
        super.setup();
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({
            active: true,
            is_voice_chat: false,  // Default to false initially
        });
        var is_voice_chat = await this.orm.call('ir.config_parameter', 'get_param', ['cyllo_voice_to_text_chatter.is_voice_chat'])
        this.state.is_voice_chat = is_voice_chat === 'True';  // Check if the setting is enabled
    },
    async summariseText() {
        var transcribed_text = this.props.composer.textInputContent
        let summarised_text = await this.rpc("/cyllo_studio/summarise/text", {transcribed_text: transcribed_text});
        const composerInput = document.querySelector('.o-mail-Composer-input');
        const summariseButton = document.querySelector('.summarise-button')
        composerInput.value = summarised_text.content;  // Set the transcribed text in the input field
        composerInput.dispatchEvent(new Event('input'));  // Trigger an input event to reflect the change
        summariseButton.classList.add('d-none'); // Hide the summarize button
    }
});
Composer.components = {
    ...Composer.components, VoiceToText, VoiceRecorder
}
