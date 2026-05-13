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

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_integration = fields.Boolean(
        related='company_id.mrp_integration',
        readonly=False,
        string='Manufacturing Integration',
        help='Automatically calculate carbon emissions based on manufacturing order operations'
    )

    fleet_integration = fields.Boolean(
        related='company_id.fleet_integration',
        readonly=False,
        string='Fleet Integration',
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.fleet_integration:
            source = self.env['carbon.source'].search([('name', '=', 'car emission')], limit=1)
            if not source:
                unit_km = self.env['carbon.unit'].search([('name', '=', 'km')], limit=1)
                if not unit_km:
                    unit_km = self.env['carbon.unit'].create({'name': 'km'})
                source = self.env['carbon.source'].create({
                    'name': 'car emission',
                    'category': 'other',
                    'activity_unit': unit_km.id,
                })

            gas_co2 = self.env['carbon.gas'].search([('name', 'ilike', 'Carbon Dioxide')], limit=1)
            if not gas_co2:
                gas_co2 = self.env['carbon.gas'].create({'name': 'Carbon Dioxide'})

            # Create per-vehicle factors for all vehicles with CO2 or sound values
            vehicles = self.env['fleet.vehicle'].search([])
            for vehicle in vehicles:
                # Determine CO2 in kg: check vehicle.co2 (g/km), fallback to model.default_co2 (g/km)
                v_co2_gkm = getattr(vehicle, 'co2', 0.0) or 0.0
                if not v_co2_gkm and vehicle.model_id:
                    v_co2_gkm = getattr(vehicle.model_id, 'default_co2', 0.0) or 0.0
                v_co2 = v_co2_gkm / 1000.0

                if v_co2:
                    air_factor = self.env['carbon.factor'].search([
                        ('name', '=', vehicle.name),
                        ('source_id', '=', source.id),
                        ('type', '=', 'air'),
                    ], limit=1)
                    if air_factor:
                        air_factor.write({'factor_value': v_co2})
                    else:
                        self.env['carbon.factor'].create({
                            'name': vehicle.name,
                            'factor_value': v_co2,
                            'source_id': source.id,
                            'gas_id': gas_co2.id,
                            'type': 'air',
                        })

                # Sound emission factor
                v_sound = 0.0
                if vehicle.model_id:
                    v_sound = getattr(vehicle.model_id, 'default_sound', 0.0) or 0.0
                if v_sound:
                    sound_factor = self.env['carbon.factor'].search([
                        ('name', '=', vehicle.name),
                        ('source_id', '=', source.id),
                        ('type', '=', 'sound'),
                    ], limit=1)
                    if sound_factor:
                        sound_factor.write({'factor_value': v_sound})
                    else:
                        self.env['carbon.factor'].create({
                            'name': vehicle.name,
                            'factor_value': v_sound,
                            'source_id': source.id,
                            'type': 'sound',
                        })

    water_cap = fields.Float(
        related='company_id.water_cap',
        readonly=False,
        string='Allocated Water',
        help='Maximum allowed water usage'
    )
    water_unit = fields.Selection(
        related='company_id.water_unit',
        readonly=False,
        string='Unit'
    )
    water_duration = fields.Selection(
        related='company_id.water_duration',
        readonly=False,
        string='Duration'
    )

    carbon_cap = fields.Float(
        related='company_id.carbon_cap',
        readonly=False,
        string='Carbon Cap',
        help='Maximum allowed carbon emissions'
    )
    carbon_unit = fields.Selection(
        related='company_id.carbon_unit',
        readonly=False,
        string='Unit'
    )
    carbon_duration = fields.Selection(
        related='company_id.carbon_duration',
        readonly=False,
        string='Duration'
    )

    enable_credit_transfer = fields.Boolean(
        config_parameter='cyllo_green_metrics.enable_credit_transfer',
        string='Credit Transfer'
    )
