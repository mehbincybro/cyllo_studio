# -*- coding: utf-8 -*-
from odoo import fields, models


class ResignedReasons(models.Model):
    """New model for resigned reasons"""
    _name = 'resigned.reasons'
    _description = 'Resigned Reasons'

    name = fields.Char(string='Resignation Reason', required=True, help='To add the reason for resignation')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
