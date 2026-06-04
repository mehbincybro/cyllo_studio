# -*- coding: utf-8 -*-
from odoo import models, fields

class FrontdeskDrink(models.Model):
    _name = 'frontdesk.drink'
    _description = 'Frontdesk Drink'
    _order = 'sequence, id'

    name = fields.Char(string='Drink Name', required=True, translate=True)
    sequence = fields.Integer(default=10, string='Sequence')
    notify_user_ids = fields.Many2many('hr.employee', string='People to Notify', help='Employees to notify when this drink is selected')
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    active = fields.Boolean(default=True, string='Active')
