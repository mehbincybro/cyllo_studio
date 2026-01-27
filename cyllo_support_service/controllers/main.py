# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class SupportServicePortal(CustomerPortal):
    """ Class to define the portal views """

    def _prepare_home_portal_values(self, counters):
        """ Function to get the count of total number of tickets """
        vals = super()._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            vals['ticket_count'] = request.env['support.service.ticket'].sudo().search_count(
                [('customer_id', '=', request.env.user.partner_id.id)])
        return vals
