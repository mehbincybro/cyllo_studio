# -*- coding: utf-8 -*-
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class WebsiteCustomerPortal(CustomerPortal):
    """ functon : Prepare portal values, datas are searched from document.file
        :return document count, request count"""

    def _prepare_home_portal_values(self, counters):
        """Prepare the values for the home portal page.
        :param counters(dict): A dictionary containing various counters for different features on the portal.
        :return: A dictionary containing the prepared values for the home portal page."""
        values = (super(WebsiteCustomerPortal, self)._prepare_home_portal_values(counters))
        if 'document_count' in counters:
            values['document_count'] = request.env['document.file'].sudo().search_count(
                [('user_id.id', '=', request.uid)])
            values['request_count'] = request.env['request.document'].sudo().search_count([
                ('user_id.id', '=', request.uid), ('state', '=', 'requested')])
        return values
