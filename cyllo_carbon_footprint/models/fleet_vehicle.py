# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    default_sound = fields.Float(string='Sound Emission', help='Sound emission in dB')
    default_sound_unit = fields.Selection([
        ('db', 'dB'),
    ], string='Sound Unit', default='db')


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    @api.model
    def _get_vehicle_co2_kg(self, vehicle):
        """Return co2 in kg/km: check vehicle.co2 first, then model.default_co2 (g/km -> kg/km)."""
        v_co2 = getattr(vehicle, 'co2', 0.0) or 0.0
        if not v_co2 and vehicle.model_id:
            v_co2 = getattr(vehicle.model_id, 'default_co2', 0.0) or 0.0
        return round(v_co2 / 1000.0, 6) if v_co2 else 0.0

    @api.model
    def _get_vehicle_sound(self, vehicle):
        """Return sound emission in dB from model."""
        if vehicle.model_id:
            return getattr(vehicle.model_id, 'default_sound', 0.0) or 0.0
        return 0.0

    @api.model
    def _ensure_vehicle_factor(self, source, vehicle, factor_type='air'):
        """Find or create a per-vehicle factor under the given source."""
        factor_name = f'{vehicle.name}'
        if factor_type == 'air':
            co2_kg = self._get_vehicle_co2_kg(vehicle)
            if not co2_kg:
                return None
            factor = self.env['carbon.factor'].search([
                ('name', '=', factor_name),
                ('source_id', '=', source.id),
                ('type', '=', 'air'),
            ], limit=1)
            if factor:
                if round(factor.factor_value, 6) != co2_kg:
                    factor.write({'factor_value': co2_kg})
            else:
                gas_co2 = self.env['carbon.gas'].search([('name', 'ilike', 'Carbon Dioxide')], limit=1)
                factor = self.env['carbon.factor'].create({
                    'name': factor_name,
                    'factor_value': co2_kg,
                    'source_id': source.id,
                    'gas_id': gas_co2.id if gas_co2 else False,
                    'type': 'air',
                })
            return factor
        elif factor_type == 'sound':
            sound_val = self._get_vehicle_sound(vehicle)
            if not sound_val:
                return None
            factor = self.env['carbon.factor'].search([
                ('name', '=', factor_name),
                ('source_id', '=', source.id),
                ('type', '=', 'sound'),
            ], limit=1)
            if factor:
                if round(factor.factor_value, 6) != sound_val:
                    factor.write({'factor_value': sound_val})
            else:
                factor = self.env['carbon.factor'].create({
                    'name': factor_name,
                    'factor_value': sound_val,
                    'source_id': source.id,
                    'type': 'sound',
                })
            return factor
        return None

    @api.model
    def _cron_calculate_fleet_emissions(self):
        company = self.env.company
        if not company.fleet_integration:
            _logger.info("Fleet integration not enabled, skipping.")
            return

        today = fields.Date.context_today(self)

        source = self.env['carbon.source'].search([('name', '=', 'car emission')], limit=1)
        if not source:
            _logger.info("Source 'car emission' not found.")
            return

        # Get or create today's calculation record
        calc = self.env['carbon.calc'].search(
            [('date', '=', today), ('state', '!=', 'done')], limit=1
        )
        if not calc:
            calc = self.env['carbon.calc'].create({
                'name': f'Fleet Emission {today.strftime("%Y-%m-%d")}',
                'date': today,
            })

        # Find today's odometer records, latest per vehicle
        odometers_today = self.env['fleet.vehicle.odometer'].search(
            [('date', '=', today)], order='id desc'
        )
        vehicles_processed = {}
        for odom in odometers_today:
            if odom.vehicle_id.id not in vehicles_processed:
                vehicles_processed[odom.vehicle_id.id] = odom

        if not vehicles_processed:
            _logger.info("No odometer records found for today.")
            return

        for vehicle_id, latest_odom in vehicles_processed.items():
            vehicle = latest_odom.vehicle_id

            # Previous odometer record before today
            past_odom = self.env['fleet.vehicle.odometer'].search([
                ('vehicle_id', '=', vehicle.id),
                ('date', '<', today)
            ], order='date desc, id desc', limit=1)

            past_value = 0.0
            if past_odom and past_odom.id != latest_odom.id:
                past_value = past_odom.value

            distance = latest_odom.value - past_value
            if distance <= 0:
                _logger.info(f"Distance <= 0 for {vehicle.name}, skipping.")
                continue

            odometer_unit = getattr(vehicle, 'odometer_unit', 'kilometers')
            if odometer_unit == 'miles':
                distance *= 1.60934

            # --- CO2 / Air emission ---
            air_factor = self._ensure_vehicle_factor(source, vehicle, factor_type='air')
            if air_factor:
                self._upsert_activity(
                    calc=calc,
                    source=source,
                    vehicle=vehicle,
                    factor=air_factor,
                    distance=distance,
                    today=today,
                    label='CO2 Emission',
                )

            # --- Sound emission ---
            sound_factor = self._ensure_vehicle_factor(source, vehicle, factor_type='sound')
            if sound_factor:
                self._upsert_activity(
                    calc=calc,
                    source=source,
                    vehicle=vehicle,
                    factor=sound_factor,
                    distance=distance,
                    today=today,
                    label='Sound Emission',
                )

    @api.model
    def _upsert_activity(self, calc, source, vehicle, factor, distance, today, label):
        """Create or update a carbon activity for a vehicle in a calculation."""
        activity_name = f'{label} for {vehicle.name}'
        existing = self.env['carbon.activity'].search([
            ('calculation_id', '=', calc.id),
            ('source_id', '=', source.id),
            ('factor_id', '=', factor.id),
            ('name', '=', activity_name),
        ], limit=1)

        if existing:
            existing.write({'quantity': distance, 'factor_id': factor.id})
            _logger.info(f"Updated activity '{activity_name}': {distance} km")
        else:
            self.env['carbon.activity'].create({
                'name': activity_name,
                'date': today,
                'calculation_id': calc.id,
                'source_id': source.id,
                'scope_id': source.scope_id.id if source.scope_id else False,
                'uom_name': source.activity_unit.id if source.activity_unit else False,
                'quantity': distance,
                'factor_id': factor.id,
                'state': 'draft',
            })
            _logger.info(f"Created activity '{activity_name}': {distance} km")
