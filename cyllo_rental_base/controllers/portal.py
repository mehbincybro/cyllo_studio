# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustodyCustomerPortal(CustomerPortal):
    """Custom Customer Portal for managing custody records."""

    def _prepare_home_portal_values(self, counters):
        """ Function to get the count of rental records records by inheriting the
            function from which gets the count of "my account" datas
            args:
                counters : the count of records in my account
            return: Count of custody records  """
        values = super()._prepare_home_portal_values(counters)
        if 'rental_order_count' in counters:
            values['rental_order_count'] = request.env['rental.order'].sudo().search_count(
                [('partner_id', '=', request.env.user.partner_id.id)])
        return values
