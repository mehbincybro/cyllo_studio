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


class CrmLead(models.Model):
    _inherit = 'crm.lead'




    def action_create_survey(self):
        """Action to create the survey."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.survey',
            'view_mode': 'form, kanban',
            'views': [
                (self.env.ref('survey.survey_survey_view_kanban').id, 'kanban'),
                (self.env.ref('survey.survey_survey_view_form').id, 'form'),
            ],
            'target': 'current',
            'context': {
                'default_name': f'{self.display_name} Survey',
                'default_lead_id': self.id,
            },
        }
