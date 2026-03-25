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
import json
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class MrpScheduleMps(models.Model):
    _name = 'mrp.mps.schedule'
    _description = 'Master Production Schedule'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    is_mps = fields.Boolean(string='Master Production Scheduler')

    mps_default_timerange = fields.Selection(
        [('Yearly', 'year'), ('Monthly', 'month'), ('weekly', 'week'), ('Daily', 'days')],
        string='Default Time Range'
    )

    product_id = fields.Many2one('product.product', string='Product')
    bom_id = fields.Many2one('mrp.bom', string='BOM', domain="[('product_id', '=', product_id)]")
    route_id = fields.Many2one('stock.route', string='Route', store=True)

    is_manufacture_route = fields.Boolean(compute='_compute_is_manufacture_route')
    available_route_ids = fields.Many2many('stock.route', compute='_compute_available_routes')
    available_bom_ids = fields.Many2many('mrp.bom', compute='_compute_available_boms')

    is_indirect = fields.Boolean(string='Indirect demand')

    forcast_target_quantity = fields.Float(string='Safety Target Quantity')
    min_to_replenish_qty = fields.Float(string='Minimum Replenish Quantity')

    replenishment_mode = fields.Selection([
        ('manual', 'Manual'),
        ('automated', 'Automated'),
        ('never', 'Never')
    ], default="manual")

    qty_available = fields.Float(related='product_id.qty_available')

    saved_demand = fields.Text(default="{}")
    saved_replenishment = fields.Text(default="{}")
    saved_manual_repl = fields.Text(default="{}")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('product_id')
    def _compute_available_routes(self):
        """Find available routes for product"""
        for schedule in self:
            schedule.available_route_ids = schedule.product_id.route_ids.filtered(
                lambda r: r.name in ('Buy', 'Manufacture')
            )
        self.get_mps_config()

    @api.depends('product_id')
    def _compute_available_boms(self):
        """Find available bom for product"""
        for schedule in self:
            schedule.available_bom_ids = schedule.product_id.bom_ids

    @api.depends('route_id')
    def _compute_is_manufacture_route(self):
        for schedule in self:
            schedule.is_manufacture_route = schedule.route_id.name == 'Manufacture' if schedule.route_id else False

    # -------------------------------------------------------------------------
    # CORE METHODS
    # -------------------------------------------------------------------------
    @api.model
    def get_product_data(self):
        """Fetch product data from backend for rendering MPS"""
        schedules = self.search([])
        schedule_map = {rec.product_id.id: rec.id for rec in schedules}

        result = []

        for schedule in schedules:
            product = schedule.product_id
            bom_components = self._get_bom_components(schedule, schedule_map)
            starting_stock = (product.qty_available or 0.0) + (product.incoming_qty or 0.0)

            result.append({
                "id": schedule.id,
                "name": product.display_name,
                "initialStock": starting_stock,
                "min_qty": schedule.min_to_replenish_qty,
                "target_qty": schedule.forcast_target_quantity,
                "replenishment_mode": schedule.replenishment_mode,
                "forecasted_qty": product.virtual_available or 0,
                "bom_components": bom_components,
                "saved_demand": self._safe_json_load(schedule.saved_demand),
                "saved_replenishment": self._safe_json_load(schedule.saved_replenishment),
                "saved_manual_repl": self._safe_json_load(schedule.saved_manual_repl),
            })

        return result

    def _get_bom_components(self, schedule, schedule_map):
        """Get bom component if the selected route is manufacture"""
        if schedule.route_id.name != 'Manufacture' or not schedule.bom_id:
            return []

        return [
            {
                "schedule_id": schedule_map.get(line.product_id.id),
                "qty": line.product_qty
            }
            for line in schedule.bom_id.bom_line_ids
            if schedule_map.get(line.product_id.id)
        ]

    def _safe_json_load(self, value):
        try:
            return json.loads(value or "{}")
        except Exception:
            return {}

    # -------------------------------------------------------------------------
    # UPDATE METHODS
    # -------------------------------------------------------------------------
    @api.model
    def update_period_data(self, record_id, demand, replenishment, manual_repl):
        """Save values from the frontend including user changed values to record using JSON"""
        schedule = self.browse(int(record_id))
        if schedule.exists():
            schedule.write({
                'saved_demand': json.dumps(demand),
                'saved_replenishment': json.dumps(replenishment),
                'saved_manual_repl': json.dumps(manual_repl),
            })
        return True

    # -------------------------------------------------------------------------
    # ORDER CREATION
    # -------------------------------------------------------------------------
    @api.model
    def create_purchase_manufacture_orders(self, quantities_by_schedule_id):
        """Create PO or MO based on product configuration in MPS"""

        valid_schedule_quantities = {
            int(schedule_id): quantity
            for schedule_id, quantity in quantities_by_schedule_id.items()
            if quantity > 0
        }

        if not valid_schedule_quantities:
            return False

        schedule_records = self.browse(valid_schedule_quantities.keys())

        purchase_orders_by_vendor = {}
        manufacturing_order_values = []

        for schedule_record in schedule_records:
            required_quantity = valid_schedule_quantities[schedule_record.id]
            product_record = schedule_record.product_id
            route_record = schedule_record.route_id

            if not product_record or not route_record:
                raise UserError(
                    f"Missing route/product for '{product_record.display_name}'."
                )

            if route_record.name == 'Manufacture':
                if not schedule_record.bom_id:
                    raise UserError(
                        f"Missing BOM for '{product_record.display_name}'."
                    )

                manufacturing_order_values.append(
                    self._prepare_mo_vals(
                        product_record,
                        required_quantity,
                        schedule_record.bom_id
                    )
                )

            elif route_record.name == 'Buy':
                vendor_record = self._get_vendor(product_record)
                purchase_orders_by_vendor.setdefault(vendor_record, []).append(
                    (product_record, required_quantity)
                )

            else:
                raise UserError(
                    f"Unsupported route '{route_record.name}'."
                )

        self._create_purchase_orders(purchase_orders_by_vendor)
        self.env['mrp.production'].create(manufacturing_order_values)

        return True

    def _prepare_mo_vals(self, product, qty, bom):
        return {
            'product_id': product.id,
            'product_qty': qty,
            'product_uom_id': product.uom_id.id,
            'bom_id': bom.id,
        }

    def _get_vendor(self, product):
        if not product.seller_ids:
            raise UserError(f"No vendor for '{product.display_name}'.")
        return product.seller_ids[0].partner_id

    def _create_purchase_orders(self, purchase_map):
        purchase_order = self.env['purchase.order']

        for vendor, lines in purchase_map.items():
            order_lines = [
                (0, 0, {
                    'product_id': p.id,
                    'product_qty': qty,
                    'product_uom': p.uom_po_id.id or p.uom_id.id,
                    'name': p.display_name,
                }) for p, qty in lines
            ]

            purchase_order.create({
                'partner_id': vendor.id,
                'order_line': order_lines,
            })

    # -------------------------------------------------------------------------
    # CONFIG & CRON
    # -------------------------------------------------------------------------
    @api.model
    def get_mps_config(self):
        period = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_manufacturing_mps.default_timerange', 'Month'
        )
        return {'period': period}

    @api.model
    def _cron_automate_mps_orders(self):
        period = self.get_mps_config()['period']
        today = date.today()

        label_map = {
            'Month': today.strftime('%b %Y'),
            'Week': f"W{today.isocalendar()[1]} {today.year}",
            'Day': f"{today.month}/{today.day}/{today.year}",
            'Year': str(today.year),
        }

        current_label = label_map.get(period, "")
        schedules = self.search([('replenishment_mode', '=', 'automated')])

        products_to_order = {
            str(rec.id): float(self._safe_json_load(rec.saved_replenishment).get(current_label, 0))
            for rec in schedules
            if float(self._safe_json_load(rec.saved_replenishment).get(current_label, 0)) > 0
        }

        if products_to_order:
            self.create_purchase_manufacture_orders(products_to_order)
