# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class HrIncidentPortal(CustomerPortal):
    """ Class to define the 'hr.incident' portal view """
    def _prepare_home_portal_values(self, counters):
        """ Function to get the count of total number of tickets """
        vals = super()._prepare_home_portal_values(counters)
        if 'incident_count' in counters:
            vals['incident_count'] = request.env['hr.incident'].sudo().search_count(
                [('incident_receptor_id', '=', request.env.user.employee_ids.id)])
        return vals
