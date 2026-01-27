/** @odoo-module **/
import { Component, markup } from "@odoo/owl";
import { useService } from '@web/core/utils/hooks';
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { ChatOption } from './chat_option'

/* Create new WhatsappChatHistory by extending Component */
export class WhatsappChatHistory extends Component {
    async setup() {
        this.store = useService("mail.store");
        this.fileViewerInstance = new useFileViewer();
        this.orm = useService('orm')
    }

    getMarkup(text) {
        return markup(text)
    }

    async viewDocument(attachment) {
        let mimetype;
        let type = attachment[1].split('.').pop()
        if (type === 'pdf') {
            mimetype = 'application/pdf';
        } else if (type === 'png') {
            mimetype = 'image/png';
        } else if (type === 'jpeg') {
            mimetype = 'image/jpeg';
        }
        const preview = this.store.Attachment.insert({
            id: attachment[0],
            filename: attachment[1],
            name: attachment[1],
            mimetype: mimetype
        });
        this.fileViewerInstance.open(preview);
    }

    getFileExtension(attachmentName) {
        let extension = attachmentName.split('.').pop()
        let fileType = {
            'docx': 'docx.png',
            'doc': 'doc.png',
            'pdf': 'pdf.png',
            'text': '.png',
            'ppt': 'ppt.png',
            'xls': 'xls.png',
            'xlsx': 'xlsx.png',
            'png': 'png.png',
            'jpeg': 'jpeg.png',
            'mp3': 'mp3.png',
            'mp4': 'mp4.png',
            'zip': 'zip.png'
        }
        return fileType[extension] || '';
    }
}

/* Associate 'WhatsappChatHistory' template with the WhatsappChatHistory component.*/
WhatsappChatHistory.template = 'WhatsappChatHistory';

WhatsappChatHistory.components = {
    ChatOption
}