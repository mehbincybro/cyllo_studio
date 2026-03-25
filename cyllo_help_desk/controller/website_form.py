from odoo import _, tools
from odoo.addons.website.controllers import form
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import plaintext2html


class WebsiteForm(form.WebsiteForm):

    def _get_website_ticket_team(self, values):
        team_id = values.get("team_id")
        if team_id:
            team = request.env["helpdesk.team"].sudo().browse(int(team_id))
            if not team.exists() or not team.use_website_ticket_creation:
                raise ValidationError(_("Invalid Helpdesk Team"))
            return team
        team = request.env["helpdesk.team"].sudo().search(
            [("use_website_ticket_creation", "=", True)], limit=1
        )
        if not team:
            raise ValidationError(_("No Helpdesk Team enabled for website"))

        return team

    def _get_or_create_partner(self, values):
        email = tools.email_normalize(values.get("email"))
        phone = values.get("phone")
        name = values.get("partner_name") or email or _("Website Visitor")

        partner = request.env["res.partner"].sudo()
        if email:
            partner = partner.search([("email", "=", email)], limit=1)

        if partner:
            partner.write({
                "name": name,
                "phone": phone,
            })
            return partner

        return request.env["res.partner"].sudo().create({
            "name": name,
            "email": email,
            "phone": phone,
        })

    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == "helpdesk.ticket":
            # Team
            team = self._get_website_ticket_team(values)
            # Partner
            partner = self._get_or_create_partner(values)
            # Assign values
            values.update({
                "team_id": team.id,
                "customer_id": partner.id,
                "email": values.get("email"),
                "description": values.get("description") or _("No description"),
            })

            # Ensure subject exists
            if not values.get("name"):
                values["name"] = _("Website Ticket")
        return super().insert_record(request, model, values, custom, meta=meta)
