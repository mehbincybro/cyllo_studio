
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
from odoo import models, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _show_in_cart(self):
        """
        Overrides the standard logic to hide the trial discount product
        from the website cart display.
        """
        # Get the standard result (which already hides delivery lines)
        res = super()._show_in_cart()

        # Get the trial product reference
        trial_product = self.env.ref('cyllo_website_sale.product_trial_discount', raise_if_not_found=False)

        # If this line is the trial discount, force it to hide (return False)
        if trial_product and self.product_id == trial_product:
            return False

        return res