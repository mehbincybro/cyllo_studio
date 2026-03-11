# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskSkill(models.Model):
    _name = 'helpdesk.skill'
    _description = 'Helpdesk Skill'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')


class ResUsers(models.Model):
    _inherit = 'res.users'

    helpdesk_skill_ids = fields.Many2many('helpdesk.skill', string='Helpdesk Skills')
