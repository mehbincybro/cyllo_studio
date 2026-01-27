/* @odoo-module */
import {Component, useState, onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {browser} from "@web/core/browser/browser";
import {VoiceRecorder} from "@mail/discuss/voice_message/common/voice_recorder";
import {registry} from "@web/core/registry";

export class VoiceToText extends VoiceRecorder {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    // Add the transcribe functionality in the stop recording function
    stopRecording() {
        this.getMp3()
            .then((buffer) => {
                const file = this._makeFile(buffer, "audio/mp3", "Voice-Recording.mp3");
                // Get the API key from Odoo's ir.config_parameter
                this.orm.call('ir.config_parameter', 'get_param', ['cyllo_voice_to_text_chatter.open_ai_api_key'])
                    .then(open_ai_api_key => {
                        if (open_ai_api_key) {
                            // API URL for the Whisper API
                            const apiUrl = 'https://api.openai.com/v1/audio/translations';
                            const formData = new FormData();
                            formData.append('file', file);  // Add the file
                            formData.append('model', 'whisper-1');  // Specify the model
                            fetch(apiUrl, {
                                method: 'POST',
                                headers: {
                                    'Authorization': `Bearer ${open_ai_api_key}`  // Use the dynamic API key
                                },
                                body: formData  // Send the form data
                            })
                                .then(response => response.json())
                                .then(result => {
                                    // Handle the transcription result
                                    this.insertTranscriptionInComposer(result.text);
                                })
                                .catch(error => console.error('Error:', error));

                            // Clean up any resources or states
                            this.cleanUp();
                        } else {
                            console.error('API key not found');
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching API key:', error);
                    });
            })
            .catch((error) => {
                console.error('Error processing audio buffer:', error);
            });
    }

    insertTranscriptionInComposer(transcribedText) {
        // Find the composer input field in the chatter and set the transcribed text
        const composerInput = document.querySelector('.o-mail-Composer-input');
        const summariseButton = document.querySelector('.summarise-button')
        composerInput.value = transcribedText;  // Set the transcribed text in the input field
        composerInput.dispatchEvent(new Event('input'));  // Trigger an input event to reflect the change
        if (transcribedText.length > 50) {
            summariseButton.classList.remove('d-none'); // Show the summarize button
        } else {
            summariseButton.classList.add('d-none'); // Hide the button
        }
    }
}

VoiceToText.template = "cyllo_voice_to_text_chatter.VoiceToText";
