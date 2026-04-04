# -*- coding: utf-8 -*-
#############################################################################
#
#   Cyllo Pvt. Ltd.
#
#   Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#   Author: Cyllo(<https://www.cyllo.com>)
#
#   You can modify it under the terms of the GNU LESSER
#   GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#   You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#   (LGPL v3) along with this program.
#   If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models, fields, api


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    shopfloor_blocking_wo_id = fields.Many2one(
        'mrp.workorder',
        string="Currently Blocked By",
        compute='_compute_shopfloor_blocking_wo_id'
    )

    @api.depends('state', 'blocked_by_workorder_ids.state')
    def _compute_shopfloor_blocking_wo_id(self):
        for wo in self:
            if wo.state == 'pending' and wo.blocked_by_workorder_ids:
                blocking_wos = wo.blocked_by_workorder_ids.filtered(
                    lambda w: w.state not in ('done', 'cancel')
                )
                wo.shopfloor_blocking_wo_id = blocking_wos[0].id if blocking_wos else False
            else:
                wo.shopfloor_blocking_wo_id = False

    def _notify_shopfloor_view(self):
        for record in self:
            is_from_shopfloor = self.env.context.get('from_shopfloor', False)
            self.env['bus.bus']._sendone(
                'shopfloor_channel',
                'workorder_updated',
                {
                    'workcenter_id': record.workcenter_id.id,
                    'source': 'shopfloor' if is_from_shopfloor else 'backend'
                }
            )

    def button_start(self):
        res = super().button_start()

        employee_id = self.env.context.get('employee_id')
        if employee_id:
            for wo in self:
                if wo.production_id:
                    wo.production_id.write({'employee_ids': [(4, employee_id)]})

        self._notify_shopfloor_view()
        return res

    def button_pending(self):
        res = super().button_pending()
        self._notify_shopfloor_view()
        return res

    def button_finish(self):
        res = super().button_finish()

        for workorder in self:
            production = workorder.production_id
            if production and production.state not in ('done', 'cancel'):
                incomplete_workorders = production.workorder_ids.filtered(
                    lambda w: w.state not in ('done', 'cancel')
                )
                if not incomplete_workorders:
                    self._notify_shopfloor_view()
                    if self.env.context.get('from_shopfloor'):
                        return {
                            'type': 'trigger_close_production',
                            'mo_id': production.id
                        }

        self._notify_shopfloor_view()
        if self.env.context.get('from_shopfloor') and isinstance(res, dict) and res.get(
                'type') == 'ir.actions.act_window_close':
            return False

        return res

    def button_block(self):
        res = super().button_pending()
        self._notify_shopfloor_view()
        return res

    def button_unblock(self):
        res = super().button_unblock()
        self._notify_shopfloor_view()
        return res

    def action_show_shopfloor_worksheet(self):
        self.ensure_one()
        worksheet_view_id = self.env.ref('cyllo_shopfloor.view_shopfloor_worksheet_popup').id
        return {
            'name': f'Worksheet: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(worksheet_view_id, 'form')],
            'target': 'new',
        }
    @api.model
    def _cron_finish_automated_workorders(self):
        """
        Evaluates running work orders. If an order belongs to an automated MO
        and has exceeded its expected duration, it is marked as finished.
        It then automatically starts the next available work order if one exists.
        """
        running_wos = self.search([
            ('state', 'in', ['progress','ready']),
            ('production_id.is_automated', '=', True),
            ('duration_expected', '>', 0)
        ])

        print(running_wos)

        now = fields.Datetime.now()

        for wo in running_wos:
            print(wo.name)
            if wo.state == 'ready':
                wo.button_start()
            else:
                print(wo.name)
                # 1. Manually calculate the exact elapsed time in minutes
                current_duration = 0.0
                for time_line in wo.time_ids:
                    if time_line.date_end:
                        # Add fully completed time blocks (e.g., if it was paused previously)
                        current_duration += time_line.duration
                    elif time_line.date_start:
                        # Calculate active running time: Now - Start Time
                        elapsed = now - time_line.date_start
                        current_duration += elapsed.total_seconds() / 60.0
                    print(current_duration)

                # 2. Compare the real-time duration against the expected duration
                if current_duration >= wo.duration_expected:
                    wo.button_finish()

                    mo = wo.production_id
                    if mo.state not in ('done', 'cancel'):
                        incomplete_wos = mo.workorder_ids.filtered(
                            lambda w: w.state not in ('done', 'cancel')
                        )

                        if not incomplete_wos:
                            mo.action_shopfloor_close_mo()
                        else:
                            next_wo = incomplete_wos.filtered(lambda w: w.state == 'ready')
                            if next_wo:
                                next_wo[0].button_start()
