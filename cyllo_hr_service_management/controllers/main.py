# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class HrServicePortal(CustomerPortal):
    """ Class to define the 'hr.service' portal view """
    def _prepare_home_portal_values(self, counters):
        """ Function to get the count of total number of tickets """
        vals = super()._prepare_home_portal_values(counters)
        if 'service_count' in counters:
            vals['service_count'] = request.env['hr.service'].sudo().search_count(
                [('employee_id', '=', request.env.user.employee_ids.id)])
        return vals
