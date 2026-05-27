/** @odoo-module */
const { useState } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";

export class WebhookNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();

        // ── UNCHANGED: original default initialisers ──────────────────────
        if (!this.fieldState.webhook_method) {
            this.fieldState.webhook_method = { value: 'POST' };
        }
        if (!this.fieldState.webhook_headers) {
            this.fieldState.webhook_headers = { value: '{"Content-Type": "application/json"}' };
        }

        // ── UI-ONLY: local reactive state for the header key/value builder
        //    and payload token helper. Nothing here touches fieldState or
        //    generateCode() — it only drives the visual panel.
        this.uiState = useState({
            // Header builder rows — purely visual, syncs TO fieldState.webhook_headers
            headerRows: this._parseHeadersToRows(this.fieldState.webhook_headers),
            headerBuilderOpen: false,

            // Custom payload form state
            showCustomPayloadForm: false,
            customPayloadKey: '',
            customPayloadValue: '',

            // Copy-to-clipboard feedback
            urlCopied: false,
        });
    }

    // ════════════════════════════════════════════════════════════════════════
    // ORIGINAL METHODS — UNTOUCHED
    // ════════════════════════════════════════════════════════════════════════

    get getMethodOptions() {
        return [
            { label: 'POST',   value: 'POST'   },
            { label: 'GET',    value: 'GET'    },
            { label: 'PUT',    value: 'PUT'    },
            { label: 'DELETE', value: 'DELETE' },
        ];
    }

    get getLabel() {
        return this.fieldState.label || "";
    }

    setLabel(label) {
        this.fieldState.label = label;
        const nodeId = this.props.id;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId });
    }

    /**
     * generateCode() — COMPLETELY UNCHANGED FROM ORIGINAL.
     * Reads webhook_url, webhook_method, webhook_headers, webhook_payload
     * from fieldState exactly as before.
     */
    generateCode() {
        const url = this.fieldState.webhook_url || "";
        const method = this.fieldState.webhook_method || "POST";
        const headers = this.fieldState.webhook_headers || '{"Content-Type": "application/json"}';
        const payload = this.fieldState.webhook_payload || "";

        // Escape JSON curly braces for Python's f-string parsing,
        // while preserving dynamic placeholders containing 'record.'
        let escapedPayload = payload.replace(/\{/g, '{{').replace(/\}/g, '}}');
        // Convert {{{{current_record.field}}}} back to {record.field} for python f-string
        escapedPayload = escapedPayload.replace(/\{\{\{\{(?:current_)?record\.([a-zA-Z0-9_.]+)\}\}\}\}/g, '{record.$1}');

        let code = ``;
        code += `url = f"${url}"\n`;
        code += `headers = ${headers}\n`;
        code += `payload = f"""${escapedPayload}"""\n`;
        code += `\n`;
        code += `try:\n`;
        code += `    if "${method}" == "GET":\n`;
        code += `        response = requests.get(url, headers=headers)\n`;
        code += `    elif "${method}" == "POST":\n`;
        code += `        response = requests.post(url, headers=headers, data=payload.encode('utf-8'))\n`;
        code += `    elif "${method}" == "PUT":\n`;
        code += `        response = requests.put(url, headers=headers, data=payload.encode('utf-8'))\n`;
        code += `    elif "${method}" == "DELETE":\n`;
        code += `        response = requests.delete(url, headers=headers)\n`;
        code += `    response.raise_for_status()\n`;
        code += `    _logger.info("Webhook success: %s %s -> %s", "", url, response.status_code)\n`;
        code += `except Exception as e:\n`;
        code += `    _logger.error("Webhook failed: %s %s -> %s", "", url, str(e))\n`;
        code += `    raise UserError(f"Webhook Execution Failed: {str(e)}")\n`;

        return code;
    }

    /**
     * validateForm() — COMPLETELY UNCHANGED FROM ORIGINAL.
     */
    validateForm() {
        const { webhook_url, webhook_method, label } = this.fieldState;
        const errors = {};
        if (!label)         errors.label         = "Label must be non-empty.";
        if (!webhook_url)   errors.webhook_url   = "URL is required.";
        if (!webhook_method) errors.webhook_method = "Method is required.";
        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }
        return { isValid: true };
    }

    // ════════════════════════════════════════════════════════════════════════
    // UI-ONLY HELPERS  —  read/write fieldState.webhook_headers and
    //                      fieldState.webhook_payload only through the
    //                      same string format the original code always used.
    //                      generateCode() still sees identical strings.
    // ════════════════════════════════════════════════════════════════════════

    // ── Method badge colour ──────────────────────────────────────────────
    get methodBadgeStyle() {
        const colours = {
            POST:   'background:#198754;color:#fff',
            GET:    'background:#0d6efd;color:#fff',
            PUT:    'background:#fd7e14;color:#fff',
            DELETE: 'background:#dc3545;color:#fff',
        };
        return colours[this.fieldState.webhook_method] || 'background:#6c757d;color:#fff';
    }

    // ── URL copy helper ──────────────────────────────────────────────────
    copyUrl() {
        const url = this.fieldState.webhook_url || '';
        if (!url) return;
        navigator.clipboard.writeText(url).then(() => {
            this.uiState.urlCopied = true;
            setTimeout(() => { this.uiState.urlCopied = false; }, 1800);
        });
    }

    // ── Header key/value builder ─────────────────────────────────────────
    /**
     * Parse the raw JSON header string into [{key, value}] rows for the
     * visual builder. If parsing fails, returns empty rows — the raw
     * string in fieldState is always preserved as-is.
     */
    _parseHeadersToRows(raw) {
        try {
            const obj = JSON.parse(raw || '{}');
            return Object.entries(obj).map(([key, value]) => ({ key, value }));
        } catch {
            return [];
        }
    }

    /**
     * Serialise the header rows back into a JSON string and write it
     * into fieldState.webhook_headers — the same field generateCode()
     * already reads. No new field, no schema change.
     */
    _syncHeadersToFieldState() {
        const obj = {};
        for (const row of this.uiState.headerRows) {
            if (row.key.trim()) obj[row.key.trim()] = row.value;
        }
        this.fieldState.webhook_headers = JSON.stringify(obj, null, 2);
    }

    toggleHeaderBuilder() {
        this.uiState.headerBuilderOpen = !this.uiState.headerBuilderOpen;
        if (this.uiState.headerBuilderOpen) {
            // Refresh rows from current fieldState each time panel opens
            this.uiState.headerRows = this._parseHeadersToRows(
                this.fieldState.webhook_headers
            );
        }
    }

    addHeaderRow() {
        this.uiState.headerRows = [...this.uiState.headerRows, { key: '', value: '' }];
    }

    removeHeaderRow(idx) {
        this.uiState.headerRows = this.uiState.headerRows.filter((_, i) => i !== idx);
        this._syncHeadersToFieldState();
    }

    onHeaderKeyChange(idx, ev) {
        this.uiState.headerRows[idx].key = ev.target.value;
        this._syncHeadersToFieldState();
    }

    onHeaderValueChange(idx, ev) {
        this.uiState.headerRows[idx].value = ev.target.value;
        this._syncHeadersToFieldState();
    }

    // ── Payload token quick-insert ───────────────────────────────────────
    /**
     * Common token suggestions shown in a helper panel below the textarea.
     * Clicking a token appends it to fieldState.webhook_payload so the
     * user doesn't have to remember the {{current_record.x}} syntax.
     * generateCode() reads webhook_payload the same way as always.
     */
    get commonTokens() {
        return [
            { label: 'Record ID',       token: '{{current_record.id}}'                      },
            { label: 'Record Name',     token: '{{current_record.name}}'                    },
            { label: 'Customer Name',   token: '{{current_record.partner_id.name}}'         },
            { label: 'Customer Email',  token: '{{current_record.partner_id.email}}'        },
            { label: 'Customer Phone',  token: '{{current_record.partner_id.phone}}'        },
            { label: 'Amount Total',    token: '{{current_record.amount_total}}'            },
            { label: 'Amount Due',      token: '{{current_record.amount_residual_signed}}'  },
            { label: 'Currency',        token: '{{current_record.currency_id.name}}'        },
            { label: 'Invoice / Ref',   token: '{{current_record.name}}'                    },
            { label: 'State',           token: '{{current_record.state}}'                   },
            { label: 'Company Name',    token: '{{current_record.company_id.name}}'         },
            { label: 'Order Date',      token: '{{current_record.date_order}}'              },
        ];
    }

    /**
     * Tags currently found in the payload JSON.
     */
    get selectedPayloadTags() {
        const payloadStr = this.fieldState.webhook_payload || "";
        let payloadObj = {};
        try {
            payloadObj = JSON.parse(payloadStr);
        } catch(e) {
            // If invalid JSON, fallback to just finding the common tokens in the raw string
            return this.commonTokens
                       .filter(tok => payloadStr.includes(tok.token))
                       .map(tok => ({ label: tok.label, token: tok.token, key: tok.token, isCustom: false }));
        }
        
        const tags = [];
        for (const [key, value] of Object.entries(payloadObj)) {
            const matchedToken = this.commonTokens.find(t => typeof value === 'string' && value === t.token);
            if (matchedToken) {
                tags.push({ label: matchedToken.label, token: matchedToken.token, key: key, isCustom: false });
            } else {
                tags.push({ label: key, token: key, key: key, isCustom: true });
            }
        }
        return tags;
    }

    /**
     * Remove a tag from the payload JSON.
     */
    removePayloadTag(key) {
        let currentText = (this.fieldState.webhook_payload || '').trim();
        try {
            let payloadObj = JSON.parse(currentText);
            if (payloadObj.hasOwnProperty(key)) {
                delete payloadObj[key];
                this.fieldState.webhook_payload = JSON.stringify(payloadObj, null, 2);
            }
        } catch(e) {
            // Rough fallback if invalid JSON: Try to strip the line containing the key/token
            const escaped = key.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            const regex = new RegExp(`.*"${escaped}".*\\n?`, 'g');
            this.fieldState.webhook_payload = currentText.replace(regex, '').trim();
        }
    }

    /**
     * Add a selected field token to the payload JSON.
     */
    addFieldToPayload(ev) {
        const token = ev.target.value;
        if (!token) return;
        
        if (token === 'CUSTOM') {
            this.uiState.showCustomPayloadForm = true;
            this.uiState.customPayloadKey = '';
            this.uiState.customPayloadValue = '';
            ev.target.value = "";
            return;
        }
        
        const selected = this.commonTokens.find(t => t.token === token);
        if (!selected) return;
        
        // Generate a valid JSON key from the label (e.g. "Amount Total" -> "amount_total")
        const key = selected.label.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
        this._injectToPayload(key, token);
        
        // Reset select dropdown
        ev.target.value = "";
    }

    /**
     * Add a custom key/value pair to the payload JSON.
     */
    addCustomPayload() {
        const key = (this.uiState.customPayloadKey || '').trim();
        const value = (this.uiState.customPayloadValue || '').trim();
        if (!key) return;
        
        this._injectToPayload(key, value);
        
        this.uiState.showCustomPayloadForm = false;
        this.uiState.customPayloadKey = '';
        this.uiState.customPayloadValue = '';
    }

    /**
     * Helper to safely append a key/value to the JSON payload.
     */
    _injectToPayload(key, value) {
        let payloadObj = null;
        let currentText = (this.fieldState.webhook_payload || '').trim();
        
        if (currentText) {
            try {
                payloadObj = JSON.parse(currentText);
            } catch (e) {
                // Not valid JSON
            }
        } else {
            payloadObj = {};
        }
        
        if (payloadObj !== null && typeof payloadObj === 'object' && !Array.isArray(payloadObj)) {
            // Try to parse number or boolean if value is not a token and looks like one
            if (!value.includes('{{') && !isNaN(value) && value !== '') {
                payloadObj[key] = Number(value);
            } else if (value === 'true') {
                payloadObj[key] = true;
            } else if (value === 'false') {
                payloadObj[key] = false;
            } else {
                try {
                    if (/^\s*[{[]/.test(value)) {
                        payloadObj[key] = JSON.parse(value);
                    } else {
                        payloadObj[key] = value;
                    }
                } catch(e) {
                    payloadObj[key] = value;
                }
            }
            this.fieldState.webhook_payload = JSON.stringify(payloadObj, null, 2);
        } else {
            // String append fallback if they typed invalid JSON
            if (currentText && !currentText.endsWith('\n')) {
                currentText += '\n';
            }
            let safeValue = value.replace(/"/g, '\\"');
            this.fieldState.webhook_payload = currentText + `"${key}": "${safeValue}"`;
        }
    }


}

WebhookNode.template  = "WebhookNode";
WebhookNode.components = { ...ConfigurationBase.components };
