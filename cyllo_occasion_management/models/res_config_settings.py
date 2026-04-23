# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Inherit the model res.config.settings to add Additional fields"""
    _inherit = 'res.config.settings'

    is_extra = fields.Boolean(string='Apply Extra Amount',
                              config_parameter='cyllo_occasion_management.is_extra',
                              help="Enable, if extra charge want to add")
    extra_amount = fields.Float(string='Extra Amount',
                                config_parameter='cyllo_occasion_management.extra_amount',
                                help='Enter extra amount/KM')
    is_fleet_integrated = fields.Boolean(string='Integrate Fleet',
                                         config_parameter='cyllo_occasion_management.is_fleet_integrated')

    def set_values(self):
        """Handle manual installation/uninstallation of modules based on settings"""
        res = super(ResConfigSettings, self).set_values()
        integration_module = self.env['ir.module.module'].search([('name', '=', 'cyllo_occasion_fleet')])
        fleet_module = self.env['ir.module.module'].search([('name', '=', 'fleet')])

        if self.is_fleet_integrated:
            if integration_module.state != 'installed':
                integration_module.button_immediate_install()
        else:
            # If turning off, uninstall both
            if integration_module.state == 'installed':
                integration_module.button_immediate_uninstall()
            if fleet_module.state == 'installed':
                # Only uninstall fleet if it's specifically requested and safe
                fleet_module.button_immediate_uninstall()
        return res
