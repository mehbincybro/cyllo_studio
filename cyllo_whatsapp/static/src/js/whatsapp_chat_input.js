/** @odoo-module **/
import { Component, useRef, useState } from "@odoo/owl";
import { useService } from '@web/core/utils/hooks';
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

/* Create new WhatsappChatInput by extending WhatsappChatInput */
export class WhatsappChatInput extends Component {
    /* This function appears to initialize various properties and set up event listeners.*/
    setup() {
        this.state = useState({
            'recording': 0,
            'mp3File': '',
            'onMic': 0,
            'blob': '',
            'audioFileNumber': 1,
            'audioTrack': '',
            'audioRecorder': '',
            'composer': 0
        })
        this.ui = useState(useService("ui"));
        this.audioPlayer = useRef('audioPlayer');
        this.inputRef = useRef('textarea')
        this.imageInput = useRef('imageInput')
        this.fileInput = useRef('fileInput')
        this.orm = useService('orm')
        this.emojiRef = useRef('emoji-button')
        this.emojiPicker = useEmojiPicker(this.emojiRef, {onSelect: this.emojiSelect.bind(this)})
    }

    /* Click function emoji*/
    emojiSelect(ev) {
        var inputText = this.inputRef.el.value
        var cursorPosition = this.inputRef.el.selectionStart;
        this.inputRef.el.value = inputText.substring(0, cursorPosition) + ev + inputText.substring(cursorPosition)
    }

    /*
    Send button function :  it will create a new record in whatsapp.message model,
    clear input field , and trigger SEND_MESSAGE function using bus
    */
    async sendMessage() {
        this.state.composer = 0
        var messageValues = await this.prepareMessageValues()
        if (messageValues) {
            var currentMessage = await this.orm.call("whatsapp.message", "send_whatsapp_message", [
                messageValues
            ]);
            if (currentMessage) {
                this.env.bus.trigger('SEND_MESSAGE', {message: currentMessage})
                this.env.bus.trigger('UPDATE_COUNTER', {partner: this.props.channel})
            }
        }
    }

    async prepareMessageValues() {
        let imageValues = ''
        let attachment = ''
        let message = this.inputRef.el ? this.inputRef.el.value : ''
        if (this.props.image) {
            let file = this.imageInput.el.files[0];
            imageValues = {
                'imageContent': this.props.image,
                'file_name': file.name,
                'file_type': file.type
            }
            this.imageInput.el.form.reset()
        } else if (this.props.document) {
            if (this.props.attachment) {
                attachment = this.props.attachment
            } else {
                attachment = await this.documentAttachment(this.props.document)
            }
        } else if (this.state.mp3File) {
            attachment = await this.documentAttachment(this.state.blob)
            this.state.mp3File = ''
        }
        let messageValues = {
            'channel': this.props.channel,
            'message': message,
            'image': imageValues,
            'attachment': attachment,
        }
        this.inputRef.el.form.reset()
        return messageValues
    }

    /** function for the enter key to send messages*/
    keyEnter(event) {
    }

    /**
     * Create an attachment record from a document file.
     *
     * @param {File} document - The document file to create an attachment from.
     * @returns {Promise} A promise that resolves to the created attachment record.
     */
    async documentAttachment(document) {
        const content = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.readAsDataURL(document);
            reader.onload = () => {
                resolve(reader.result);
            };
        });
        let base64content = content.split(',')
        let documentName = document.name
        if (document.type === 'audio/opus') {
            const audPrefix = 'AUD'
            documentName = audPrefix + this.state.audioFileNumber
            this.state.audioFileNumber += 1
        }

        let AttachmentValues = {
            name: documentName,
            mimetype: document.type,
            datas: base64content[1],
        }
        return this.orm.create("ir.attachment", [AttachmentValues], {});
    }

    /** Trigger an event to request image preview **/
    async viewImagePreview() {
        this.state.composer = 1
        let image = this.imageInput.el.files[0];
        this.env.bus.trigger('PREVIEW_IMAGE', {imageFile: image})
    }

    /** Trigger an event to request document preview **/
    async viewFilePreview() {
        let file = this.fileInput.el.files[0];
        this.state.composer = 1
        this.env.bus.trigger('PREVIEW_DOCUMENT', {documentFile: file})
    }

    /** Click function of mic to record the voice **/
    async onClickVoice() {
        let chunks = []
        this.state.recording = 1
        if (this.state.audioRecorder && this.state.audioRecorder.state === "recording") {
            this.state.audioRecorder.stop();
            this.state.onMic = 0
            this.state.audioTrack.getAudioTracks()[0].stop();
        } else {
            this.state.onMic = 1
            const audioStream = await navigator.mediaDevices.getUserMedia({audio: true});
            this.state.audioTrack = audioStream;
            this.state.audioRecorder = new MediaRecorder(audioStream);
            this.state.audioRecorder.start();
        }
        this.state.audioRecorder.ondataavailable = (e) => {
            chunks.push(e.data);
        };
        this.state.audioRecorder.onstop = async () => {
            this.state.blob = await new Blob(chunks, {type: "audio/opus"});
            this.audioPlayer.el.src = URL.createObjectURL(this.state.blob);
        }
    }

    async sendVoiceMessage() {
        this.state.recording = 0
        this.state.onMic = 0
        this.state.mp3File = await new File([this.state.blob], 'audio-file.opus', {type: 'audio/opus'});
        await this.sendMessage();
    }

    deleteAudio() {
        this.audioPlayer.el.src = ' '
        this.state.recording = 0
    }

    get voiceInputProps() {
        return {
            deleteAudio: this.deleteAudio.bind(this),
            sendVoiceMessage: this.sendVoiceMessage.bind(this),
            onClickMic: this.onClickVoice.bind(this),
            onMic: this.state.onMic
        }
    }

    composeMessage(ev) {
        if (ev.key === "Enter") {
            this.sendMessage()
        }
        if (this.inputRef.el.value) {
            this.state.composer = 1;
        } else {
            this.state.composer = 0;
        }
    }
}

/* Associate 'WhatsappChatInput' template with the WhatsappChatInput component.*/
WhatsappChatInput.template = 'WhatsappChatInput';