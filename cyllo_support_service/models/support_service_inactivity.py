# -*- coding: utf-8 -*-
from odoo import fields, models


class SupportServiceInactivity(models.Model):
    """ Class defines support service Inactivity model"""
    _name = 'support.service.inactivity'
    _description = 'Support Service Inactivity'

    stage_id = fields.Many2one('support.service.stage', string='Current Stage')
    state_id = fields.Many2one('support.service.stage', string='Stage To Be Converted')
    no_of_inactive_days = fields.Integer(string="Number of inactive days")
    team_id = fields.Many2one('support.service.team')
