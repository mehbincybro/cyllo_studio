/** @odoo-module */
const { useState } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { MailRecordPathSelector } from "../mailNode/subcomponents/mailRecordPathSelector";

export class WebhookNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        if (!this.fieldState.webhook_method || typeof this.fieldState.webhook_method === 'object') {
            this.fieldState.webhook_method = 'POST';
        }
        if (!this.fieldState.webhook_headers || typeof this.fieldState.webhook_headers === 'object') {
            this.fieldState.webhook_headers = '{"Content-Type": "application/json"}';
        }
        if (!this.fieldState.webhook_actions) {
            this.fieldState.webhook_actions = [];
        }
    }

    addAction() {
        const actions = Array.isArray(this.fieldState.webhook_actions) ? this.fieldState.webhook_actions : [];
        this.fieldState.webhook_actions = [...actions, {
            id: Date.now().toString(),
            type: 'extract',
            json_path: '',
            target: '',
            message: '',
        }];
    }

    removeAction(id) {
        if (Array.isArray(this.fieldState.webhook_actions)) {
            this.fieldState.webhook_actions = this.fieldState.webhook_actions.filter(a => a.id !== id);
        }
    }

    get getMethodOptions() {
        return [
            { label: 'POST', value: 'POST' },
            { label: 'GET', value: 'GET' },
            { label: 'PUT', value: 'PUT' },
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
     * generateCode()
     *
     * Produces a Python snippet that:
     *   1. Builds the payload as a native Python dict using json.loads()
     *      on an f-string — avoids ALL brace-escaping nightmares.
     *   2. Substitutes {{expr}} tokens (e.g. {{current_record.name}}) with
     *      Python f-string expressions {expr or ""}.
     *   3. Sends the request using requests.post(..., json=payload) so the
     *      dict is serialized correctly and Content-Type is set automatically.
     *   4. Logs the payload and response for debugging in the Cyllo server log.
     *
     * The user writes payload tokens as {{current_record.field}} in the UI.
     * This is converted to the Python f-string token {current_record.field or ""}.
     */
    generateCode() {
        const url = this.fieldState.webhook_url || "";
        const method = this.fieldState.webhook_method || "POST";
        const headersRaw = this.fieldState.webhook_headers || '{"Content-Type": "application/json"}';
        const payloadRaw = this.fieldState.webhook_payload || "{}";

        // --- Step 1: Replace {{expr}} → Python f-string token ---
        // User writes: {{current_record.id}}
        // We produce:  {current_record.id or ""}  (safe: None/False → "")
        // We use a unique sentinel to avoid double-processing.
        const tokens = [];
        const sentinel = payloadRaw.replace(/\{\{([^}]+)\}\}/g, (match, expr) => {
            const idx = tokens.length;
            tokens.push(expr.trim());
            return `\x00PH${idx}\x00`;  // null-byte sentinel, safe in temp string
        });

        // --- Step 2: Escape remaining literal { and } for Python f-string ---
        // Every { or } that is NOT one of our sentinels is literal JSON structure.
        // Python f-strings require {{ and }} for literal braces.
        let fstring = sentinel
            .replace(/\{/g, '{{')
            .replace(/\}/g, '}}');

        // --- Step 3: Restore sentinels as real Python f-string expressions ---
        tokens.forEach((expr, idx) => {
            // Use a safe fallback: `expr or ""` handles None/False/0 gracefully
            fstring = fstring.replace(`\x00PH${idx}\x00`, `{${expr} or ""}`);
        });

        // --- Step 4: Build the Python code ---
        let code = '';
        code += `_wh_url = "${url}"\n`;
        code += `_wh_headers = ${headersRaw}\n`;
        code += `_wh_template = f"""${fstring}"""\n`;
        code += `try:\n`;
        code += `    _wh_payload = json.loads(_wh_template)\n`;
        code += `except Exception as _je:\n`;
        code += `    raise UserError(f"Webhook: JSON parse failed after field substitution: {str(_je)}\\nPayload was: {_wh_template}")\n`;
        code += `_logger.info("=== WEBHOOK PAYLOAD ===\\n%s", json.dumps(_wh_payload, indent=2, default=str))\n`;
        code += `try:\n`;
        if (method === 'GET') {
            code += `    _wh_resp = requests.get(_wh_url, headers=_wh_headers)\n`;
        } else if (method === 'POST') {
            code += `    _wh_resp = requests.post(_wh_url, headers=_wh_headers, json=_wh_payload)\n`;
        } else if (method === 'PUT') {
            code += `    _wh_resp = requests.put(_wh_url, headers=_wh_headers, json=_wh_payload)\n`;
        } else if (method === 'DELETE') {
            code += `    _wh_resp = requests.delete(_wh_url, headers=_wh_headers)\n`;
        } else {
            code += `    _wh_resp = requests.request("${method}", _wh_url, headers=_wh_headers, json=_wh_payload)\n`;
        }
        code += `    _logger.info("=== WEBHOOK RESPONSE %s ===\\n%s", _wh_resp.status_code, _wh_resp.text)\n`;
        code += `    _wh_resp.raise_for_status()\n`;
        code += `    _logger.info("Webhook success: ${method} ${url} -> %s", _wh_resp.status_code)\n`;

        // --- Response Processing ---
        code += `    try:\n`;
        code += `        _wh_resp_json = _wh_resp.json() if _wh_resp.text else {}\n`;
        code += `    except Exception:\n`;
        code += `        _wh_resp_json = {}\n`;

        code += `    def _extract_json_path(data, path):\n`;
        code += `        if not path: return data\n`;
        code += `        for key in path.split('.'):\n`;
        code += `            if isinstance(data, dict) and key in data:\n`;
        code += `                data = data[key]\n`;
        code += `            elif isinstance(data, list) and key.isdigit() and int(key) < len(data):\n`;
        code += `                data = data[int(key)]\n`;
        code += `            else:\n`;
        code += `                return None\n`;
        code += `        return data\n`;

        const actions = Array.isArray(this.fieldState.webhook_actions) ? this.fieldState.webhook_actions : [];
        actions.forEach((action, index) => {
            if (action.json_path) {
                code += `    _val_${index} = _extract_json_path(_wh_resp_json, "${action.json_path}")\n`;
                if (action.type === 'extract' && action.target) {
                    code += `    ${action.target} = _val_${index}\n`;
                } else if (action.type === 'update_record' && action.target) {
                    code += `    if _val_${index} is not None and 'current_record' in locals() and current_record:\n`;
                    code += `        current_record.write({"${action.target}": _val_${index}})\n`;
                } else if (action.type === 'chatter' && action.message) {
                    code += `    if 'current_record' in locals() and current_record and hasattr(current_record, "message_post"):\n`;
                    code += `        _msg = """${action.message}""".replace("{{value}}", str(_val_${index} or ''))\n`;
                    code += `        current_record.message_post(body=_msg)\n`;
                } else if (action.type === 'activity' && action.message) {
                    code += `    if 'current_record' in locals() and current_record and hasattr(current_record, "activity_schedule"):\n`;
                    code += `        _summary = """${action.message}""".replace("{{value}}", str(_val_${index} or ''))\n`;
                    code += `        current_record.activity_schedule("mail.mail_activity_data_todo", summary=_summary)\n`;
                } else if (action.type === 'email' && action.message) {
                    code += `    _msg = """${action.message}""".replace("{{value}}", str(_val_${index} or ''))\n`;
                    // Build a safe dot-path expression using the variable name (no var_ prefix)
                    // and action.target_obj.path (raw path, no .id suffix added by pathValue)
                    let emailPath = '';
                    if (action.target_obj && action.target_obj.record) {
                        const variable = this.variables.find(item => item.id === action.target_obj.record);
                        if (variable) {
                            const varName = variable.variable_name;  // e.g. 'current_record'
                            const path = action.target_obj.path || '';  // e.g. 'partner_id.email'
                            emailPath = path ? `${varName}.${path}` : varName;
                        }
                    }
                    if (emailPath) {
                        // Use safe getattr traversal instead of eval()
                        const pathParts = emailPath.split('.');
                        const rootVar = pathParts.shift();
                        const remainingPath = pathParts.join('.');
                        code += `    try:\n`;
                        code += `        _email_obj = ${rootVar}\n`;
                        if (remainingPath) {
                            code += `        for _email_key in "${remainingPath}".split('.'):\n`;
                            code += `            _email_obj = getattr(_email_obj, _email_key, None)\n`;
                            code += `            if _email_obj is None: break\n`;
                        }
                        code += `        _email_to = getattr(_email_obj, 'email', str(_email_obj)) if _email_obj else ''\n`;
                        code += `    except Exception:\n`;
                        code += `        _email_to = ''\n`;
                        code += `    if _email_to and '@' in _email_to:\n`;
                        code += `        env['mail.mail'].sudo().create({'subject': 'Webhook Notification', 'body_html': _msg, 'email_to': _email_to, 'state': 'outgoing'}).send()\n`;
                    }
                } else if (action.type === 'redirect') {
                    code += `    if _val_${index}:\n`;
                    code += `        action = {"type": "ir.actions.act_url", "url": str(_val_${index}), "target": "self"}\n`;
                }
            }
        });

        code += `except Exception as _we:\n`;
        code += `    _we_msg = str(_we)\n`;
        code += `    _wh_status = getattr(_wh_resp, "status_code", "N/A") if "_wh_resp" in dir() else "N/A"\n`;
        code += `    _logger.error("Webhook failed: ${method} ${url} [HTTP %s] -> %s", _wh_status, _we_msg)\n`;
        code += `    raise UserError(f"Webhook Execution Failed [HTTP {_wh_status}]:\\n{_we_msg}")\n`;

        return code;
    }

    validateForm() {
        const { webhook_url, webhook_method, label } = this.fieldState;
        const errors = {};
        if (!label) errors.label = "Label must be non-empty.";
        if (!webhook_url) errors.webhook_url = "URL is required.";
        if (!webhook_method) errors.webhook_method = "Method is required.";
        
        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }
        return { isValid: true };
    }
}

WebhookNode.template = "WebhookNode";
WebhookNode.components = {
    ...ConfigurationBase.components,
    MailRecordPathSelector
};
