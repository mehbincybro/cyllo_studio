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


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_shopfloor_close_mo(self):
        """Auto-consumes expected quantities for untracked components and closes the MO."""
        self.ensure_one()

        if self.product_id.tracking in ['lot', 'serial'] and not self.lot_producing_id:
            self.action_generate_serial()

        if self.qty_producing == 0:
            self.qty_producing = self.product_qty

        pending_moves = self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))

        for raw_move in pending_moves:
            if raw_move.product_id.tracking == 'none':
                quantity_field = 'quantity' if hasattr(raw_move, 'quantity') else 'quantity_done'
                consumed_qty = getattr(raw_move, quantity_field)

                if consumed_qty < raw_move.product_uom_qty:
                    setattr(raw_move, quantity_field, raw_move.product_uom_qty)

        return self.button_mark_done()
    