# -*- coding: utf-8 -*-
import pytz

from odoo.http import request
from odoo import api, fields, models

# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728

def _tz_get():
    """
        Get a list of timezones.

        :param self: Model instance.
        :return: list: List of timezones.
        """
    return [(tz, tz) for tz in sorted(pytz.all_timezones,
                                  key=lambda tz: tz if not tz.startswith(
                                      'Etc/') else '_')]


class ResUsers(models.Model):
    """
        Model for extending user details.
        """
    _inherit = 'res.users'

    idle_timer = fields.Boolean(help="Enable idle timer to set idle time")
    idle_time = fields.Integer(string="Idle Time (In minutes)", default=10,
                               help="Set idle time for user. You will be logged out from the session"
                                    " once the timer ends")
    api_key = fields.Char(help="API key from OpenWeatherMap")
    location_set = fields.Selection(
        selection=[('auto', 'Use Browser Location'), ('manual', 'Manual Location')],
        string="Set Location", default='auto',
        help="Use Browser Location: Fetching data based on browsers location, Manual Location:Need to specify the city"
             " in the city field")
    city = fields.Char()
    # SQL constraints
    _sql_constraints = [
        ('positive_idle_time', 'CHECK(idle_time >= 1)', 'Idle Time should be a greater than or equal to one minute.'),
    ]

    @api.model
    def _check_credentials(self, password, user_agent_env):
        """
            Check user credentials and log login details.
        """
        res = super(ResUsers, self)._check_credentials(password, user_agent_env)
        ip_address = request.httprequest.environ['REMOTE_ADDR']
        vals = {
            'name': self.name,
            'ip_address': ip_address
        }
        self.env['login.user.detail'].sudo().create(vals)
        return res

    @api.model
    def get_current_user_details(self):
        """
         Retrieves details of currently logged-in users
        """
        current_user = self.env.user
        return {
            'id': current_user.id,
            'name': current_user.name,
            'image': current_user.image_1920,
            'language': self.env['res.lang'].search([('code', '=', current_user.lang)]).id,
            'active_lang': [{'id': lang.id, 'name': lang.name, 'code': lang.code}
                            for lang in self.env['res.lang'].search([('active', '=', True)])],
            'work_email': current_user.email,
            'timezone': _tz_get(),
            'current_tz': current_user.tz,
            'notif_type': current_user.notification_type,
            'odoobot_state': current_user.odoobot_state,
        }

    @api.model
    def get_non_admin_user_details(self, user_id):
        """
         Retrieves details of currently logged in non-admin user
        """
        current_user = self.env.user
        allowed_companies = [company.search_read([], ['id', 'name', 'email', 'phone', 'currency_id', 'parent_id', 'vat',
                                                      'street', 'street2', 'state_id', 'country_id', 'zip'])
                             for company in current_user.company_ids if company]
        return {
            'signature': current_user.signature,
            'groups_id': current_user.groups_id.ids,
            'model_access': current_user.groups_id.model_access.ids,
            'rule_groups': current_user.groups_id.rule_groups.ids,
            'action_id': current_user.action_id.name,
            'phone': current_user.partner_id.phone,
            'country': current_user.partner_id.country_id.name,
            'state': current_user.partner_id.state_id.name,
            'street': current_user.partner_id.street,
            'street2': current_user.partner_id.street2,
            'zip': current_user.partner_id.zip,
            'allowed_companies': allowed_companies,
            'job_position': current_user.employee_id.job_id.name
            if hasattr(current_user, 'employee_id') and current_user.employee_id else False,
            'default_company': {'id': current_user.company_id.id, 'name': current_user.company_id.name},
        }

    @api.model
    def get_change_pwd_view_id(self):
        """
            Retrieve the ID of the 'Change Password' dashboard form view.
        """
        return self.env.ref('cyllo_dashboard.view_change_password_own_form').id

    @api.model
    def get_groups(self):
        """
            Retrieve the IDs of the groups associated with the current user.
        """
        return self.env.user.groups_id.ids

    @api.model
    def toggle_auto_edit(self, auto_edit):
        self.env.user.sudo().write({
            'auto_edit': auto_edit
        })

    @api.model
    def get_auto_edit_value(self):
        return self.env.user.auto_edit


class ChangePasswordOwn(models.TransientModel):
    """
        Model for changing own password.
        """
    _inherit = "change.password.own"

    def action_change_password_dashboard(self):
        """
        Change password through dashboard.

        :return: dict: Action to reload.
                """
        self.env.user._change_password(self.new_password)
        self.unlink()
        # reload to avoid a session expired error
        # would be great to update the session id in-place, but it seems dicey
        return {'type': 'ir.actions.client', 'tag': 'reload'}
