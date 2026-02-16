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
from odoo.exceptions import ValidationError


class GoogleFormQuestions(models.Model):
    _name = 'google.form.questions'
    _description = 'Google Form Questions'

    name = fields.Char(required=True, string="Question")
    google_form_id = fields.Many2one(
        'google.form', string="Google Form", ondelete='cascade'
    )

    question_type = fields.Selection([
        # ── Plain text inputs ──────────────────────────────────────────
        ('TEXT',      'Short Text'),
        ('PARAGRAPH', 'Paragraph / Long Text'),

        # ── Typed inputs (validated by Google as text questions) ───────
        ('EMAIL',  'Email'),
        ('PHONE',  'Phone Number'),
        ('NUMBER', 'Number'),
        ('AGE',    'Age'),

        # ── Date / Time ────────────────────────────────────────────────
        ('DATE', 'Date'),
        ('TIME', 'Time'),

        # ── Address (free-text block) ──────────────────────────────────
        ('ADDRESS', 'Address'),

        # ── Choice inputs ──────────────────────────────────────────────
        ('MULTIPLE_CHOICE', 'Multiple Choice (Radio)'),
        ('DROPDOWN',        'Dropdown'),
        ('CHECKBOX',        'Checkboxes (Multi-select)'),
    ], required=True, default='TEXT', string="Question Type")

    choices = fields.Text(
        string="Choices (comma-separated)",
        help="Required for Multiple Choice, Dropdown, and Checkbox question types."
    )

    lead_field_id = fields.Many2one(
        'ir.model.fields',
        domain=[('model', '=', 'crm.lead')],
        string='Map to Lead Field',
        help="Select which CRM Lead field this question's answer should be saved to."
    )

    # Computed flag used by the view to show/hide Choices textarea
    show_choices = fields.Boolean(compute='_compute_show_choices', store=False)

    @api.depends('question_type')
    def _compute_show_choices(self):
        choice_types = {'MULTIPLE_CHOICE', 'DROPDOWN', 'CHECKBOX'}
        for rec in self:
            rec.show_choices = rec.question_type in choice_types

    @api.constrains('question_type', 'choices')
    def _check_choices_required(self):
        choice_types = {'MULTIPLE_CHOICE', 'DROPDOWN', 'CHECKBOX'}
        for rec in self:
            if rec.question_type in choice_types and not (rec.choices or '').strip():
                raise ValidationError(
                    "Question '%s': Choices are required for '%s' questions." % (
                        rec.name,
                        dict(rec._fields['question_type'].selection).get(rec.question_type, ''),
                    )
                )













# # -*- coding: utf-8 -*-
# #############################################################################
# #
# #    Cyllo Pvt. Ltd.
# #
# #    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
# #    Author: Cyllo(<https://www.cyllo.com>)
# #
# #    You can modify it under the terms of the GNU LESSER
# #    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
# #
# #    This program is distributed in the hope that it will be useful,
# #    but WITHOUT ANY WARRANTY; without even the implied warranty of
# #    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# #    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
# #
# #    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
# #    (LGPL v3) along with this program.
# #    If not, see <http://www.gnu.org/licenses/>.
# #
# #############################################################################
# from odoo import models, fields
#
# class GoogleFormQuestions(models.Model):
#     _name = 'google.form.questions'
#     _description = 'Google Form Questions'
#
#     name = fields.Char(required=True, string="Question")
#     google_form_id = fields.Many2one('google.form', string="Google Form", ondelete='cascade')
#     question_type = fields.Selection([
#         ('TEXT', 'Text'),
#         ('MULTIPLE_CHOICE', 'Multiple Choice')
#     ], required=True, default='TEXT')
#     choices = fields.Text("Choices (comma-separated)", help="Only for Multiple Choice questions")
#     lead_field_id = fields.Many2one(
#         'ir.model.fields',
#         domain=[('model', '=', 'crm.lead')],
#         string='Lead Field',
#         help="Select the CRM Lead field to map this question's answer to."
#     )