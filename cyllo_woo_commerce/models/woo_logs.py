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
from odoo import fields, models


class WooLogs(models.Model):
    """Class for the model Woo Logs. Contains fields for the model."""
    _name = 'woo.logs'
    _rec_name = "trigger"
    _description = "Woo Logs"

    status = fields.Selection(
        selection=[('success', "Success"),
                   ('failed', "Failed")], readonly=True, string="Status",
        help='Status of the process done that related to the woo log. ')
    description = fields.Text(string="Description", readonly=True,
                              help='Description of the woo log.')
    trigger = fields.Selection(selection=[('queue', "Queue"),
                                          ('import', "Import"),
                                          ('export', "Export")],
                               string="Trigger", readonly=True,
                               help='Type of the function triggered that is'
                                    'related to the woo log.')
