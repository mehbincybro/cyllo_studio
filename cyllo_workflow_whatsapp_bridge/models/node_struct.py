# -*- coding: utf-8 -*-

from odoo import fields, models


class NodeStruct(models.Model):
    _inherit = "node.struct"

    whatsapp_record = fields.Json(string="WhatsApp Record")
    whatsapp_template = fields.Json(string="WhatsApp Template")
    whatsapp_partner_ids = fields.Json(string="WhatsApp Recipients")
    whatsapp_isTemplate = fields.Boolean(string="WhatsApp Is Template")
    whatsapp_message = fields.Char(string="WhatsApp Message")
