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
from odoo import fields,models

class ModelAccess(models.Model):
    _name = 'model.access'
    _description = 'Model Access'
    _rec_name = 'model_id'

    profile_management_id = fields.Many2one('profile.management',
                                            string='Profile Management ID')
    model_id = fields.Many2one('ir.model',string='Model')
    is_readonly = fields.Boolean('Read-only')
    hide_create = fields.Boolean('Hide Create')
    hide_edit = fields.Boolean('Hide Edit')
    hide_delete = fields.Boolean('Hide Delete')
    hide_archive = fields.Boolean('Hide Archive/Unarchive')
    hide_duplicate = fields.Boolean('Hide Duplicate')
    hide_export = fields.Boolean('Hide Export')
    hide_reports = fields.Boolean('Hide Reports')
    hide_actions = fields.Boolean('Hide Actions')
