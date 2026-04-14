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

import re
from odoo import api, fields, models

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    carbon_activity_ids = fields.One2many('carbon.activity', 'workorder_id', string='Carbon Activities')

    @api.depends('time_ids.duration', 'qty_produced')
    def _compute_duration(self):
        super(MrpWorkorder, self)._compute_duration()
        for order in self:
            order._update_carbon_activities()

    def _update_carbon_activities(self):
        """ Automatically write activities in carbon.calc for today's emission. """
        self.ensure_one()
        if not self.company_id.mrp_integration:
            return
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()
        
        # Calculate today's duration including in-progress sessions
        today_recs = self.time_ids.filtered(
            lambda r: r.date_start and fields.Datetime.context_timestamp(self, r.date_start).date() == today
        )
        
        # Calculate today's duration including in-progress sessions in HOURS
        total_duration_hrs = 0.0
        for rec in today_recs:
            if rec.date_end:
                # Based on observation, rec.duration is already in hours (decimal)
                total_duration_hrs += rec.duration
            else:
                # Real-time duration for in-progress session (convert seconds to hours)
                diff = now - rec.date_start
                total_duration_hrs += max(0, diff.total_seconds() / 3600.0)
        
        today_duration_hrs = total_duration_hrs
        if today_duration_hrs <= 0.001:
            return

        # Find the operation
        operation = self.operation_id
        if not operation:
            # Search within company and use more strict matching
            all_routing_ops = self.env['mrp.routing.workcenter'].search([('company_id', '=', self.company_id.id)])
            for op in all_routing_ops:
                # Match exact name (ignoring case)
                if op.name and re.search(f'^{re.escape(self.name)}$', op.name, re.IGNORECASE):
                    operation = op
                    break
        
        if not operation:
            return

        # Find or create today's carbon calculation record
        calc = self.env['carbon.calc'].search([('date', '=', today)], limit=1)
        if not calc:
            calc = self.env['carbon.calc'].create({
                'name': f"Calculations for {today}",
                'date': today,
                'state': 'draft',
            })

        # Find the 'hr' unit
        unit_hr = self.env['carbon.unit'].search([('name', 'ilike', 'hr')], limit=1)

        # For each source in the operation, create/update activities for each factor
        for line in operation.carbon_line_ids:
            source = line.source_id
            all_factors = source.air_factor_ids + source.sound_factor_ids + source.water_factor_ids
            for factor in all_factors:
                existing_activity = self.env['carbon.activity'].search([
                    ('calculation_id', '=', calc.id),
                    ('workorder_id', '=', self.id),
                    ('source_id', '=', source.id),
                    ('factor_id', '=', factor.id),
                ], limit=1)
                
                vals = {
                    'name': self.name,
                    'date': today,
                    'calculation_id': calc.id,
                    'workorder_id': self.id,
                    'source_id': source.id,
                    'factor_id': factor.id,
                    'quantity': today_duration_hrs,
                    'uom_name': unit_hr.id if unit_hr else source.activity_unit.id,
                }
                
                if existing_activity:
                    if abs(existing_activity.quantity - today_duration_hrs) > 0.0001:
                        existing_activity.write({
                            'name': self.name,
                            'quantity': today_duration_hrs
                        })
                else:
                    self.env['carbon.activity'].create(vals)
