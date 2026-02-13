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

class GoogleFormQuestions(models.Model):
    _name = 'google.form.questions'
    _description = 'Google Form Questions'

    name = fields.Char(required=True, string="Question")
    google_form_id = fields.Many2one('google.form', string="Google Form", ondelete='cascade')
    question_type = fields.Selection([
        ('TEXT', 'Text'),
        ('MULTIPLE_CHOICE', 'Multiple Choice')
    ], required=True, default='TEXT')
    choices = fields.Text("Choices (comma-separated)", help="Only for Multiple Choice questions")