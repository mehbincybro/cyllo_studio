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
##############################################################################
from odoo import models


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _mark_done(self):
        res = super()._mark_done()
        for user_input in self:
            if user_input.survey_id.create_lead:
                lead_vals = {
                    'name': f"{user_input.survey_id.title} - {user_input.partner_id.name if user_input.partner_id else 'Anonymous'}",
                    'type': 'lead',
                }
                for line in user_input.user_input_line_ids:
                    if line.question_id.lead_field_id:
                        field_name = line.question_id.lead_field_id.name
                        value = False
                        if line.answer_type == 'char_box':
                            value = line.value_char_box
                        elif line.answer_type == 'text_box':
                            value = line.value_text_box
                        elif line.answer_type == 'numerical_box':
                            value = line.value_numerical_box
                        elif line.answer_type == 'date':
                            value = line.value_date
                        elif line.answer_type == 'datetime':
                            value = line.value_datetime
                        elif line.answer_type == 'suggestion':
                            value = line.suggested_answer_id.value

                        if value:
                            lead_vals[field_name] = value

                if lead_vals:
                    self.env['crm.lead'].create(lead_vals)

        return res
