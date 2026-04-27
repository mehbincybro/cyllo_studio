/** @odoo-module **/
export const QrMixin = {

    _getDefaultQrState() {
        return {
            step: 1,
            type: 'portal',
            config: {
                field: 'object.name',
                baseUrl: window.location.origin,
                portalPath: '',
                tokenType: 'auto',
                tokenExpr: '',
                upiVpa: '',
                amountField: 'amount_residual',
                noteField: 'object.name',
                expression: '',
                size: 100,
                align: 'center',
                errorCorrection: 'M',
                caption: '',
                requireAuth: false,
                trackAnalytics: true,
                hasExpiry: false,
                expiresDays: 30,
            },
            previewImgUrl: '',
            previewLoading: false,
            previewError: false,
            previewStr: '',
            qwebPreview: '',
            validationResult: 'none',
            validationError: '',
            warnings: {},
            errors: {
                hasErrors: false,
                upi_vpa: false,
            }
        };
    },

    async openQrWizard(placeholderEl, mode = 'insert') {
        const self = this;
        this.state.showQrWizard = true;

        if (mode === 'edit' && placeholderEl.dataset.qrConfig) {
            try {
                const existing = JSON.parse(placeholderEl.dataset.qrConfig);
                this.state.qr = this._getDefaultQrState();
                this.state.qr.type = existing.type || 'portal';
                Object.assign(this.state.qr.config, existing.config || {});
                this.state.qr.step = 3;
            } catch (e) {
                this.state.qr = this._getDefaultQrState();
            }
        } else {
            this.state.qr = this._getDefaultQrState();
        }

        const model = this.state.reportInfo.model;
        if (model === 'account.move') {
            this.state.qr.config.portalPath = '/my/invoices/';
        } else if (model === 'sale.order') {
            this.state.qr.config.portalPath = '/my/orders/';
        }

        this._updateQrPreviews();

        return new Promise((resolve) => {
            self._qrResolve = (config) => {
                self.state.showQrWizard = false;
                resolve(config);
            };
        });
    },

    onSelectQrType(type) {
        this.state.qr.type = type;
        this._updateQrPreviews();
    },

    updateQrConfig(key, value) {
        if (key === 'size') {
            value = parseInt(value, 10) || 100;
        }
        this.state.qr.config[key] = value;
        if (this.state.qr.type === 'upi') {
            this.state.qr.errors.upi_vpa = !this.state.qr.config.upiVpa;
            this.state.qr.errors.hasErrors = this.state.qr.errors.upi_vpa;
        } else {
            this.state.qr.errors.hasErrors = false;
        }
        this._updateQrPreviews();
    },

    qrNextStep() {
        if (this.state.qr.step < 3) this.state.qr.step++;
    },

    qrPrevStep() {
        if (this.state.qr.step > 1) this.state.qr.step--;
    },

    qrGoToStep(step) {
        if (step < this.state.qr.step || !this.state.qr.errors.hasErrors) {
            this.state.qr.step = step;
        }
    },

    onQrWizardCancel() {
        this.onQrCancel();
    },

    onQrCancel() {
        this.state.showQrWizard = false;
        if (this._qrResolve) this._qrResolve(null);
    },

    async onQrWizardConfirm() {
        if (this.state.qr.type === 'pdf_link' && !this.state.qr.config.token) {
            console.log('entered', this.state.reportInfo.report_name, this)
            try {
                this.state.qr.previewLoading = true;
                const res = await this.rpc('/cyllo_studio/generate_qr_token', {
                    template: this.state.reportInfo.report_name || this._template,
                    options: {
                        requireAuth: this.state.qr.config.requireAuth,
                        trackAnalytics: this.state.qr.config.trackAnalytics,
                        expiresDays: this.state.qr.config.hasExpiry ? this.state.qr.config.expiresDays : null,
                    }
                });
                if (res.success) {
                    this.state.qr.config.token = res.token;
                } else {
                    this.notification.add(res.error || "Failed to generate token", { type: "danger" });
                    this.state.qr.previewLoading = false;
                    return;
                }
            } catch (e) {
                this.notification.add("Could not connect to server", { type: "danger" });
                this.state.qr.previewLoading = false;
                return;
            }
        }

        if (this._qrResolve) {
            this._qrResolve({
                type: this.state.qr.type,
                config: { ...this.state.qr.config }
            });
        }
    },

    async validateQrExpression() {
        const expr = this.state.qr.config.expression;
        if (!expr) return;
        try {
            const result = await this.rpc('/studio/report/validate_expr', {
                expr: expr,
                model: this.state.reportInfo.model
            });
            this.state.qr.validationResult = result.valid ? 'valid' : 'invalid';
            this.state.qr.validationError = result.error || '';
        } catch (e) {
            this.state.qr.validationResult = 'invalid';
            this.state.qr.validationError = e.message;
        }
    },

    onQrPreviewError() {
        this.state.qr.previewError = true;
        this.state.qr.previewLoading = false;
    },

    _updateQrPreviews() {
        if (!this.state.showQrWizard) return;
        const expr = this._buildQrExpression();
        this.state.qr.previewStr = expr;
        this.state.qr.previewLoading = true;
        this.state.qr.previewError = false;

        const encoded = encodeURIComponent(expr.replace(/doc\./g, 'object.'));
        const size = this.state.qr.config.size || 100;
        this.state.qr.previewImgUrl = `/report/barcode/?barcode_type=QR&value=${encoded}&width=${size}&height=${size}`;

        const align = this.state.qr.config.align;
        const qwebExpr = this._buildQrExpression(true);

        let html = `<div style="text-align:${align};">\n`;
        html += `  <img t-att-src="'/report/barcode/?barcode_type=QR&amp;value=%s&amp;width=${size}&amp;height=${size}' % url_quote(str(${qwebExpr}) or 'No Data')" \n`;
        html += `       style="width:${size}px; height:${size}px;"/>\n`;
        if (this.state.qr.config.caption) {
            html += `  <div style="font-size:8pt; margin-top:3px;">${this.state.qr.config.caption}</div>\n`;
        }
        html += `</div>`;
        this.state.qr.qwebPreview = html;
    },

    _buildQrExpression(forQWeb = false, qrState = null) {
        const type = qrState ? qrState.type : this.state.qr.type;
        const config = qrState ? qrState.config : this.state.qr.config;
        const obj = 'doc'; // Always use 'doc' to match the blank report iterator

        /**
         * Determine whether a string value looks like a Python field expression
         * (e.g. "doc.partner_id.name") or a static literal that must be quoted.
         * A static value = anything that:
         *   - contains '://' (URLs like https://...)
         *   - starts with a digit or special char that isn't a valid Python identifier start
         *   - contains spaces
         *   - is NOT prefixed with a known Python variable name
         */
        const _quoteIfStatic = (val) => {
            if (!val) return "''";
            // Already a quoted string in the expression (starts/ends with quote)
            if ((val.startsWith("'") && val.endsWith("'")) ||
                (val.startsWith('"') && val.endsWith('"'))) {
                return val;
            }
            // Looks like a field path: starts with a word char and contains only
            // word chars, dots, underscores (e.g. doc.partner_id.name)
            if (/^[a-zA-Z_][a-zA-Z0-9_.]*$/.test(val)) {
                return val.replace(/object\./g, obj + '.');
            }
            // Static value — escape single quotes and wrap
            const escaped = val.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            return `'${escaped}'`;
        };

        if (type === 'plain') return _quoteIfStatic(config.field);
        if (type === 'portal') {
            const path = config.portalPath || '/my/view/';
            let baseUrlStr = `str(${obj}.get_base_url()).rstrip('/')`;
            if (config.baseUrl && config.baseUrl !== window.location.origin) {
                const safeUrl = config.baseUrl.replace(/'/g, "\\'").replace(/\/$/, '');
                baseUrlStr = `'${safeUrl}'`;
            }

            const s = `${baseUrlStr} `;
            if (config.tokenType === 'auto') return s + ` + '?' + ${obj}._get_share_url()`;
            return s;
        }
        if (type === 'upi') {
            const pa = config.upiVpa;
            const am = `${obj}.${config.amountField}`;
            const tn = config.noteField === 'custom' ? "'Payment'" : config.noteField.replace(/object\./g, obj + '.');
            return `'upi://pay?pa=${pa}&am=' + str(${am}) + '&tn=' + str(${tn})`;
        }
        if (type === 'custom') return _quoteIfStatic(config.expression || "''");
        if (type === 'pdf_link') {
            const reportId = this.state.reportInfo?.id || this._reportId || 'REPORT_ID';
            let baseUrlStr = `str(${obj}.get_base_url()).rstrip('/')`;
            return `${baseUrlStr} + '/report/pdf/${this.state.reportInfo.id}/' + str(${obj}.id) + '?token=${config.token || "PENDING"}'`;
        }
        return "''";
    },

    insertQrBlock(placeholderEl, qrConfig, mode = 'insert') {
        const type = qrConfig.type;
        const config = qrConfig.config;
        const align = config.align || 'center';
        const size = config.size || 100;

        placeholderEl.className = 's_qr_block c_new';
        placeholderEl.style.textAlign = align;
        placeholderEl.style.cursor = 'default';
        placeholderEl.style.opacity = '1';
        placeholderEl.setAttribute('cy-type', 'qr');
        placeholderEl.dataset.qrConfig = JSON.stringify(qrConfig);

        const previewImg = this._buildQrExpression().replace(/doc\./g, 'object.');
        const encoded = encodeURIComponent(previewImg);

        // Build a clear edit-mode placeholder with icon + label visible even if img fails
        placeholderEl.innerHTML = `
            <div class="qr-handle-container" contenteditable="false" style="position:absolute; top:-10px; left:10px; background:#9ea700; border-radius:4px; padding:0 4px; display:flex; gap:6px; z-index:100;">
                <span class="fa fa-bars" style="color:white; font-size:10px; cursor:grab; padding:2px;"></span>
                <span class="qr-edit-btn fa fa-edit" style="color:white; font-size:10px; cursor:pointer; padding:2px;" title="Edit QR"></span>
                <span class="qr-delete fa fa-trash" style="color:#ffdce0; font-size:10px; cursor:pointer; padding:2px;" title="Delete QR"></span>
            </div>
            <div class="qr-edit-placeholder" style="display:inline-block; border:2px dashed #9ea700; border-radius:6px; padding:10px; min-width:${size}px; min-height:${size}px; position:relative; background:#fafdf0;">
                <div style="position:absolute; top:4px; left:0; right:0; text-align:center; font-size:9px; color:#9ea700; font-weight:700; letter-spacing:0.5px; text-transform:uppercase;">QR Code</div>
                <div style="width:${size}px; height:${size}px; display:flex; flex-direction:column; align-items:center; justify-content:center; margin:0 auto; padding-top:10px;">
                    <i class="fa fa-qrcode" style="font-size:${Math.round(size * 0.55)}px; color:#9ea700; opacity:0.7;"></i>
                    <div style="font-size:9px; color:#9ea700; margin-top:4px; opacity:0.8;">${type}</div>
                </div>
                ${config.caption ? `<div class="qr-caption" style="font-size:8pt; margin-top:3px; text-align:center; color:#555;">${config.caption}</div>` : ''}
            </div>
        `;

        placeholderEl.querySelector('.qr-delete').onclick = (e) => {
            e.stopPropagation();
            if (confirm("Delete this QR code?")) placeholderEl.remove();
        };

        if (mode === 'insert') {
            setTimeout(() => placeholderEl.classList.add('selected'), 0);
        }
        this._refreshDragHandles();
    }
};
