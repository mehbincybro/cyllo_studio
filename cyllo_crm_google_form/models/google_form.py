# -*- coding: utf-8 -*-
# ############################################################################
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

############################################################################
from odoo import models, fields
import requests
from odoo.exceptions import ValidationError


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

    # ======================================================================
    # CONSTANTS
    # ======================================================================

    # Question types that use a choiceQuestion in the Google Forms API
    _CHOICE_TYPES = {'MULTIPLE_CHOICE', 'DROPDOWN', 'CHECKBOX'}

    # Google Forms API "type" value for each Odoo question_type
    _CHOICE_API_TYPE = {
        'MULTIPLE_CHOICE': 'RADIO',
        'DROPDOWN':        'DROP_DOWN',
        'CHECKBOX':        'CHECKBOX',
    }

    # Question types that are sent as plain text questions to Google.
    # The Google Forms API does NOT support textValidation, validateAsEmail,
    # or regex patterns in the createItem payload — those fields simply do
    # not exist in the API schema and will cause a 400 INVALID_ARGUMENT error.
    # All typed questions (EMAIL, PHONE, NUMBER, AGE, ADDRESS) are sent as
    # plain textQuestion items; the question label tells the respondent what
    # to enter.
    _TEXT_TYPES = {
        'TEXT', 'PARAGRAPH', 'EMAIL', 'PHONE', 'NUMBER', 'AGE', 'ADDRESS',
    }

    # Types within _TEXT_TYPES that should render as a multiline paragraph box
    _PARAGRAPH_TYPES = {'PARAGRAPH', 'ADDRESS'}

    # ======================================================================
    # OAUTH
    # ======================================================================

    def refresh_access_token(self):
        """Refresh Google OAuth access token using stored credentials."""
        params = self.env['ir.config_parameter'].sudo()
        refresh_token  = params.get_param('cyllo_google.refresh_token')
        client_id      = params.get_param('cyllo_google.client_id')
        client_secret  = params.get_param('cyllo_google.client_secret')

        if not all([refresh_token, client_id, client_secret]):
            raise ValidationError(
                "Google OAuth configuration is incomplete.\n"
                "Please fill in Client ID, Client Secret and Refresh Token "
                "under Settings → Google Forms Configuration."
            )

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id":     client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type":    "refresh_token",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise ValidationError("Token refresh failed: %s" % response.text)

        result = response.json()
        access_token = result.get("access_token")
        if not access_token:
            raise ValidationError("Access token missing in response: %s" % result)

        params.set_param('cyllo_google.access_token', access_token)
        return access_token

    # ======================================================================
    # CREATE / SYNC FORM
    # ======================================================================

    def create_google_form(self):
        """Create a Google Form and push all questions via batchUpdate."""
        self.ensure_one()
        access_token = self.refresh_access_token()
        headers = {
            "Authorization": "Bearer %s" % access_token,
            "Content-Type":  "application/json",
        }

        # STEP 1 ── Create the form (title only)
        create_resp = requests.post(
            "https://forms.googleapis.com/v1/forms",
            headers=headers,
            json={"info": {"title": self.name}},
            timeout=10,
        )
        if create_resp.status_code != 200:
            raise ValidationError(
                "Failed to create Google Form:\n%s\n\n"
                "Hint: Make sure your refresh token includes the full "
                "'https://www.googleapis.com/auth/forms' scope." % create_resp.text
            )

        result       = create_resp.json()
        form_id      = result.get("formId")
        responder_uri = result.get("responderUri", "")

        if not form_id:
            raise ValidationError("Google API did not return a formId.")

        # STEP 2 ── Push questions via batchUpdate
        if self.question_ids:
            batch_requests = [
                self._build_create_item_request(q, idx)
                for idx, q in enumerate(self.question_ids)
            ]
            batch_resp = requests.post(
                "https://forms.googleapis.com/v1/forms/%s:batchUpdate" % form_id,
                headers=headers,
                json={"requests": batch_requests},
                timeout=15,
            )
            if batch_resp.status_code != 200:
                raise ValidationError(
                    "Form created but questions failed to sync.\n%s" % batch_resp.text
                )

        # STEP 3 ── Save form_id + URL back to Odoo
        self.write({
            'google_form_id': form_id,
            'form_url':       responder_uri,
        })
        return True

    def _build_create_item_request(self, question, index):
        """
        Build one batchUpdate 'createItem' payload for *any* question type.

        Google Forms API only supports three real question widget families:
          • textQuestion   – for all plain / typed text questions
          • choiceQuestion – for radio, dropdown, checkboxes
          • dateQuestion   – for date pickers
          • timeQuestion   – for time pickers

        Everything else (email, phone, number, age, address) is a text question
        with optional server-side validation.
        """
        q_type = question.question_type

        # ── Date ──────────────────────────────────────────────────────────
        if q_type == 'DATE':
            question_body = {
                "required": False,
                "dateQuestion": {
                    "includeTime": False,
                    "includeYear": True,
                },
            }

        # ── Time ──────────────────────────────────────────────────────────
        elif q_type == 'TIME':
            question_body = {
                "required": False,
                "timeQuestion": {
                    "duration": False,
                },
            }

        # ── Choice types (Radio / Dropdown / Checkbox) ─────────────────────
        elif q_type in self._CHOICE_TYPES:
            options = [
                {"value": opt.strip()}
                for opt in (question.choices or "").split(",")
                if opt.strip()
            ]
            question_body = {
                "required": False,
                "choiceQuestion": {
                    "type":    self._CHOICE_API_TYPE[q_type],
                    "options": options,
                    "shuffle": False,
                },
            }

        # ── All text-based types: TEXT, PARAGRAPH, EMAIL, PHONE, NUMBER, AGE, ADDRESS
        # Sent as plain textQuestion. Only 'paragraph' bool is valid in the API.
        else:
            # The Google Forms API only accepts `paragraph` (bool) inside
            # textQuestion. Fields like textValidation, validateAsEmail, or
            # pattern do NOT exist in the API and cause a 400 INVALID_ARGUMENT.
            is_paragraph = q_type in self._PARAGRAPH_TYPES
            question_body = {
                "required": False,
                "textQuestion": {"paragraph": is_paragraph},
            }

        return {
            "createItem": {
                "item": {
                    "title":        question.name,
                    "questionItem": {"question": question_body},
                },
                "location": {"index": index},
            }
        }

    # ======================================================================
    # RELATIONAL FIELD RESOLVER
    # ======================================================================

    def _resolve_relational_value(self, field, raw_value):
        """
        Convert a raw string value from a Google Form response into the
        correct Python value expected by the given ir.model.fields record.

        Returns:
            - int              for many2one
            - [(4, id), ...]   for many2many  (ORM command list)
            - None             for one2many   (must be skipped)
            - int/float        for integer/float/monetary
            - bool             for boolean
            - str              for char/text/selection/date/datetime/html/phone/email
            - False            if conversion fails or value is empty
        """
        if not raw_value or not raw_value.strip():
            return False

        ttype = field.ttype

        # ── Relational: Many2one ───────────────────────────────────────────
        if ttype == 'many2one':
            comodel  = field.relation      # e.g. 'res.partner'
            RelModel = self.env[comodel].sudo()
            record   = RelModel.search([('name', 'ilike', raw_value.strip())], limit=1)
            if not record:
                # Auto-create a minimal record so we never crash
                try:
                    record = RelModel.create({'name': raw_value.strip()})
                except Exception:
                    # If model doesn't support plain name creation, skip silently
                    return False
            return record.id

        # ── Relational: Many2many ──────────────────────────────────────────
        elif ttype == 'many2many':
            comodel  = field.relation
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

        # ── Relational: One2many ───────────────────────────────────────────
        elif ttype == 'one2many':
            # one2many lines cannot be set directly on lead create
            return None

        # ── Numeric types ─────────────────────────────────────────────────
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

        # ── Boolean ───────────────────────────────────────────────────────
        elif ttype == 'boolean':
            return raw_value.strip().lower() in ('true', 'yes', '1', 'y', 'on')

        # ── Everything else: char, text, selection, date, datetime,
        #    html, phone, email, etc. ──────────────────────────────────────
        else:
            return raw_value.strip()

    # ======================================================================
    # FETCH RESPONSES → CRM LEADS
    # ======================================================================

    def fetch_responses_create_leads(self):
        """
        Fetch submitted Google Form responses and create crm.lead records.

        Algorithm
        ---------
        1. Pull the live form structure from Google to get a
           questionId → question title map.
        2. Match each Google questionId to the corresponding
           google.form.questions ORM record (by title, case-insensitive).
        3. For each submission:
             a. If the question has lead_field_id set → use
                _resolve_relational_value() to get the right Odoo value.
             b. If no lead_field_id set → apply keyword heuristics
                (name / email / phone / mobile) or fall through to description.
        4. Create one crm.lead per submission.
        """
        if not self.active:
            raise ValidationError("This form is currently not active.")
        access_token = self.refresh_access_token()
        headers = {"Authorization": "Bearer %s" % access_token}

        for form in self:
            if not form.google_form_id:
                continue

            # ----------------------------------------------------------
            # 1️⃣  Fetch form structure → build questionId maps
            # ----------------------------------------------------------
            form_resp = requests.get(
                "https://forms.googleapis.com/v1/forms/%s" % form.google_form_id,
                headers=headers,
                timeout=10,
            )
            if form_resp.status_code != 200:
                continue

            form_data = form_resp.json()

            # google_qid → title string
            title_map = {}
            # google_qid → google.form.questions record (if matched)
            record_map = {}

            for item in form_data.get("items", []):
                q_item = item.get("questionItem") or item.get("questionGroupItem")
                if not q_item:
                    continue

                # Handle both single questions and question groups
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

                    # Match to ORM record by title (case-insensitive)
                    matched = form.question_ids.filtered(
                        lambda q, t=title: q.name.strip().lower() == t.strip().lower()
                    )
                    if matched:
                        record_map[gqid] = matched[0]

            # ----------------------------------------------------------
            # 2️⃣  Fetch responses
            # ----------------------------------------------------------
            resp = requests.get(
                "https://forms.googleapis.com/v1/forms/%s/responses" % form.google_form_id,
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue

            responses_data = resp.json()

            # ----------------------------------------------------------
            # 3️⃣  Process each submission → build lead_vals
            # ----------------------------------------------------------
            for submission in responses_data.get("responses", []):
                answers = submission.get("answers", {})
                lead_vals = {}
                description_lines = []

                for gqid, answer_obj in answers.items():
                    # ── Extract raw answer value ───────────────────────
                    raw_value = self._extract_answer_value(answer_obj)
                    if raw_value is None:
                        raw_value = ""

                    q_title    = title_map.get(gqid, "Unknown Question")
                    orm_q      = record_map.get(gqid)

                    # ── CASE A: Explicit field mapping ─────────────────
                    if orm_q and orm_q.lead_field_id:
                        field      = orm_q.lead_field_id
                        field_name = field.name

                        # one2many → skip (can't set on create)
                        if field.ttype == 'one2many':
                            description_lines.append(
                                "%s: %s  [one2many — skipped]" % (q_title, raw_value)
                            )
                            continue

                        resolved = self._resolve_relational_value(field, raw_value)

                        if resolved is None or resolved is False:
                            # Nothing valid to set
                            if raw_value:
                                description_lines.append("%s: %s" % (q_title, raw_value))
                            continue

                        # many2many → accumulate ORM commands
                        if field.ttype == 'many2many':
                            existing = lead_vals.get(field_name, [])
                            lead_vals[field_name] = existing + resolved
                        else:
                            lead_vals[field_name] = resolved

                    # ── CASE B: No mapping — keyword heuristics ────────
                    else:
                        lower_title = q_title.lower().strip()

                        if lower_title in ('name', 'full name', 'your name', 'contact name'):
                            lead_vals.setdefault('name', raw_value)

                        elif lower_title in ('email', 'email address', 'e-mail', 'your email'):
                            lead_vals.setdefault('email_from', raw_value)

                        elif lower_title in ('phone', 'phone number', 'contact number', 'telephone'):
                            lead_vals.setdefault('phone', raw_value)

                        elif lower_title in ('mobile', 'mobile number', 'cell', 'cell phone'):
                            lead_vals.setdefault('mobile', raw_value)

                        elif lower_title in ('company', 'company name', 'organisation', 'organization'):
                            lead_vals.setdefault('partner_name', raw_value)

                        elif lower_title in ('website', 'website url', 'web'):
                            lead_vals.setdefault('website', raw_value)

                        elif lower_title in ('address', 'street address', 'your address'):
                            lead_vals.setdefault('street', raw_value)

                        elif lower_title in ('city',):
                            lead_vals.setdefault('city', raw_value)

                        elif lower_title in ('zip', 'zip code', 'postal code', 'postcode'):
                            lead_vals.setdefault('zip', raw_value)

                        else:
                            # Anything unmapped → description
                            if raw_value:
                                description_lines.append("%s: %s" % (q_title, raw_value))

                # ── Smart lead name ───────────────────────────────────
                # Priority:
                #   1. Explicit 'name' field already in lead_vals (mapped question)
                #   2. partner_id resolved → "<Partner Name>'s Opportunity"
                #   3. partner_name (company) captured → "<Company>'s Opportunity"
                #   4. email_from captured → "<email>'s Opportunity"
                #   5. Fallback → "<Form Name>'s Opportunity"
                if not lead_vals.get('name'):
                    partner_id = lead_vals.get('partner_id')
                    if partner_id:
                        partner_rec = self.env['res.partner'].sudo().browse(partner_id)
                        lead_vals['name'] = "%s's Opportunity" % (partner_rec.name or form.name)
                    elif lead_vals.get('partner_name'):
                        lead_vals['name'] = "%s's Opportunity" % lead_vals['partner_name']
                    elif lead_vals.get('email_from'):
                        lead_vals['name'] = "%s's Opportunity" % lead_vals['email_from']
                    else:
                        lead_vals['name'] = "%s's Opportunity" % form.name

                # ── Append unmapped Q&A to description ────────────────
                if description_lines:
                    existing_desc = lead_vals.get('description', '')
                    extra = "\n".join(description_lines)
                    lead_vals['description'] = (
                        "%s\n%s" % (existing_desc, extra)
                    ).strip() if existing_desc else extra

                # ── Link to the form's own lead/opportunity ───────────
                if form.lead_id:
                    lead_vals.setdefault('parent_id', form.lead_id.id)

                self.env['crm.lead'].sudo().create(lead_vals)

    # ======================================================================
    # ANSWER VALUE EXTRACTOR
    # ======================================================================

    def _extract_answer_value(self, answer_obj):
        """
        Extract a plain string value from a Google Forms answer object.

        Google Forms returns answers in different shapes depending on question type:

          textAnswers   – TEXT, PARAGRAPH, EMAIL, PHONE, NUMBER, AGE, ADDRESS,
                          MULTIPLE_CHOICE (single), DROPDOWN
          fileUploadAnswers – file uploads (not supported here)
          textAnswers with multiple entries – CHECKBOX (multi-select)
          date          – DATE question
          time          – TIME question
          grade         – graded questions (ignored here)

        Returns a single string (or comma-joined string for multi-select).
        """
        if not answer_obj:
            return ""

        # ── textAnswers (most common) ──────────────────────────────────────
        text_answers = answer_obj.get("textAnswers", {}).get("answers", [])
        if text_answers:
            # For CHECKBOX, there can be multiple entries → join with comma
            return ", ".join(
                a.get("value", "") for a in text_answers if a.get("value", "")
            )

        # ── Date answer ────────────────────────────────────────────────────
        date_ans = answer_obj.get("date")
        if date_ans:
            year  = date_ans.get("year", "")
            month = str(date_ans.get("month", "")).zfill(2)
            day   = str(date_ans.get("day", "")).zfill(2)
            return "%s-%s-%s" % (year, month, day) if year else ""

        # ── Time answer ────────────────────────────────────────────────────
        time_ans = answer_obj.get("time")
        if time_ans:
            hour   = str(time_ans.get("hours", 0)).zfill(2)
            minute = str(time_ans.get("minutes", 0)).zfill(2)
            return "%s:%s" % (hour, minute)

        return ""



# # -*- coding: utf-8 -*-
# #############################################################################
# #
# #    Cyllo Pvt. Ltd.
# #
# #    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
# #    Author: Cyllo(<https://www.cyllo.com>)
# #
# #    You can modify it under the terms of the GNU LESSER
# #    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
# #
# #    This program is distributed in the hope that it will be useful,
# #    but WITHOUT ANY WARRANTY; without even the implied warranty of
# #    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# #    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
# #
# #    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
# #    (LGPL v3) along with this program.
# #    If not, see <http://www.gnu.org/licenses/>.
# #
# #############################################################################
# from odoo import models, fields, api
# import requests
# from odoo.exceptions import ValidationError
#
#
# class GoogleForm(models.Model):
#     _name = 'google.form'
#     _description = 'Google Form'
#     _order = 'id desc'
#
#     name = fields.Char(required=True)
#     google_form_id = fields.Char(string='Google Form ID', readonly=True)
#     form_url = fields.Char(string='Form URL', readonly=True)
#     lead_id = fields.Many2one('crm.lead', string='Linked Lead')
#     active = fields.Boolean(default=True)
#     question_ids = fields.One2many(
#         'google.form.questions',
#         'google_form_id',
#         string='Questions'
#     )
#
#     # ------------------------------------------------------------------
#     # OAUTH
#     # ------------------------------------------------------------------
#     def refresh_access_token(self):
#         """Refresh Google OAuth access token using stored credentials."""
#         params = self.env['ir.config_parameter'].sudo()
#         refresh_token = params.get_param('cyllo_google.refresh_token')
#         client_id = params.get_param('cyllo_google.client_id')
#         client_secret = params.get_param('cyllo_google.client_secret')
#
#         if not all([refresh_token, client_id, client_secret]):
#             raise ValidationError(
#                 "Google OAuth configuration is incomplete.\n"
#                 "Please fill in Client ID, Client Secret and Refresh Token "
#                 "under Settings > Google Forms Configuration."
#             )
#
#         response = requests.post(
#             "https://oauth2.googleapis.com/token",
#             data={
#                 "client_id": client_id,
#                 "client_secret": client_secret,
#                 "refresh_token": refresh_token,
#                 "grant_type": "refresh_token",
#             },
#             timeout=10,
#         )
#
#         if response.status_code != 200:
#             raise ValidationError(f"Token refresh failed: {response.text}")
#
#         result = response.json()
#         access_token = result.get("access_token")
#         if not access_token:
#             raise ValidationError(f"Access token missing in response: {result}")
#
#         # Save latest access token in config parameters
#         params.set_param('cyllo_google.access_token', access_token)
#         return access_token
#
#     # ------------------------------------------------------------------
#     # CREATE / SYNC FORM
#     # ------------------------------------------------------------------
#     def create_google_form(self):
#         """
#         Create a Google Form using Google Forms API.
#         Requires that the access token has `https://www.googleapis.com/auth/forms` scope.
#         """
#         self.ensure_one()
#         access_token = self.refresh_access_token()
#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json",
#         }
#
#         # STEP 1: Create form with title only
#         create_resp = requests.post(
#             "https://forms.googleapis.com/v1/forms",
#             headers=headers,
#             json={"info": {"title": self.name}},
#             timeout=10,
#         )
#         if create_resp.status_code != 200:
#             raise ValidationError(
#                 f"Failed to create Google Form: {create_resp.text}\n"
#                 "Hint: Make sure your refresh token has full 'forms' scope: "
#                 "https://www.googleapis.com/auth/forms"
#             )
#
#         result = create_resp.json()
#         form_id = result.get("formId")
#         responder_uri = result.get("responderUri", "")
#
#         if not form_id:
#             raise ValidationError("Google API did not return a formId.")
#
#         # STEP 2: Push questions via batchUpdate
#         if self.question_ids:
#             batch_requests = [
#                 self._build_create_item_request(q, idx)
#                 for idx, q in enumerate(self.question_ids)
#             ]
#             batch_resp = requests.post(
#                 f"https://forms.googleapis.com/v1/forms/{form_id}:batchUpdate",
#                 headers=headers,
#                 json={"requests": batch_requests},
#                 timeout=15,
#             )
#             if batch_resp.status_code != 200:
#                 raise ValidationError(
#                     f"Form created but questions failed to sync.\n{batch_resp.text}"
#                 )
#
#         # STEP 3: Save form_id + URL back to Odoo record
#         self.write({
#             'google_form_id': form_id,
#             'form_url': responder_uri,
#         })
#         return True
#
#     def _build_create_item_request(self, question, index):
#         """
#         Build one batchUpdate 'createItem' payload for a question.
#         Supports MULTIPLE_CHOICE or TEXT.
#         """
#         if question.question_type == 'MULTIPLE_CHOICE':
#             options = [
#                 {"value": opt.strip()}
#                 for opt in (question.choices or "").split(",")
#                 if opt.strip()
#             ]
#             question_body = {
#                 "required": False,
#                 "choiceQuestion": {
#                     "type": "RADIO",
#                     "options": options,
#                     "shuffle": False,
#                 }
#             }
#         else:
#             # TEXT — short answer
#             question_body = {"required": False,
#                              "textQuestion": {"paragraph": False}}
#
#         return {
#             "createItem": {
#                 "item": {
#                     "title": question.name,
#                     "questionItem": {"question": question_body}
#                 },
#                 "location": {"index": index}
#             }
#         }
#
#     # ------------------------------------------------------------------
#     # FETCH RESPONSES -> CRM LEADS
#     # ------------------------------------------------------------------
#
#     def fetch_responses_create_leads(self):
#         """Fetch submitted responses and create crm.lead records."""
#         access_token = self.refresh_access_token()
#         headers = {"Authorization": f"Bearer {access_token}"}
#
#         for form in self:
#             if not form.google_form_id:
#                 continue
#
#             # -------------------------------
#             # 1️⃣ Fetch Form Structure (Questions)
#             # -------------------------------
#             form_resp = requests.get(
#                 f"https://forms.googleapis.com/v1/forms/{form.google_form_id}",
#                 headers=headers,
#                 timeout=10,
#             )
#             print('Response : ', form_resp.text)
#             if form_resp.status_code != 200:
#                 continue
#
#             form_data = form_resp.json()
#
#             questions_map = {}
#             for item in form_data.get("items", []):
#                 question_item = item.get("questionItem")
#                 if not question_item:
#                     continue
#
#                 question = question_item.get("question")
#                 if not question:
#                     continue
#
#                 question_id = question.get("questionId")
#                 question_title = item.get("title")
#
#                 questions_map[question_id] = question_title
#
#             # -------------------------------
#             # 2️⃣ Fetch Responses
#             # -------------------------------
#             resp = requests.get(
#                 f"https://forms.googleapis.com/v1/forms/{form.google_form_id}/responses",
#                 headers=headers,
#                 timeout=10,
#             )
#             print('Response :', resp.text)
#             if resp.status_code != 200:
#                 continue
#
#             responses_data = resp.json()
#
#             # -------------------------------
#             # 3️⃣ Process Each Submission
#             # -------------------------------
#             for submission in responses_data.get("responses", []):
#                 answers = submission.get("answers", {})
#
#                 lead_vals = {}
#                 description_lines = []
#
#                 for question_id, answer_obj in answers.items():
#                     question_text = questions_map.get(question_id,
#                                                       "Unknown Question")
#
#                     texts = answer_obj.get("textAnswers", {}).get("answers", [])
#                     value = texts[0].get("value", "") if texts else ""
#
#                     # Example Mapping (Customize as needed)
#                     if question_text.lower() == "name":
#                         lead_vals["name"] = value
#                     elif question_text.lower() == "email":
#                         lead_vals["email_from"] = value
#                     else:
#                         description_lines.append(f"{question_text}: {value}")
#
#                 # Default name if not provided
#                 if not lead_vals.get("name"):
#                     lead_vals["name"] = f"Response - {form.name}"
#
#                 lead_vals["description"] = "\n".join(description_lines)
#
#                 self.env["crm.lead"].create(lead_vals)
#
#     # def fetch_responses_create_leads(self):
#     #     """Fetch submitted responses and create crm.lead records."""
#     #     access_token = self.refresh_access_token()
#     #     headers = {"Authorization": f"Bearer {access_token}"}
#     #
#     #     for form in self:
#     #         if not form.google_form_id:
#     #             continue
#     #             # Need a change (Hard code)
#     #         resp = requests.get(
#     #             f"https://forms.googleapis.com/v1/forms/{form.google_form_id}/responses",
#     #             headers=headers,
#     #             timeout=10,
#     #         )
#     #         print('Responses:', resp.text)
#     #         if resp.status_code != 200:
#     #             continue
#     #
#     #         for submission in resp.json().get("responses", []):
#     #             answers = submission.get("answers", {})
#     #             answer_list = list(answers.values())
#     #
#     #             def get_answer(pos):
#     #                 try:
#     #                     texts = answer_list[pos].get("textAnswers", {}).get("answers", [])
#     #                     return texts[0].get("value", "") if texts else ""
#     #                 except (IndexError, KeyError):
#     #                     return ""
#     #
#     #             self.env["crm.lead"].create({
#     #                 "name": get_answer(0) or f"Response - {form.name}",
#     #                 "email_from": get_answer(1),
#     #             })
