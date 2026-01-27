/** @odoo-module **/
import {Component, markup, onMounted, onWillStart, useRef, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {GraphTile} from "@cyllo_analytics/js/presentation/components/graph_tile";
import {ThemeMaker} from "../theme_maker";
import {SelectUser} from "./components/select_user";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";

/**
 * Converts a data URL to a Blob.
 *
 * @param {string} data - The data URL to be converted.
 * @param {string} type - The MIME type of the data.
 * @returns {Blob} A Blob representing the converted data.
 */
function dataUrlToBlob(data, type) {
    const binData = window.atob(data);
    const uiArr = new Uint8Array(binData.length);
    uiArr.forEach((_, index) => (uiArr[index] = binData.charCodeAt(index)));
    return new Blob([uiArr], {type});
}

function htmlToText(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return doc.body.textContent || "";
}

/**
 * @class
 * @extends {Component}
 */
export class ExplainAIModal extends Component {
    setup() {
        this.dialogService = useService("dialog")
        this.actionService = useService("action")
        this.orm = useService("orm")
        this.rpc = useService("rpc")
        this.rootRef = useRef("root")
        this.messageRef = useRef("message")
        this.threadService = useService("mail.thread");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.state = useState({imgSrc: "", name: "", explanation: "Loading....!!!", error: true, data: false, apiError: false})
        var theme_maker = new ThemeMaker(this.props.theme)
        theme_maker.getTheme()
        onWillStart(async () => {
            const {query} = this.props.options
            this.state.data = await this.orm.call("dashboard.config", "sql_execute", [query])
        })
        onMounted(async () => {
            this.state.explanation = await this.explainWithAi()
        })
    }
    goToSettings() {
        this.actionService.doAction({
            name: _t("Settings"),
            type: "ir.actions.act_window",
            res_model: "res.config.settings",
            views: [[false, "form"]],
            view_mode: "form",
            target: "main",
            context: {
                module: 'cyllo_analytics_settings'
            },
        })
        this.dismiss()
    }
    get chartProps() {
        const {options} = this.props
        return {
            data: this.state.data,
            name: options.name || '',
            measures: eval(options.measure),
            dimension: options.dimension, // TODO: Test with gpt generated dimension
            dimension_axis: options.dimension_axis,
            type: options.type,
        }
    }

    async _sendMessage(userId) {
        const thread = await this.threadService.getChat({userId})
        const postData = {...this.postData}
        const attachment = await this.uploadData(thread)
        if (attachment.id) {
            postData.attachments = [{...attachment}]
        }
        const text = htmlToText(this.explain);
        await this.threadService.post(thread, text, postData)
    }

    dismiss() {
        this.props.close();
    }

    getImageFile() {
        const name = this.state.name;
        const data = this.state.imgSrc.split(",")[1];
        const type = 'image/png'
        return new File([dataUrlToBlob(data, type)], name, {type});
    }

    async uploadData(thread) {
        return await this.attachmentUploadService.uploadFile({thread}, this.getImageFile())
    }

    async handleSendToUser(event) {
        const {currentValue} = event
        currentValue.map(async (user) => await this._sendMessage(user[0]))
    }

    get postData() {
        return {
            attachments: [],
            isNote: false,
            mentionedChannels: [],
            mentionedPartners: [],
            cannedResponseIds: [],
            parentId: null,
        }
    }

    setImage(imgSrc, name) {
        this.state.imgSrc = imgSrc;
        this.state.name = name;
    }

    get explain() {
        return this.state.explanation
    }

    shareToUser() {
        if (this.state.error) return;
        this.dialogService.add(SelectUser, {
            handleSendToUser: this.handleSendToUser.bind(this)
        })
    }

    parseExplain(explanation) {
        const md = window.markdownit();
        const parsedHTML = md.render(explanation);
        return markup(parsedHTML);
    }

    async explainWithAi(retry = false) {
        const {data} = this.props.options
        const [error, apiError ,explanation] = await this.orm.call("dashboard.sheet", "explain_with_ai", [this.state.data, retry])
        this.state.error = error
        this.state.apiError = apiError
        return this.parseExplain(explanation)
    }

    async retry() {
        if (this.state.error) return;
        this.state.explanation = await this.explainWithAi(true)
    }

    showActionMessage(message) {
        var messageContainer = this.messageRef.el.querySelector("#messageContainer");
        messageContainer.innerText = message;
        messageContainer.classList.add("show");
        setTimeout(function () {
            messageContainer.classList.remove("show");
        }, 1000);
    }

    async copyToClip() {
        if (this.state.error) return;
        const message = "Copied to Clipboard!"
        this.showActionMessage(message)
        var textArea = document.createElement("textarea");
        textArea.value = htmlToText(this.explain);
        document.body.appendChild(textArea);
        textArea.select();
        var successful = document.execCommand('copy');
        document.body.removeChild(textArea)
        return successful;
    }

    download() {
        if (this.state.error) return;
        var pdf = new jsPDF('l', 'mm', 'a3');
        html2canvas(this.rootRef.el).then(async (canvas) => {
            var imgData = canvas.toDataURL('image/png');
            var pageWidth = pdf.internal.pageSize.getWidth();
            var pageHeight = pdf.internal.pageSize.getHeight();
            var imageWidth = pageWidth - 25;
            var imageHeight = (imageWidth / canvas.width) * canvas.height;
            var offsetX = 15;
            var offsetY = 40
            pdf.setFont("helvetica");
            pdf.setFontType("bold");
            pdf.setFontSize(14);
            pdf.text(`${this.state.name || ''}`, 140, 20);
            pdf.addImage(imgData, 'PNG', offsetX, offsetY, imageWidth, imageHeight);
            pdf.save(`${this.state.name}.pdf`);
            this.showActionMessage("Downloaded")
        });
    }

    get style() {
        return {
            height: `55vh;`,
            width: `100%;`,
        }
    }

    static props = {
        close: {type: Function, optional: false},
        currentTheme: {type: String, optional: true},
        options: {type: Object, optional: false},
        theme: {type: Object, optional: false},
    }
}

ExplainAIModal.template = "ExplainAIModal";
ExplainAIModal.components = {
    Dialog, GraphTile
}
