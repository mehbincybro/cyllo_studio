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
from odoo import models


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def _notify_shopfloor_view(self):
        """Broadcast a websocket message to the shopfloor channel."""
        for record in self:
            self.env['bus.bus']._sendone(
                'shopfloor_channel',
                'workorder_updated',
                {'workcenter_id': record.workcenter_id.id}
            )

    def button_start(self):
        res = super().button_start()
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