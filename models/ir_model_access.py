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
from odoo import models


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    def update_access_rights(self, access_rights_data):
        """Update access rights for matching records."""
        for access in self:
            access_right = next((access_data for access_data in access_rights_data if access_data.get('id') == access.id), None)
            if access_right:
                access.update({
                    'name': access_right['name'],
                    'group_id': access_right['group_id'][0],
                    'perm_read': access_right['perm_read'],
                    'perm_write': access_right['perm_write'],
                    'perm_create': access_right['perm_create'],
                    'perm_unlink': access_right['perm_unlink']
                })