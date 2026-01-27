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
from odoo import models, fields


class CrmRecentSummary(models.Model):
    """Summary of recent activities for CRM leads"""
    _name = 'crm.recent.summary'
    _order = 'id desc'

    name = fields.Char(
        string='Activity',
        help='Short description of the change or activity performed on the CRM lead.',
        tracking=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Changed By',
        help='User who performed the change or activity on the CRM lead.'
    )

    change_datetime = fields.Datetime(
        string='Change Date',
        default=fields.Datetime.now,
        help='Date and time when the activity or change occurred.'
    )

    field_name = fields.Char(
        string='Field Name',
        help='Name of the lead field that was modified.'
    )

    old_value = fields.Char(
        string='Before Value',
        help='Previous value of the field before the change.'
    )

    new_value = fields.Char(
        string='After Value',
        help='New value of the field after the change.'
    )

    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        domain=[('type', '=', 'lead')],
        help='CRM lead related to this activity summary.'
    )
