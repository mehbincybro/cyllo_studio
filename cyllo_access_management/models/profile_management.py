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
from odoo import api,fields,models

class ProfileManagement(models.Model):
    _name = 'profile.management'
    _description = 'Profile Management'
    _inherit = 'mail.thread'

    name = fields.Char('Name',required=True,tracking=True)
    company_ids = fields.Many2many('res.company',string='Companies')
    profile_ids = fields.Many2many('user.profile',string='Profiles',
                                   required=True)
    is_readonly = fields.Boolean('Profile System Readonly')
    disable_chatter = fields.Boolean('Disable Chatter')
    disable_debug_mode = fields.Boolean('Disable Debug Mode')
    disable_login = fields.Boolean('Disable Login')
    menu_ids = fields.Many2many('ir.ui.menu',string='Menus')
    hide_buttons_tabs_ids = fields.One2many('hide.buttons.tabs',
                                            'profile_management_id',
                                            string='Hide Buttons and Tabs')
    hide_filters_ids = fields.One2many('hide.filters',
                                   'profile_management_id',
                                   string='Hide Filters and Groups')
    field_access_ids = fields.One2many('field.access',
                                       'profile_management_id',
                                       string='Field Access')
    model_access_ids = fields.One2many('model.access',
                                       'profile_management_id',
                                       string='Model Access')
    domain_access_ids = fields.One2many('domain.access',
                                       'profile_management_id',
                                       string='Domain Access')
    access_count = fields.Integer('# Access Rights',
                                    help='Number of access rights that apply '
                                         'to the current user profile',
                                    compute='_compute_accesses_count',
                                    compute_sudo=True)
    rule_count = fields.Integer('# Record Rules',
                                 help='Number of record rules that apply to '
                                      'the current profile management',
                                 compute='_compute_accesses_count',
                                 compute_sudo=True)
    user_count = fields.Integer('# Users',
                                help='Number of users that apply to '
                                     'the current user profile management',
                                compute='_compute_user_count',
                                )
    is_activated = fields.Boolean('Active',default=True)

    @api.depends('profile_ids')
    def _compute_accesses_count(self):
        for record in self:
            groups = record.profile_ids.group_ids
            record.access_count = len(groups.model_access)
            record.rule_count = len(groups.rule_groups)

    @api.depends('profile_ids')
    def _compute_user_count(self):
        for record in self:
            users = record.profile_ids.user_ids
            record.user_count = len(users)

    def action_show_users(self):
        self.ensure_one()
        return {
            'name': 'Users',
            'view_mode': 'tree,form',
            'res_model': 'res.users',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in',
                        self.profile_ids.user_ids.ids)],
            'target': 'current',
        }

    def action_show_access_rights(self):
        self.ensure_one()
        return {
            'name': 'Access Rights',
            'view_mode': 'tree,form',
            'res_model': 'ir.model.access',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in',
                        self.profile_ids.group_ids.model_access.ids)],
            'target': 'current',
        }

    def action_show_record_rules(self):
        self.ensure_one()
        return {
            'name': 'Record Rules',
            'view_mode': 'tree,form',
            'res_model': 'ir.rule',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in',
                        self.profile_ids.group_ids.rule_groups.ids)],
            'target': 'current',
        }

    @api.model
    def get_profile_flags(self, model):
        user = self.env.user
        profiles = user.profile_ids
        company_id = self.env.company.id
        actions = []
        hide_print = False
        hide_action = False
        if profiles:
            access_mgmt = self.sudo().search([
            ('profile_ids', 'in', profiles.ids),('is_activated','=',True),"|",
            ('company_ids','in',[company_id]),('company_ids','=',False)
            ])
            if access_mgmt:
                model_rules = access_mgmt.model_access_ids.filtered(
                    lambda r: r.model_id.model == model
                )
                if any(model_rules.mapped('hide_archive')):
                    actions += ["archive","unarchive"]
                if any(model_rules.mapped('hide_export')):
                    actions += ["export"]
                if any(model_rules.mapped('hide_reports')):
                    hide_print = True
                if any(model_rules.mapped('hide_actions')):
                    hide_action = True

        return {
            'actions' : actions,
            'hide_print' : hide_print,
            'hide_actions': hide_action,
        }
