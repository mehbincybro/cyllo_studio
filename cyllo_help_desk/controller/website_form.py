from odoo import _, tools
from odoo.addons.website.controllers import form
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import plaintext2html


class WebsiteForm(form.WebsiteForm):
    def _parse_custom_values(self, custom):
        custom_values = {}
        for line in (custom or "").splitlines():
            if " : " not in line:
                continue
            key, value = line.split(" : ", 1)
            custom_values[key.strip().lower()] = value.strip()
        return custom_values

    def _get_website_ticket_team(self, values):
        team_id = values.get("team_id")
        if team_id:
            team = request.env["helpdesk.team"].sudo().browse(team_id)
            if not team.exists() or not team.use_website_ticket_creation:
                raise ValidationError(_("Please select a valid helpdesk team."))
            return team
        team = request.env["helpdesk.team"].sudo().search(
            [("use_website_ticket_creation", "=", True)],
            limit=1,
        )
        if not team:
            raise ValidationError(_("No helpdesk team is enabled for website ticket creation."))
        return team

    def _get_or_create_ticket_customer(self, values, custom):
        custom_values = self._parse_custom_values(custom)
        email = tools.email_normalize(values.get("email"))
        phone = values.get("phone")
        partner_name = (
            custom_values.get("name")
            or custom_values.get("contact name")
            or custom_values.get("full name")
            or values.get("partner_name")
            or values.get("contact_name")
            or values.get("name")
            or email
            or _("Website Visitor")
        )
        company_name = custom_values.get("company") or custom_values.get("company name")

        partner = request.env["res.partner"].sudo()
        if email:
            partner = partner.search([("email", "=", email)], limit=1)
        else:
            partner = request.env["res.partner"]

        partner_values = {
            "name": partner_name,
            "email": email or values.get("email"),
            "phone": phone,
            "company_name": company_name,
        }
        if partner:
            partner.write({key: value for key, value in partner_values.items() if value})
            return partner
        return request.env["res.partner"].sudo().create(partner_values)

    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == "helpdesk.ticket":
            team = self._get_website_ticket_team(values)
            partner = self._get_or_create_ticket_customer(values, custom)
            values["team_id"] = team.id
            values["customer_id"] = partner.id
            values["email"] = values.get("email") or partner.email
            values["phone"] = values.get("phone") or partner.phone or partner.mobile
            values["user_id"] = False
            if not values.get("name"):
                custom_values = self._parse_custom_values(custom)
                values["name"] = custom_values.get("subject") or _("Website Ticket")
            if not values.get("description"):
                custom_values = self._parse_custom_values(custom)
                question = custom_values.get("question") or custom_values.get("message")
                if question:
                    values["description"] = plaintext2html(question)
        return super().insert_record(request, model, values, custom, meta=meta)
