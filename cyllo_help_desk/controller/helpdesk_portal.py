# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class HelpdeskPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(HelpdeskPortal, self)._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            ticket_count = request.env['helpdesk.ticket'].search_count([
                ('customer_id', '=', request.env.user.partner_id.id)
            ])
            values['ticket_count'] = ticket_count
        return values

    @http.route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_tickets(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        HelpdeskTicket = request.env['helpdesk.ticket']
        domain = [('customer_id', '=', request.env.user.partner_id.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        ticket_count = HelpdeskTicket.search_count(domain)
        pager = portal_pager(
            url="/my/tickets",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=ticket_count,
            page=page,
            step=self._items_per_page
        )
        tickets = HelpdeskTicket.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'tickets': tickets,
            'page_name': 'ticket',
            'pager': pager,
            'default_url': '/my/tickets',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("cyllo_help_desk.portal_my_tickets", values)

    @http.route(['/my/ticket/<int:ticket_id>'], type='http', auth="public", website=True)
    def portal_my_ticket_detail(self, ticket_id, access_token=None, **kw):
        try:
            ticket_sudo = self._document_check_access('helpdesk.ticket', ticket_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'ticket': ticket_sudo,
            'page_name': 'ticket',
        }
        return request.render("cyllo_help_desk.portal_ticket_page", values)

    @http.route(['/my/ticket/<int:ticket_id>/close'], type='http', auth="user", website=True)
    def portal_my_ticket_close(self, ticket_id, **kw):
        ticket = request.env['helpdesk.ticket'].browse(ticket_id)
        if ticket.customer_id == request.env.user.partner_id:
            solved_stage = request.env.ref('cyllo_help_desk.solved_ticket')
            ticket.stage_id = solved_stage.id
        return request.redirect('/my/ticket/%s' % ticket_id)
