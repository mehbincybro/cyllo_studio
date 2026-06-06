# -*- coding: utf-8 -*-
from odoo import models, fields


class FrontdeskFrontdesk(models.Model):
    _inherit = 'frontdesk.frontdesk'

    appointment_type_id = fields.Many2one(
        'appointment.type', 
        string='Default Appointment Type',
        help='Default appointment type for walk-in visitors at this station.'
    )
