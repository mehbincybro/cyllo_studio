# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """ Class to define field to res config settings for invoice approval"""
    _inherit = 'res.config.settings'

    contact_office_connector_id = fields.Many2one(
        'cyllo.office.connector', string="Instance synced with contacts",
        config_parameter="cyllo_office_365_connector.contact_office_connector_id",
        help="when an contact created in the office automatically it save in res partner with this connector id")
    contact_office_access_token = fields.Char(
        string="Office 365 Access Token", config_parameter="cyllo_office_365_connector.contact_office_access_token")
    todo_office_connector_id = fields.Many2one(
        'cyllo.office.connector', string="Instance synced with To Do",
        config_parameter="cyllo_office_365_connector.todo_office_connector_id",
        help="when an activity created in the office automatically it save in mail activity with this connector id")
    office_todo_access_token = fields.Char(
        string="Office 365 Access Token", config_parameter="cyllo_office_365_connector.office_todo_access_token")
