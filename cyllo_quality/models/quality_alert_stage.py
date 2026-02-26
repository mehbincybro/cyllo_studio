# -*- coding: utf-8 -*-
from odoo import fields, models


class QualityAlertStages(models.Model):
    _name = 'quality.alert.stage'
    _description = 'Alert Stages'

    name = fields.Char(required=True)
