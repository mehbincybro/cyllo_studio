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


class CrmStage(models.Model):
    """Inherit the model to add a fields"""
    _inherit = 'crm.stage'

    type = fields.Selection([
        ('lead', 'Lead Only'),
        ('opportunity', 'Opportunity Only'),
        ('both', 'Both')
    ], string='Type', default='both'
    )

    # Dashboard
    @api.model
    def get_pipeline_stages(self):
        """Get all pipeline stages for dashboard"""
        return self.search([]).read(['name', 'sequence', 'is_won'])
