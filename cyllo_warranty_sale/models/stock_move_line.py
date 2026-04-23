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


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    warranty_expiration_date = fields.Date(
        string="Warranty Expiration Date",
        compute='_compute_warranty_expiration_date',
        store=True,
    )

    @api.depends('move_id.sale_line_id.warranty_expiration_date')
    def _compute_warranty_expiration_date(self):
        for line in self:
            # We only handle sale_line_id here. 
            # purchase_line_id will be handled in cyllo_warranty_purchase.
            line.warranty_expiration_date = line.move_id.sale_line_id.warranty_expiration_date
