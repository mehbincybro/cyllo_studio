# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields, api
import requests
import logging
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class GoogleForm(models.Model):
    _name = 'google.form'
    _description = 'Google Form'
    _order = 'id desc'

    name = fields.Char(required=True)
    google_form_id = fields.Char(string='Google Form ID', readonly=True)
    form_url = fields.Char(string='Form URL', readonly=True)
    lead_id = fields.Many2one('crm.lead', string='Linked Lead')
    active = fields.Boolean(default=True)
    question_ids = fields.One2many(
        'google.form.questions',
        'google_form_id',
        string='Questions'
    )
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'google.form')],
        default=lambda self: self.env.ref(
            'cyllo_crm_google_form.email_template_google_form_share',
            raise_if_not_found=False
        ),
    )
    need_automatic_fetching = fields.Boolean(string='Automatic Fetching')

    # Stores comma-separated Google responseIds already turned into leads.
    # This is the single source of truth for duplicate prevention.
    processed_response_ids = fields.Text(
        string='Processed Response IDs',
        default='',
        help='Internal. Comma-separated Google Form responseIds already processed into leads.'
    )

    # ======================================================================
    # CONSTANTS
    # ======================================================================

    _CHOICE_TYPES = {'MULTIPLE_CHOICE', 'DROPDOWN', 'CHECKBOX'}

    _CHOICE_API_TYPE = {
        'MULTIPLE_CHOICE': 'RADIO',
        'DROPDOWN': 'DROP_DOWN',
        'CHECKBOX': 'CHECKBOX',
    }

    _TEXT_TYPES = {
        'TEXT', 'PARAGRAPH', 'EMAIL', 'PHONE', 'NUMBER', 'AGE', 'ADDRESS',
    }

    _PARAGRAPH_TYPES = {'PARAGRAPH', 'ADDRESS'}

    # ======================================================================
    # OAUTH
    # ======================================================================

    def refresh_access_token(self):
        """Refresh Google OAuth access token using stored credentials."""
        params = self.env['ir.config_parameter'].sudo()
        refresh_token = params.get_param('cyllo_google.refresh_token')
        client_id = params.get_param('cyllo_google.client_id')
        client_secret = params.get_param('cyllo_google.client_secret')

        if not all([refresh_token, client_id, client_secret]):
            raise ValidationError(
                "Google OAuth configuration is incomplete.\n"
                "Please fill in Client ID, Client Secret and Refresh Token "
                "under Settings → Google Forms Configuration."
            )

        response = requests.post(
            url="https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise ValidationError(f"Token refresh failed: {response.text}")

        result = response.json()
        access_token = result.get("access_token")
        if not access_token:
            raise ValidationError(
                f"Access token missing in response: {result}")

        params.set_param('cyllo_google.access_token', access_token)
        return access_token

    # ======================================================================
    # CREATE FORM
    # ======================================================================

    def create_google_form(self):
        """Create a Google Form and push all questions via batchUpdate."""
        self.ensure_one()
        access_token = self.refresh_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        create_resp = requests.post(
            "https://forms.googleapis.com/v1/forms",
            headers=headers,
            json={"info": {"title": self.name}},
            timeout=10,
        )
        if create_resp.status_code != 200:
            raise ValidationError(
                f"Failed to create Google Form:\n{create_resp.text}\n\n"
                "Hint: Make sure your refresh token includes the full "
                "'https://www.googleapis.com/auth/forms' scope."
            )

        result = create_resp.json()
        form_id = result.get("formId")
        responder_uri = result.get("responderUri", "")

        if not form_id:
            raise ValidationError("Google API did not return a formId.")

        if self.question_ids:
            batch_requests = [
                self._build_create_item_request(q, idx)
                for idx, q in enumerate(self.question_ids)
            ]
            batch_resp = requests.post(
                f"https://forms.googleapis.com/v1/forms/{form_id}:batchUpdate",
                headers=headers,
                json={"requests": batch_requests},
                timeout=15,
            )
            if batch_resp.status_code != 200:
                raise ValidationError(
                    f"Form created but questions failed to sync.\n{batch_resp.text}"
                )

        self.write({
            'google_form_id': form_id,
            'form_url': responder_uri,
        })
        return True

    def _build_create_item_request(self, question, index):
        q_type = question.question_type

        if q_type == 'DATE':
            question_body = {
                "required": False,
                "dateQuestion": {
                    "includeTime": False,
                    "includeYear": True,
                },
            }
        elif q_type == 'TIME':
            question_body = {
                "required": False,
                "timeQuestion": {
                    "duration": False,
                },
            }
        elif q_type in self._CHOICE_TYPES:
            options = [
                {"value": opt.strip()}
                for opt in (question.choices or "").split(",")
                if opt.strip()
            ]
            question_body = {
                "required": False,
                "choiceQuestion": {
                    "type": self._CHOICE_API_TYPE[q_type],
                    "options": options,
                    "shuffle": False,
                },
            }
        else:
            is_paragraph = q_type in self._PARAGRAPH_TYPES
            question_body = {
                "required": False,
                "textQuestion": {"paragraph": is_paragraph},
            }

        return {
            "createItem": {
                "item": {
                    "title": question.name,
                    "questionItem": {"question": question_body},
                },
                "location": {"index": index},
            }
        }

    # ======================================================================
    # RELATIONAL FIELD RESOLVER
    # ======================================================================

    def _resolve_relational_value(self, field, raw_value):
        """Relational fields resolve here"""
        if not raw_value or not raw_value.strip():
            return False

        ttype = field.ttype

        if ttype == 'many2one':
            comodel = field.relation
            RelModel = self.env[comodel].sudo()
            record = RelModel.search([('name', 'ilike', raw_value.strip())],
                                     limit=1)
            if not record:
                try:
                    record = RelModel.create({'name': raw_value.strip()})
                except Exception:
                    return False
            return record.id

        elif ttype == 'many2many':
            comodel = field.relation
            RelModel = self.env[comodel].sudo()
            ids = []
            for val in raw_value.split(','):
                val = val.strip()
                if not val:
                    continue
                record = RelModel.search([('name', 'ilike', val)], limit=1)
                if not record:
                    try:
                        record = RelModel.create({'name': val})
                    except Exception:
                        continue
                ids.append(record.id)
            return [(4, rid) for rid in ids] if ids else False

        elif ttype == 'one2many':
            return None

        elif ttype in ('integer',):
            try:
                return int(float(raw_value.strip().replace(',', '')))
            except (ValueError, TypeError):
                return False

        elif ttype in ('float', 'monetary'):
            try:
                return float(raw_value.strip().replace(',', ''))
            except (ValueError, TypeError):
                return False

        elif ttype == 'boolean':
            return raw_value.strip().lower() in ('true', 'yes', '1', 'y', 'on')

        else:
            return raw_value.strip()

    # ======================================================================
    # DUPLICATE PREVENTION HELPERS
    # ======================================================================

    def _get_processed_ids(self):
        """Return a set of already-processed Google responseIds for this form."""
        raw = self.processed_response_ids or ''
        return set(filter(None, [r.strip() for r in raw.split(',')]))

    def _mark_response_processed(self, response_id):
        """Append a responseId to the processed set and persist immediately."""
        if not response_id:
            return
        existing = self._get_processed_ids()
        existing.add(str(response_id).strip())
        # Use sudo + direct write so cron user permissions never block this
        self.sudo().write({
            'processed_response_ids': ','.join(existing)
        })

    # ======================================================================
    # CORE: PROCESS A SINGLE FORM'S RESPONSES  (internal, no active check)
    # ======================================================================

    def _process_form_responses(self, access_token):
        """
        Internal method that does the actual API calls and lead creation
        for a single google.form record (self must be a single record).
        Does NOT check self.active — callers are responsible for filtering.
        Returns the number of new leads created.
        """
        self.ensure_one()
        headers = {"Authorization": f"Bearer {access_token}"}
        leads_created = 0

        # ── 1. Fetch form structure ────────────────────────────────────────
        form_resp = requests.get(
            f"https://forms.googleapis.com/v1/forms/{self.google_form_id}",
            headers=headers,
            timeout=10,
        )
        if form_resp.status_code != 200:
            _logger.warning(
                f"google.form [{self.id}] — could not fetch form structure: {form_resp.text}"
            )
            return 0

        title_map = {}  # questionId → question title string
        record_map = {}  # questionId → google.form.questions record

        for item in form_resp.json().get("items", []):
            q_item = item.get("questionItem") or item.get("questionGroupItem")
            if not q_item:
                continue

            questions_in_item = []
            if "question" in q_item:
                questions_in_item.append(q_item["question"])
            elif "questions" in q_item:
                questions_in_item.extend(q_item["questions"])

            title = item.get("title", "")
            for gq in questions_in_item:
                gqid = gq.get("questionId")
                if not gqid:
                    continue
                title_map[gqid] = title
                matched = self.question_ids.filtered(
                    lambda q,
                           t=title: q.name.strip().lower() == t.strip().lower()
                )
                if matched:
                    record_map[gqid] = matched[0]

        # ── 2. Fetch all responses ─────────────────────────────────────────
        resp = requests.get(
            f"https://forms.googleapis.com/v1/forms/{self.google_form_id}/responses",
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            _logger.warning(
                f"google.form [{self.id}] — could not fetch responses: {resp.text}"
            )
            return 0

        already_processed = self._get_processed_ids()

        for submission in resp.json().get("responses", []):
            response_id = submission.get("responseId", "")

            # ── DUPLICATE GUARD ──────────────────────────────────────────
            # processed_response_ids is the main source of truth.
            # Each unique Google responseId only ever creates one lead.
            if response_id and response_id in already_processed:
                _logger.debug(
                    f"google.form [{self.id}] — skipping already-processed responseId {response_id}"
                )
                continue

            # ── Build lead values from answers ───────────────────────────
            answers = submission.get("answers", {})
            lead_vals = {}
            description_lines = []

            for gqid, answer_obj in answers.items():
                raw_value = self._extract_answer_value(answer_obj) or ""
                q_title = title_map.get(gqid, "Unknown Question")
                orm_q = record_map.get(gqid)

                if orm_q and orm_q.lead_field_id:
                    field = orm_q.lead_field_id
                    field_name = field.name

                    if field.ttype == 'one2many':
                        description_lines.append(
                            f"{q_title}: {raw_value}  [one2many — skipped]")
                        continue

                    resolved = self._resolve_relational_value(field, raw_value)
                    if resolved is None or resolved is False:
                        if raw_value:
                            description_lines.append(f"{q_title}: {raw_value}")
                        continue

                    if field.ttype == 'many2many':
                        lead_vals[field_name] = lead_vals.get(field_name,
                                                              []) + resolved
                    else:
                        lead_vals[field_name] = resolved
                else:
                    lower_title = q_title.lower().strip()
                    if lower_title in ('name', 'full name', 'your name',
                                       'contact name'):
                        lead_vals.setdefault('name', raw_value)
                    elif lower_title in ('email', 'email address', 'e-mail',
                                         'your email'):
                        lead_vals.setdefault('email_from', raw_value)
                    elif lower_title in ('phone', 'phone number',
                                         'contact number', 'telephone'):
                        lead_vals.setdefault('phone', raw_value)
                    elif lower_title in ('mobile', 'mobile number', 'cell',
                                         'cell phone'):
                        lead_vals.setdefault('mobile', raw_value)
                    elif lower_title in ('company', 'company name',
                                         'organisation', 'organization'):
                        lead_vals.setdefault('partner_name', raw_value)
                    elif lower_title in ('website', 'website url', 'web'):
                        lead_vals.setdefault('website', raw_value)
                    elif lower_title in ('address', 'street address',
                                         'your address'):
                        lead_vals.setdefault('street', raw_value)
                    elif lower_title in ('city',):
                        lead_vals.setdefault('city', raw_value)
                    elif lower_title in ('zip', 'zip code', 'postal code',
                                         'postcode'):
                        lead_vals.setdefault('zip', raw_value)
                    else:
                        if raw_value:
                            description_lines.append(f"{q_title}: {raw_value}")

            # ── Fallback lead name ────────────────────────────────────────
            if not lead_vals.get('name'):
                partner_id = lead_vals.get('partner_id')
                if partner_id:
                    partner_rec = self.env['res.partner'].sudo().browse(
                        partner_id)
                    lead_vals[
                        'name'] = f"{partner_rec.name or self.name}'s Opportunity"
                elif lead_vals.get('partner_name'):
                    lead_vals[
                        'name'] = f"{lead_vals['partner_name']}'s Opportunity"
                elif lead_vals.get('email_from'):
                    lead_vals[
                        'name'] = f"{lead_vals['email_from']}'s Opportunity"
                else:
                    lead_vals['name'] = f"{self.name}'s Opportunity"

            if self.lead_id:
                lead_vals.setdefault('parent_id', self.lead_id.id)

            # ── Stamp responseId into description for traceability ────────
            # This makes it easy to trace which Google Form submission
            # created which lead, directly from the lead's Notes tab.
            response_tag = (
                f"[Google Form Response ID: {response_id}]"
                if response_id else ""
            )
            extra_lines = "\n".join(description_lines)

            if response_tag and extra_lines:
                lead_vals['description'] = f"{response_tag}\n\n{extra_lines}"
            elif response_tag:
                lead_vals['description'] = response_tag
            elif extra_lines:
                lead_vals['description'] = extra_lines

            # ── Create the lead ───────────────────────────────────────────
            #
            # WHY mail_create_nosubscribe=True and tracking_disable=True?
            #
            # Odoo's mail thread (mail.thread) runs email normalization
            # and partner-matching logic when a lead is created. If a lead
            # with the same email_from already exists, Odoo can silently
            # skip creation or merge the new lead into the existing one.
            #
            # mail_create_nosubscribe=True
            #   → Skips auto-subscribing followers. Prevents the mail
            #     thread from doing its partner-lookup/dedup during create.
            #
            # tracking_disable=True
            #   → Disables field change tracking entirely during create.
            #     This stops the mail.tracking.value logic that triggers
            #     email normalization checks on email_from, which is the
            #     root cause of the second lead not being created when the
            #     same email address appears in a different submission.
            #
            # Result: every Google Form submission always becomes its own
            # independent CRM lead, regardless of email address.
            self.env['crm.lead'].sudo().with_context(
                mail_create_nosubscribe=True,
                tracking_disable=True,
            ).create(lead_vals)

            leads_created += 1
            _logger.info(
                f"google.form [{self.id}] — created lead for responseId {response_id or '(no id)'}"
            )

            # ── Mark processed immediately after successful creation ───────
            if response_id:
                self._mark_response_processed(response_id)
                already_processed.add(response_id)

        return leads_created

    # ======================================================================
    # PUBLIC: MANUAL FETCH (button on form view)
    # ======================================================================

    def fetch_responses_create_leads(self):
        """
        Manual button handler — fetch responses and create leads for
        the current record(s). Raises user-visible errors on failure.
        """
        self.ensure_one()

        if not self.active:
            raise ValidationError("This form is currently not active.")
        if not self.google_form_id:
            raise ValidationError(
                "This form has not been pushed to Google yet.")

        access_token = self.refresh_access_token()
        count = self._process_form_responses(access_token)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fetch Complete',
                'message': f'{count} new lead(s) created from Google Form responses.',
                'type': 'success',
                'sticky': False,
            }
        }

    # ======================================================================
    # ANSWER VALUE EXTRACTOR
    # ======================================================================

    def _extract_answer_value(self, answer_obj):
        if not answer_obj:
            return ""

        text_answers = answer_obj.get("textAnswers", {}).get("answers", [])
        if text_answers:
            return ", ".join(
                a.get("value", "") for a in text_answers if a.get("value", "")
            )

        date_ans = answer_obj.get("date")
        if date_ans:
            year = date_ans.get("year", "")
            month = str(date_ans.get("month", "")).zfill(2)
            day = str(date_ans.get("day", "")).zfill(2)
            return f"{year}-{month}-{day}" if year else ""

        time_ans = answer_obj.get("time")
        if time_ans:
            hour = str(time_ans.get("hours", 0)).zfill(2)
            minute = str(time_ans.get("minutes", 0)).zfill(2)
            return f"{hour}:{minute}"

        return ""

    # ======================================================================
    # CRON: AUTO FETCH RESPONSES
    # ======================================================================

    @api.model
    def cron_auto_fetch_responses(self):
        """
        Entry point called by the ir.cron scheduled action:
            model.cron_auto_fetch_responses()

        Loops over every active form that has need_automatic_fetching = True
        and processes new responses. Each form gets its own try/except so
        a single failure never kills the entire cron run.
        """
        forms = self.search([
            ('active', '=', True),
            ('need_automatic_fetching', '=', True),
            ('google_form_id', '!=', False),
        ])

        if not forms:
            _logger.info(
                "google.form cron — no forms with automatic fetching enabled.")
            return

        _logger.info(
            f"google.form cron — processing {len(forms)} form(s) with automatic fetching."
        )

        for form in forms:
            try:
                # Refresh token once per form (tokens last ~1 hour)
                access_token = form.refresh_access_token()
                count = form._process_form_responses(access_token)
                _logger.info(
                    f"google.form cron — form '{form.name}' (ID {form.id}): {count} new lead(s) created."
                )
            except Exception:
                _logger.exception(
                    f"google.form cron — ERROR processing form '{form.name}' (ID {form.id}). "
                    f"Continuing with remaining forms."
                )

    # ======================================================================
    # SHARE WIZARD
    # ======================================================================

    def action_open_share_wizard(self):
        self.ensure_one()

        if not self.form_url:
            raise UserError(
                "Form URL is not available. "
                "Please create the Google Form first by clicking 'Create Google Form'."
            )

        if not self.mail_template_id:
            raise UserError(
                "No email template is linked to this form. "
                "Please set an email template in the 'Email Template' field."
            )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'google.form',
                'default_res_ids': [self.id],
                'default_template_id': self.mail_template_id.id,
                'default_composition_mode': 'comment',
                'force_email': True,
            }
        }
