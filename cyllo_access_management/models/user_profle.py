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
from odoo import api, fields, models


class UserProfile(models.Model):
    _name = 'user.profile'
    _description = 'User Profile'
    _inherit = 'mail.thread'

    name = fields.Char('Name', required=True, tracking=True, help="Name of the user profile.")
    user_ids = fields.Many2many('res.users', string='User',
                                domain=[('share', '=', False)], required=True,
                                help="Internal Odoo users assigned to this profile.")
    color = fields.Integer('Color',
                           help="Associated color index for the profile tags in views.")
    group_ids = fields.Many2many('res.groups',
                                 default=lambda self: [fields.Command.link(
                                     self.env.ref('base.group_user').id)],
                                 help="Associated Odoo security groups for this profile.")
    access_count = fields.Integer('# Access Rights',
                                  help='Number of access rights that apply '
                                       'to the current user profile',
                                  compute='_compute_accesses_count',
                                  compute_sudo=True)
    rule_count = fields.Integer('# Record Rules',
                                help='Number of record rules that apply to '
                                     'the current user profile',
                                compute='_compute_accesses_count',
                                compute_sudo=True)

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        current_group_ids = res.group_ids.filtered(lambda x: x.id != 1)
        commands = []
        for group in current_group_ids:
            commands.append(fields.Command.link(group.id))

        res.user_ids.write({"groups_id": commands})

        return res

    def write(self, vals):
        previous_group_ids = self.group_ids.filtered(lambda x: x.id != 1)
        previous_user_ids = self.user_ids
        res = super().write(vals)
        if 'user_ids' in vals:
            current_user_ids = self.user_ids
            removed_user_ids = previous_user_ids - current_user_ids
            added_user_ids = current_user_ids - previous_user_ids
            current_group_ids = self.group_ids.filtered(lambda x: x.id != 1)

            commands = []

            if added_user_ids:
                for group in current_group_ids:
                    commands.append(fields.Command.link(group.id))

                added_user_ids.write({"groups_id": commands})

            if removed_user_ids:
                for group in current_group_ids:
                    commands.append(fields.Command.unlink(group.id))

                removed_user_ids.write({"groups_id": commands})

        if 'group_ids' in vals:
            current_group_ids = self.group_ids.filtered(lambda x: x.id != 1)

            remove_group_ids = previous_group_ids - current_group_ids
            add_group_ids = current_group_ids - previous_group_ids

            commands = []

            if add_group_ids:
                for group in add_group_ids:
                    commands.append(fields.Command.link(group.id))

            if remove_group_ids:
                for group in remove_group_ids:
                    commands.append(fields.Command.unlink(group.id))

            if commands:
                self.user_ids.write({"groups_id": commands})

        return res

    def unlink(self):
        current_group_ids = self.group_ids.filtered(lambda x: x.id != 1)
        commands = []

        for group in current_group_ids:
            commands.append(fields.Command.unlink(group.id))

        self.user_ids.write({"groups_id": commands})

        return super().unlink()

    @api.depends('group_ids')
    def _compute_accesses_count(self):
        for profile in self:
            groups = profile.group_ids
            profile.access_count = len(groups.model_access)
            profile.rule_count = len(groups.rule_groups)

    def action_show_access_rights(self):
        self.ensure_one()
        return {
            'name': 'Access Rights',
            'view_mode': 'tree,form',
            'res_model': 'ir.model.access',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.group_ids.model_access.ids)],
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
            'domain': [('id', 'in', self.group_ids.rule_groups.ids)],
            'target': 'current',
        }

    def get_current_company(self):
        return self.env.company
