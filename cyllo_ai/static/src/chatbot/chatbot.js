/** @odoo-module **/
import { Component, useState, markup, useRef, onMounted, onWillUnmount, onPatched, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { ChatUser } from "../chatuser/chatuser";
import { ChatResponse } from "../chatresponse/chatresponse";
import { ChatSidebar } from "../chatsidebar/chatsidebar";
import { LottieAnimation } from "@cyllo_web/js/popups/lottie/lottie";


export class ChatBot extends Component {
    static props = {
        isChatOpen: { type: Boolean, optional: true, default: false },
    };

    setup() {
        super.setup(...arguments);
        this.user = useService("user");
        this.orm = useService("orm");
        this.company = useService("company");
        this.inputWrapper = useRef('input-wrapper');
        this.busService = this.env.services.bus_service;
        this.upperScroll = useRef('upperScroll')
        const { origin } = browser.location;
        const { userId } = this.user;
        this.childChartApis = {};
        this.isDestroyed = false;
        this.state = useState({
            messages: [],
            chatOn: false,
            inputText: "",
            isTyping: false,
            minimized: true,
            user_image: `${origin}/web/image?model=res.users&field=avatar_128&id=${userId}`,
            isDragging: false,
            interrupted: false,
            dragStyle: "bottom: 20px;",
            session_id: "",
            chartNeedsRefresh: false,
            isRecording: false,
            isProcessingVoice: false,
            convertVoice: false,
            recordingStart: 0,
            recordingElapsed: 0,
            recordingDisplay: "00:00",
            sessions: [],
            sessionsLoading: false,
            historyOpen: false,
        })
        this.rpc = useService("rpc");
        this.chartDiv = useRef('echart')
        this.chatbotDiv = useRef("chatbotDiv")
        this.messageContainerRef = useRef("messageContainer");
        this.inputWrapper = useRef('input-wrapper')
        this.onInterruptResponse = this.onInterruptResponse.bind(this);
        this.onMessageBound = this.onMessage.bind(this);

        this.sessionRT = reactive({
            typing: {},          // { [sessionId]: boolean }
            pendingReq: {},      // { [sessionId]: requestId }
            pendingMsgs: {},     // { [sessionId]: Array<pendingMsg> }
        });

        // Initialize session BEFORE onWillStart - now tracking active company IDs
        this.lastActiveCompanyIds = this._getActiveCompanyIds();
        this._initSessionForCompanies();

        onWillStart(async () => {
            this.busService.addChannel("cyllo_channel");
            this.channel = "your_channel"
            this.busService.addChannel(this.channel)
            this.busService.addEventListener("notification", this.onMessageBound)
            if (this.isDestroyed || this.__owl__?.status === 3) return;
            let configValue = null
            let cyllo_ai_widget = null
            try {
                configValue = await this.rpc('/cyllo/get_agent_enabled');
                cyllo_ai_widget = await this.rpc('/cyllo/get_ai_widget_enabled');
                if (!this.isDestroyed) {
                    this.state.config = configValue;
                }
            } catch (err) {
                console.error("Error fetching config", err);
            }
            if (cyllo_ai_widget === '1' && configValue == 'True') {
                this.state.chatOn = true
            }
            else if (cyllo_ai_widget === "0" || !configValue) {
                this.state.chatOn = false
            }
            const companyIds = this._getActiveCompanyIds();
            const history = await this.rpc("/chatbot/get_conversation", {
                session_id: this.state.session_id,
                company_ids: companyIds
            });

            this.state.messages = (history || []).map((msg, index) => {
                let htmlContent = "";
                if (msg.from === "bot") {
                    htmlContent = msg.text
                        ? markup(this.parseMarkdown(msg.text))
                        : (msg.html || "");
                } else {
                    htmlContent = msg.text
                        ? markup(this.parseMarkdown(msg.text)) : (msg.html || "");
                }
                const safeId = msg.id ? msg.id : `temp_${msg.timestamp || Date.now()}_${index}`;
                return {
                    id: safeId,
                    from: msg.from,
                    html: htmlContent,
                    text: msg.text,
                    chart_config: msg.chart_config || null,
                    interrupted: msg.interrupted,
                    timestamp: msg.timestamp,
                };
            });
        });
        onWillUpdateProps((nextProps) => {
            // Check if chart_config has changed
            if (JSON.stringify(nextProps.chart_config) !== JSON.stringify(this.props.chart_config)) {
                this.baseChartConfig = nextProps.chart_config ? JSON.parse(JSON.stringify(nextProps.chart_config)) : null;
                this.state.chart_config = this.baseChartConfig;
                setTimeout(() => {
                    this.initChart();
                }, 0);
            }
        });
        onMounted(() => {
            window.addEventListener('keydown', this.onKeyDown.bind(this));
            document.addEventListener("mousedown", this.handleClickOutside.bind(this));
            this.scrollToBottom();
        });
        onWillUnmount(() => {
            window.removeEventListener('keydown', this.onKeyDown);
            document.removeEventListener("mousedown", this.handleClickOutside);
            this.busService.removeEventListener("notification", this.onMessageBound);
            this.isDestroyed = true;
        });
        onPatched(() => {
            this.scrollToBottom();
            if (this.state.chartNeedsRefresh) {
                this.refreshCharts();
                this.state.chartNeedsRefresh = false;
            }

            // Check if active company selection has changed
            const currentActiveIds = this._getActiveCompanyIds();
            if (!this._areCompanyIdsEqual(currentActiveIds, this.lastActiveCompanyIds)) {
                this.lastActiveCompanyIds = currentActiveIds;
                const newSession = this._initSessionForCompanies();
                this.loadSession(newSession);
                this.env.bus.trigger('LOAD_SIDEBAR', {});
            }
        });
    }

    // Helper to get active company IDs
    _getActiveCompanyIds() {
        return this.company?.activeCompanyIds || [];
    }

    // Helper to compare two arrays of company IDs
    _areCompanyIdsEqual(arr1, arr2) {
        if (arr1.length !== arr2.length) return false;
        const sorted1 = [...arr1].sort((a, b) => a - b);
        const sorted2 = [...arr2].sort((a, b) => a - b);
        return sorted1.every((val, index) => val === sorted2[index]);
    }

    // Generate storage key based on active company IDs
    _sessionStorageKey(companyIds) {
        // Create a consistent key from sorted company IDs
        const sortedIds = [...companyIds].sort((a, b) => a - b);
        const idsKey = sortedIds.length > 0 ? sortedIds.join('_') : 'no_company';
        return `chat_session_id_${idsKey}`;
    }

    // Initialize session for the current set of active companies
    _initSessionForCompanies() {
        const companyIds = this._getActiveCompanyIds();
        const key = this._sessionStorageKey(companyIds);
        let sessionId = localStorage.getItem(key);

        if (!sessionId) {
            const rand = crypto.randomUUID?.() || Math.random().toString(36).slice(2);
            // Include company IDs in session ID for clarity
            const idsStr = companyIds.length > 0 ? companyIds.sort((a, b) => a - b).join('_') : 'none';
            sessionId = `${idsStr}_${rand}`;
            localStorage.setItem(key, sessionId);
        }

        this.state.session_id = sessionId;
        return sessionId;
    }

    handleClickOutside(ev) {
        const chatbotEl = this.chatbotDiv.el;
        const sidebarEl = document.querySelector('.chatbot-history-sidebar');
        if (sidebarEl && sidebarEl.contains(ev.target)) {
            return;
        }
        if (chatbotEl && !chatbotEl.contains(ev.target) && chatbotEl.querySelector('.chatbot-box')) {
            this._minimize_chatbot();
        }
    }

    async onMessage({ detail: notifications }) {
        notifications = notifications.filter(item => item.payload.channel === this.channel)
        let configValue = null
        try {
            configValue = await this.rpc('/cyllo/get_agent_enabled');
        } catch (err) {
            console.error("RPC failed (probably destroyed during call):", err);
            return;
        }
        let chatStatus = notifications[0]?.payload?.chat_on;
        if (chatStatus !== undefined) {
            if (chatStatus && configValue == 'True') {
                this.state.chatOn = true
            }
            else if (!chatStatus || !configValue) {
                this.state.chatOn = false
            }
        }
    }

    registerChartApi(index, api) {
        this.childChartApis[index] = api;
    }
    refreshCharts() {
        for (const index in this.childChartApis) {
            const api = this.childChartApis[index];
            if (api && typeof api.resizeChart === 'function') {
                api.resizeChart();
            }
        }
    }

    scrollToBottom() {
        const el = this.upperScroll?.el || this.messageContainerRef?.el;
        if (!el) return;
        requestAnimationFrame(() => {
            el.scrollTop = el.scrollHeight;
        });
    }

    startDrag(ev) {
        if (this.state.minimized) return;
        this.state.isDragging = true;
        this.state.dragStartX = ev.clientX;
        this.state.dragStartY = ev.clientY;
    }

    parseMarkdown(text) {
        if (typeof text !== 'string') return "";
        return window.marked.parse(text);
    }

    async _close_chatbot() {
        this.env.chatbotClose()
    }

    async _minimize_chatbot() {
        this.state.isDragging = false;
        this.state.minimized = true;
        this.state.historyOpen = false;
    }

    async _maximize_chatbot() {
        this.state.minimized = true;
        await new Promise(requestAnimationFrame);
        this.state.minimized = false;
        await new Promise(requestAnimationFrame);
        setTimeout(() => {
            this.state.chartNeedsRefresh = true;
            const textarea = this.inputWrapper?.el?.querySelector('textarea');
            if (textarea) {
                textarea.focus();
            }
        }, 500);
    }

    onKeyDown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            if (this.state.isTyping) return;
            this.handleSend();
        }
    }

    autoResize(ev) {
        const textarea = ev.target;
        textarea.style.height = "auto"
        textarea.style.height = textarea.scrollHeight + "px";
    }

    async handleSend(value = null) {
        this.pendingRequestBySession = this.pendingRequestBySession || {};
        this.typingBySession = this.typingBySession || {};
        this.pendingMessagesBySession = this.pendingMessagesBySession || {};

        const text = typeof value === "string" ? value : this.state.inputText.trim();
        if (!text) return;

        const __sessionId = this.state.session_id;
        const __requestId = (crypto.randomUUID?.() || Math.random().toString(36).slice(2));
        this.pendingRequestBySession[__sessionId] = __requestId;

        const companyIds = this._getActiveCompanyIds();

        const __tempId = 'pending_' + Date.now() + '_' + Math.random().toString(36).slice(2);
        const pendingMsg = { id: __tempId, from: "user", text };

        this.state.messages.push(pendingMsg);
        this.pendingMessagesBySession[__sessionId] = this.pendingMessagesBySession[__sessionId] || [];
        this.pendingMessagesBySession[__sessionId].push(pendingMsg);

        this.state.inputText = "";
        this.typingBySession[__sessionId] = true;
        if (this.state.session_id === __sessionId) {
            this.state.isTyping = true;
        }

        this.render();
        this.resetInputHeight();
        this.scrollToBottom();
        try {
            const { userId } = this.user;
            const interrupted = this.state.interrupted;
            const session_id = __sessionId;

            const response = await this.rpc("/chatbot/query", { text, userId, interrupted, session_id, company_ids: companyIds });
            let raw = response.last_message;
            let isInterrupted = false;

            if (response.response !== 'none') {
                isInterrupted = true;
                raw = response.response;
            }

            let parsed = null;
            const tryExtractJSON = (s) => {
                if (typeof s !== 'string') return null;
                let t = s.trim();
                t = t.replace(/^`{3}\s*json?\s*/i, '').replace(/`{3}\s*$/i, '').trim();
                t = t.replace(/^`+/, '').replace(/`+$/, '').trim();
                const first = t.indexOf('{');
                const last = t.lastIndexOf('}');
                if (first !== -1 && last !== -1 && last > first) {
                    t = t.slice(first, last + 1);
                }
                try {
                    return JSON.parse(t);
                } catch (_) {
                    return null;
                }
            };

            parsed = tryExtractJSON(raw);
            if (!parsed && typeof raw === 'string') {
                const contentMatch = raw.match(/content=["']([\s\S]*?)["']/);
                if (contentMatch) {
                    parsed = tryExtractJSON(contentMatch[1]);
                }
            }
            if (!parsed && typeof raw === 'string' && raw.includes('{') && raw.includes('}')) {
                const first = raw.indexOf('{');
                const last = raw.lastIndexOf('}');
                if (first !== -1 && last !== -1 && last > first) {
                    try { parsed = JSON.parse(raw.slice(first, last + 1)); } catch (_) { }
                }
            }
            if (!parsed && typeof raw === 'string') {
                try {
                    const once = JSON.parse(raw);
                    if (once && typeof once === 'object' && once.text) {
                        parsed = once;
                    } else if (typeof once === 'string') {
                        try {
                            const twice = JSON.parse(once);
                            if (twice && typeof twice === 'object' && twice.text) {
                                parsed = twice;
                            }
                        } catch (_) { }
                    }
                } catch (_) { }
            }
            if (!parsed && typeof raw === 'string') {
                const m = raw.match(/"text"\s*:\s*"([\s\S]*?)"/);
                if (m) {
                    parsed = { text: m[1] };
                }
            }

            if (!parsed && !this.__loggedParseWarn) {
                this.__loggedParseWarn = true;
            }

            let botMessage;
            if (parsed && parsed.text) {
                if (parsed?.chart_config?.series?.[0]?.data?.length === 1) {
                    parsed.chart_config = null;
                }
                const textWithNewlines = String(parsed.text).replace(/\\n/g, '\n');

                botMessage = {
                    from: "bot",
                    html: markup(this.parseMarkdown(textWithNewlines)),
                    chart_config: parsed.chart_config || null,
                    interrupted: isInterrupted,
                };
            } else {
                const textWithNewlines = typeof raw === 'string' ? raw.replace(/\\n/g, '\n') : (raw || '');
                botMessage = {
                    from: "bot",
                    html: markup(this.parseMarkdown(textWithNewlines)),
                    chart_config: null,
                    interrupted: isInterrupted,
                };
            }

            // --- Persist conversation ---
            const record = await this.rpc("/chatbot/set_conversation", {
                user_id: this.user.userId,
                session_id: session_id || null,
                user_message: text || null,
                response_message: isInterrupted ? raw : (parsed?.text ?? raw),
                chart_config: parsed?.chart_config ?? null,
                interrupted: isInterrupted,
                company_ids: companyIds,  // Changed from company_id to company_ids
            });

            botMessage.id = record.id;

            if (this.pendingMessagesBySession[__sessionId]) {
                this.pendingMessagesBySession[__sessionId] =
                    this.pendingMessagesBySession[__sessionId].filter(m => m.id !== __tempId);
            }

            if (this.pendingRequestBySession[__sessionId] === __requestId && this.state.session_id === __sessionId) {
                this.state.messages.push(botMessage);
                this.state.interrupted = isInterrupted;
            }

            if (this.pendingRequestBySession[__sessionId] === __requestId) {
                delete this.pendingRequestBySession[__sessionId];
            }

        } catch (err) {
            console.error('Error in handleSend:', err);
            if (this.state.session_id === __sessionId) {
                this.state.messages.push({
                    from: "bot",
                    html: "⚠️ Something went wrong while processing your request.",
                    chart_config: null,
                });
            }

            if (this.pendingMessagesBySession[__sessionId]) {
                this.pendingMessagesBySession[__sessionId] =
                    this.pendingMessagesBySession[__sessionId].filter(m => m.id !== __tempId);
            }
        } finally {
            this.typingBySession[__sessionId] = false;
            if (this.state.session_id === __sessionId) {
                this.state.isTyping = false;
                this.render();
            }
        }

        this.env.bus.trigger('LOAD_SIDEBAR', {});
    }

    resetInputHeight() {
        const textarea = this.inputWrapper.el.querySelector('textarea');
        textarea.style.height = "24px";
    }

    resetChat() {
        this.state.messages = [];
        this.state.inputText = "";
        const companyIds = this._getActiveCompanyIds();
        const rand = crypto.randomUUID?.() || Math.random().toString(36).slice(2);
        const idsStr = companyIds.length > 0 ? companyIds.sort((a, b) => a - b).join('_') : 'none';
        const newId = `${idsStr}_${rand}`;
        this.state.session_id = newId;
        localStorage.setItem(this._sessionStorageKey(companyIds), newId);
        this.childChartApis = {};
    }

    handleQuickAction = (text) => {
        this.state.inputText = text;
    };

    async onInterruptResponse(event) {
        let messageToUpdate = null
        for (let i = this.state.messages.length - 1; i >= 0; i--) {
            const msg = this.state.messages[i];
            if (msg.from === "bot" && msg.interrupted) {
                messageToUpdate = msg;
                msg.interrupted = false;
                break;
            }
        }
        if (messageToUpdate && messageToUpdate.id) {
            await this.orm.write(
                'chatbot.history',
                [messageToUpdate.id],
                { interrupted: false }
            );
        }
        this.handleSend(event);
    }
    async recordVoice() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.state.isRecording = true
            this.state.recordingStart = Date.now();
            this.state.recordingElapsed = 0;
            this.state.recordingDisplay = "00:00";
            this.recordingTimer = setInterval(() => {
                const seconds = Math.floor((Date.now() - this.state.recordingStart) / 1000);
                this.state.recordingElapsed = seconds;
                const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
                const ss = String(seconds % 60).padStart(2, '0');
                this.state.recordingDisplay = `${mm}:${ss}`;
                this.render();
            }, 1000);
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                this.state.isProcessingVoice = true;
                this.stream.getTracks().forEach(track => track.stop());
                this.state.convertVoice = true
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                const encoded_audio = await this.blobToBase64(audioBlob);
                const audioConvertion = await this.rpc("/cyllo/speech_to_text", {
                    encoded_audio: encoded_audio,
                });
                this.state.inputText = "";
                this.state.inputText = audioConvertion;
                this.state.convertVoice = false
                this.state.isProcessingVoice = false
                setTimeout(() => {
                    const textarea = this.inputWrapper.el.querySelector('textarea');
                    textarea.style.height = "auto";
                    textarea.style.height = `${textarea.scrollHeight}px`;
                }, 5);
            };
            this.mediaRecorder.start();
        } catch (err) {
            console.error('Error recording audio:', err);
        }
    }

    async stopRecording() {
        if (this.state.isRecording && this.mediaRecorder) {
            this.mediaRecorder.stop();
            this.state.isRecording = false;
            if (this.recordingTimer) {
                clearInterval(this.recordingTimer);
                this.recordingTimer = null;
            }
        }
    }
    blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64String = reader.result.split(',')[1];
                resolve(base64String);
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
    cancelRecording() {
        if (this.state.isRecording && this.mediaRecorder) {
            this.mediaRecorder.ondataavailable = null;
            this.mediaRecorder.onstop = null;

            if (this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            this.audioChunks = [];
            this.state.isRecording = false;
            if (this.recordingTimer) {
                clearInterval(this.recordingTimer);
                this.recordingTimer = null;
            }
            this.state.recordingStart = 0;
            this.state.recordingElapsed = 0;
            this.state.recordingDisplay = "00:00";
            this.mediaRecorder = null;
            this.stream = null;
        }
    }

    async loadSession(sessionId) {
        const companyIds = this._getActiveCompanyIds();
        const history = await this.rpc("/chatbot/get_conversation", {
            session_id: sessionId,
            company_ids: companyIds
        });

        this.state.session_id = sessionId;
        localStorage.setItem(this._sessionStorageKey(companyIds), sessionId);

        // ADDED 'index' argument here
        this.state.messages = (history || []).map((msg, index) => {

            // ADDED Safe ID Generation (crucial for t-key="msg.id")
            // If msg.id is null, we create a unique one using the session + index
            const safeId = msg.id
                ? msg.id
                : `${sessionId}_temp_${msg.timestamp || Date.now()}_${index}`;

            let htmlContent = "";
            if (msg.from === "bot") {
                htmlContent = msg.text ? markup(this.parseMarkdown(msg.text)) : (msg.html || "");
            } else {
                htmlContent = msg.text ? markup(this.parseMarkdown(msg.text)) : (msg.html || "");
            }
            return {
                id: safeId, //  Use the safeId
                from: msg.from,
                html: htmlContent,
                text: msg.text,
                chart_config: msg.chart_config || null,
                interrupted: msg.interrupted,
                timestamp: msg.timestamp,
            };
        });

        const pending = this.pendingMessagesBySession?.[sessionId] || [];
        if (pending.length) {
            this.state.messages = [...this.state.messages, ...pending];
        }
        this.state.isTyping = !!this.typingBySession?.[sessionId];
        this.scrollToBottom();
    }

    onSelectSession = (s) => {
        if (s && s.session_id) {
            this.loadSession(s.session_id);
            this.state.historyOpen = false;
            this._maximize_chatbot();
        }
    };

    toggleHistory() {
        this.state.historyOpen = !this.state.historyOpen;
    }

}
ChatBot.template = "ChatBot";
ChatBot.components = {
    ChatUser,
    ChatResponse,
    ChatSidebar,
    LottieAnimation
};