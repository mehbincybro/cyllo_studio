# -*- coding: utf-8 -*-
from odoo import fields, models


class LoginUserDetail(models.Model):
    """
        Model for storing login details of users.

        This model allows you to store login details for users, including their
        username, the date and time of login (with a default value of the current
        datetime), and the IP address from which the login occurred.
    """
    _name = 'login.user.detail'
    _description = 'Login Details'

    name = fields.Char(string="User Name")
    date_time = fields.Datetime(string="Login Date And Time", default=lambda self: fields.datetime.now())
    ip_address = fields.Char()
