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

    # ------------------------------------------------------------------
    # OAUTH
    # ------------------------------------------------------------------
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
                "under Settings > Google Forms Configuration."
            )

        response = requests.post(
            "https://oauth2.googleapis.com/token",
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
            raise ValidationError(f"Access token missing in response: {result}")

        # Save latest access token in config parameters
        params.set_param('cyllo_google.access_token', access_token)
        return access_token

    # ------------------------------------------------------------------
    # CREATE / SYNC FORM
    # ------------------------------------------------------------------
    def create_google_form(self):
        """
        Create a Google Form using Google Forms API.
        Requires that the access token has `https://www.googleapis.com/auth/forms` scope.
        """
        self.ensure_one()
        access_token = self.refresh_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # STEP 1: Create form with title only
        create_resp = requests.post(
            "https://forms.googleapis.com/v1/forms",
            headers=headers,
            json={"info": {"title": self.name}},
            timeout=10,
        )
        if create_resp.status_code != 200:
            raise ValidationError(
                f"Failed to create Google Form: {create_resp.text}\n"
                "Hint: Make sure your refresh token has full 'forms' scope: "
                "https://www.googleapis.com/auth/forms"
            )

        result = create_resp.json()
        form_id = result.get("formId")
        responder_uri = result.get("responderUri", "")

        if not form_id:
            raise ValidationError("Google API did not return a formId.")

        # STEP 2: Push questions via batchUpdate
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

        # STEP 3: Save form_id + URL back to Odoo record
        self.write({
            'google_form_id': form_id,
            'form_url': responder_uri,
        })
        return True

    def _build_create_item_request(self, question, index):
        """
        Build one batchUpdate 'createItem' payload for a question.
        Supports MULTIPLE_CHOICE or TEXT.
        """
        if question.question_type == 'MULTIPLE_CHOICE':
            options = [
                {"value": opt.strip()}
                for opt in (question.choices or "").split(",")
                if opt.strip()
            ]
            question_body = {
                "required": False,
                "choiceQuestion": {
                    "type": "RADIO",
                    "options": options,
                    "shuffle": False,
                }
            }
        else:
            # TEXT — short answer
            question_body = {"required": False, "textQuestion": {"paragraph": False}}

        return {
            "createItem": {
                "item": {
                    "title": question.name,
                    "questionItem": {"question": question_body}
                },
                "location": {"index": index}
            }
        }

    # ------------------------------------------------------------------
    # FETCH RESPONSES -> CRM LEADS
    # ------------------------------------------------------------------
    def fetch_responses_create_leads(self):
        """Fetch submitted responses and create crm.lead records."""
        access_token = self.refresh_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        for form in self:
            if not form.google_form_id:
                continue
            resp = requests.get(
                f"https://forms.googleapis.com/v1/forms/{form.google_form_id}/responses",
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue

            for submission in resp.json().get("responses", []):
                answers = submission.get("answers", {})
                answer_list = list(answers.values())

                def get_answer(pos):
                    try:
                        texts = answer_list[pos].get("textAnswers", {}).get("answers", [])
                        return texts[0].get("value", "") if texts else ""
                    except (IndexError, KeyError):
                        return ""

                self.env["crm.lead"].create({
                    "name": get_answer(0) or f"Response - {form.name}",
                    "email_from": get_answer(1),
                })

