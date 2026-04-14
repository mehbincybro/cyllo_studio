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
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CarbonActivity(models.Model):
    _name = 'carbon.activity'
    _description = 'Carbon Activity'
    _order = 'date, name'

    name = fields.Char(required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    calculation_id = fields.Many2one('carbon.calc', ondelete='set null')
    source_id = fields.Many2one('carbon.source', required=True, ondelete='restrict')
    scope_id = fields.Many2one('carbon.scope', ondelete='restrict')
    quantity = fields.Float(required=True)
    uom_name = fields.Many2one('carbon.unit', string='Unit')
    factor_id = fields.Many2one(
        'carbon.factor',
        ondelete='restrict',
        domain="[('source_id', '=', source_id)]",
    )
    gas_id = fields.Many2one('carbon.gas', ondelete='restrict')
    factor_value = fields.Float(related='factor_id.factor_value',store=True,readonly=True)
    emission_total = fields.Float(string='Emissions', compute='_compute_emissions', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    cost_total = fields.Monetary(string='Cost')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', required=True)
    note = fields.Text()
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', ondelete='set null')

    @api.onchange('source_id')
    def _onchange_source_id(self):
        if self.source_id:
            self.uom_name = self.source_id.activity_unit
            self.scope_id = self.source_id.scope_id

    @api.onchange('factor_id')
    def _onchange_factor_id(self):
        if self.factor_id:
            self.gas_id = self.factor_id.gas_id
            # Stop overwriting uom_name with factor unit; it must stay as source activity unit
            if self.source_id and self.source_id.activity_unit:
                self.uom_name = self.source_id.activity_unit

    @api.constrains('quantity', 'factor_value')
    def _check_values(self):
        for rec in self:
            if rec.quantity < 0 or rec.factor_value < 0:
                raise ValidationError('Quantity and factor must be non-negative.')

    @api.depends('quantity', 'factor_value')
    def _compute_emissions(self):
        for rec in self:
            rec.emission_total = rec.quantity * rec.factor_value if rec.quantity and rec.factor_value else 0.0

    def action_apply_rules(self):
        rules = self.env['carbon.assign.rule'].search([
            ('model_id.model', '=', 'carbon.activity'),
            ('active', '=', True),
        ], order='priority, id')
        for rec in self:
            if rec.factor_id:
                continue
            for rule in rules:
                if rule._match(rec):
                    rec.source_id = rule.source_id
                    if rule.factor_id:
                        rec.factor_id = rule.factor_id
                        rec.gas_id = rule.factor_id.gas_id
                    break

    def action_mark_done(self):
        if not self.env.user.has_group('cyllo_green_metrics.group_carbon_manager'):
            from odoo.exceptions import ValidationError
            raise ValidationError("Only a Green Metrics Manager can move an activity to Done state.")
        for rec in self:
            rec.state = 'done'

    def action_compute(self):
        for rec in self:
            if not rec.factor_value:
                raise ValidationError('Selected factor has no value.')
            rec.state = 'done'

    @api.model
    def _get_initiative_stats(self, xml_id, start_date=False, end_date=False, scope_filter='all'):
        project = self.env.ref(xml_id, raise_if_not_found=False)
        ideas_cnt, prog_cnt, done_cnt, total_cnt = 0, 0, 0, 0
        idea_stage_id, prog_stage_id, done_stage_id = False, False, False
        total_reduced_kg = 0.0
        total_recycled_water = 0.0

        if project:
            stages = self.env['project.task.type'].search([('project_ids', 'in', project.id)])
            idea_stage = stages.filtered(lambda s: 'Ideas' in s.name)
            prog_stage = stages.filtered(lambda s: 'Progress' in s.name)
            done_stage = stages.filtered(lambda s: 'Done' in s.name)
            
            idea_stage_id = idea_stage.id if idea_stage else False
            prog_stage_id = prog_stage.id if prog_stage else False
            done_stage_id = done_stage.id if done_stage else False

            domain = [('project_id', '=', project.id)]
            if start_date:
                domain.append(('create_date', '>=', start_date))
            if end_date:
                domain.append(('create_date', '<=', end_date))
            
            if scope_filter == 'available':
                domain.append(('scope_id', '!=', False))
            elif scope_filter == 'no_scope':
                domain.append(('scope_id', '=', False))
            elif scope_filter and scope_filter != 'all':
                try:
                    scope_id = int(scope_filter)
                    domain.append(('scope_id', '=', scope_id))
                except (ValueError, TypeError):
                    pass

            tasks_aggr = self.env['project.task'].read_group(domain, ['stage_id', 'reduced_emissions:sum', 'recycled_water:sum'], ['stage_id'])
            for t_grp in tasks_aggr:
                cnt = t_grp['stage_id_count']
                total_cnt += cnt
                s_id = t_grp['stage_id'][0] if t_grp.get('stage_id') else False
                if idea_stage_id and s_id == idea_stage_id:
                    ideas_cnt += cnt
                elif prog_stage_id and s_id == prog_stage_id:
                    prog_cnt += cnt
                elif done_stage_id and s_id == done_stage_id:
                    done_cnt += cnt
                    total_reduced_kg += t_grp.get('reduced_emissions', 0.0)
                    total_recycled_water += t_grp.get('recycled_water', 0.0)
        
        return {
            'project_id': project.id if project else False,
            'idea_stage_id': idea_stage_id,
            'prog_stage_id': prog_stage_id,
            'done_stage_id': done_stage_id,
            'ideas_cnt': ideas_cnt,
            'prog_cnt': prog_cnt,
            'done_cnt': done_cnt,
            'total_cnt': total_cnt,
            'total_reduced_kg': total_reduced_kg,
            'total_recycled_water': total_recycled_water
        }

    @api.model
    def get_dashboard_data(self, water_date_filter='yearly', water_scope_filter='all', water_start_date=False, water_end_date=False):
        from dateutil.relativedelta import relativedelta
        from datetime import datetime
        # Use context_today for timezone-aware calculations
        today = fields.Date.context_today(self)
        company = self.env.company
        
        # --- COMMON FILTER LOGIC ---
        start_date = False
        end_date = today
        
        if water_date_filter == 'today':
            start_date = today
        elif water_date_filter == 'monthly':
            start_date = today.replace(day=1)
        elif water_date_filter == 'quarterly':
            start_month = 3 * ((today.month - 1) // 3) + 1
            start_date = today.replace(month=start_month, day=1)
        elif water_date_filter == 'yearly':
            start_date = today.replace(month=1, day=1)
        elif water_date_filter == 'range':
            if water_start_date:
                start_date = fields.Date.from_string(water_start_date)
            if water_end_date:
                end_date = fields.Date.from_string(water_end_date)
        else:
            # Fallback to yearly if no specific filter
            start_date = today.replace(month=1, day=1)

        def get_scoped_activities(calc_ids, factor_type):
            domain = [('calculation_id', 'in', calc_ids), ('factor_id.type', '=', factor_type)]
            
            if not water_scope_filter or water_scope_filter == 'all':
                return self.env['carbon.activity'].search(domain)
            
            # Handle multiple selections (passed as a list or comma-separated string)
            scope_filters = []
            if isinstance(water_scope_filter, list):
                scope_filters = water_scope_filter
            elif isinstance(water_scope_filter, str):
                scope_filters = water_scope_filter.split(',')

            scope_ids = []
            include_no_scope = False
            for f in scope_filters:
                if f == 'all':
                    return self.env['carbon.activity'].search(domain)
                if f == 'no_scope':
                    include_no_scope = True
                else:
                    try:
                        scope_ids.append(int(f))
                    except (ValueError, TypeError):
                        pass
            
            if scope_ids and include_no_scope:
                domain.append('|')
                domain.append(('scope_id', 'in', scope_ids))
                domain.append(('scope_id', '=', False))
            elif scope_ids:
                domain.append(('scope_id', 'in', scope_ids))
            elif include_no_scope:
                domain.append(('scope_id', '=', False))
            else:
                # If everything is deselected, return nothing as per user request
                # (or maybe return all? The user said 'when no scope is selected all should be deselected')
                # I'll return empty recordset
                return self.env['carbon.activity'].browse()

            return self.env['carbon.activity'].search(domain)

        # Filter calculations in the current period - ONLY 'done' records
        calcs = self.env['carbon.calc'].search([
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ])
        calc_ids = calcs.ids
        
        # --- CAP VS USAGE CALCULATION (CARBON) ---
        cap_amount = company.carbon_cap or 0.0
        used_amount = 0.0
        
        air_activities = get_scoped_activities(calc_ids, 'air')
        for activity in air_activities:
            unit_name = activity.uom_name.name or ""
            if 'kg' in unit_name.lower():
                used_amount += (activity.emission_total / 1000.0)
        
        cap_data = {
            'cap': cap_amount,
            'used': round(used_amount, 3),
            'duration': water_date_filter,
            'unit': 't CO2e'
        }

        # 1. Overall Gas Emissions (Type = air) - Grouped by Gas
        gas_labels = []
        gas_values = []
        if air_activities:
            gas_groups = self.env['carbon.activity'].read_group(
                domain=[('id', 'in', air_activities.ids)],
                fields=['gas_id', 'emission_total:sum'],
                groupby=['gas_id']
            )
            for g in gas_groups:
                gas_name = g['gas_id'][1] if g['gas_id'] else 'Unknown Gas'
                gas_labels.append(gas_name)
                gas_values.append(g['emission_total'])

        # 2. Sound Analysis (Type = sound)
        start_date_4m_sound = (today.replace(day=1) - relativedelta(months=3))
        sound_calcs = self.env['carbon.calc'].search([
            ('state', '=', 'done'),
            ('date', '>=', start_date_4m_sound),
            ('date', '<=', today)
        ])
        sound_activities = get_scoped_activities(sound_calcs.ids, 'sound')
        
        sound_groups = []
        if sound_activities:
            sound_groups = self.env['carbon.activity'].read_group(
                domain=[('id', 'in', sound_activities.ids)],
                fields=['date', 'emission_total:sum'],
                groupby=['date:month']
            )
        
        sound_labels_map = {}
        curr_m_s = start_date_4m_sound
        for _ in range(4):
            m_str = curr_m_s.strftime('%B %Y')
            sound_labels_map[m_str] = 0.0
            curr_m_s += relativedelta(months=1)
            
        for s in sound_groups:
            m_key = s['date:month']
            if m_key in sound_labels_map:
                sound_labels_map[m_key] += s['emission_total']

        sound_labels = list(sound_labels_map.keys())
        sound_values = list(sound_labels_map.values())

        # 3. Water Pollution Chart (Type = water) - Trend
        start_date_3m_water = (today.replace(day=1) - relativedelta(months=2))
        water_pollution_calcs = self.env['carbon.calc'].search([
            ('state', '=', 'done'),
            ('date', '>=', start_date_3m_water),
            ('date', '<=', today)
        ])
        water_activities_trend = get_scoped_activities(water_pollution_calcs.ids, 'water')
        
        water_groups = []
        if water_activities_trend:
            water_groups = self.env['carbon.activity'].read_group(
                domain=[('id', 'in', water_activities_trend.ids)],
                fields=['date', 'emission_total:sum'],
                groupby=['date:month']
            )

        water_labels_map = {}
        curr_m_w = start_date_3m_water
        for _ in range(3):
            m_str = curr_m_w.strftime('%B %Y')
            water_labels_map[m_str] = 0.0
            curr_m_w += relativedelta(months=1)
            
        for w in water_groups:
            m_key = w['date:month']
            if m_key in water_labels_map:
                water_labels_map[m_key] += w['emission_total']
        
        water_labels = list(water_labels_map.keys())
        water_values = list(water_labels_map.values())

        # 4. Initiatives (Green, Water, Sound)
        green_stats = self._get_initiative_stats('cyllo_green_metrics.project_green_initiatives', start_date, end_date, water_scope_filter)
        water_stats = self._get_initiative_stats('cyllo_green_metrics.project_water_initiatives', start_date, end_date, water_scope_filter)
        sound_stats = self._get_initiative_stats('cyllo_green_metrics.project_sound_initiatives', start_date, end_date, water_scope_filter)

        total_reduced_kg = green_stats['total_reduced_kg'] + water_stats['total_reduced_kg'] + sound_stats['total_reduced_kg']
        
        original_used = float(used_amount)
        green_t = round(float(total_reduced_kg) / 1000.0, 3)
        cap_val = float(cap_amount)

        # Available Credit = Allocated Cap - Used Amount + Reduced Emissions + Transfer Credits
        total_transfer_credits = self.env['account.move']._get_available_credits()
        credit = cap_val - original_used + green_t + total_transfer_credits
        cap_data['available_credit'] = round(credit, 3)

        # Visibility logic for available credit
        show_credit = (cap_val > 0) and (credit > 0.0001)
        if abs(cap_val - original_used) < 0.0001 and abs(green_t) < 0.0001:
            show_credit = False
            
        cap_data['show_available_credit'] = show_credit
        cap_data['used'] = round(original_used, 3)

        # --- WATER CAP VS USAGE CALCULATION WITH FILTERS ---
        water_unit = company.water_unit or 'L'
        water_cap_amount = company.water_cap or 0.0
        
        # Fetch all scopes for the filter dropdown
        scopes = self.env['carbon.scope'].search_read([], ['id', 'name'])
        
        water_activities = get_scoped_activities(calc_ids, 'water')
        water_used_amount = 0.0
        
        for activity in water_activities:
            act_unit = activity.uom_name.name or ""
            qty = activity.quantity
            if act_unit.lower() == 'l':
                qty_in_l = qty
            elif act_unit.lower() in ('kl', 'tonnes'):
                qty_in_l = qty * 1000.0
            else:
                qty_in_l = qty

            if water_unit == 'L':
                water_used_amount += qty_in_l
            elif water_unit in ('KL', 'tonnes'):
                water_used_amount += (qty_in_l / 1000.0)

        recycled_kl = water_stats['total_recycled_water']
        if water_unit == 'L':
            recycled_water = recycled_kl * 1000.0
        else:
            recycled_water = recycled_kl
            
        water_credit = water_cap_amount - water_used_amount + recycled_water
        show_water_credit = (water_cap_amount > 0) and (water_credit > 0.0001)
        if abs(water_cap_amount - water_used_amount) < 0.0001 and abs(recycled_water) < 0.0001:
            show_water_credit = False

        water_cap_data = {
            'cap': float(water_cap_amount),
            'used': round(float(water_used_amount), 3),
            'duration': water_date_filter,
            'unit': water_unit,
            'available_credit': round(float(water_credit), 3),
            'show_available_credit': show_water_credit
        }

        return {
            'cap_data': cap_data,
            'water_cap_data': water_cap_data,
            'projects': green_stats,
            'water_projects': water_stats,
            'sound_projects': sound_stats,
            'scopes': scopes,
            'gas': {
                'labels': gas_labels,
                'values': gas_values
            },
            'sound': {
                'labels': sound_labels,
                'values': sound_values
            },
            'water': {
                'labels': water_labels,
                'values': water_values
            },
            'transfer_credits': self.env['account.move']._get_available_credits(),
        }


