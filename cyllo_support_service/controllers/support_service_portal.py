# -*- coding: utf-8 -*-
import base64

from odoo import Command, http
from odoo.exceptions import AccessError, MissingError
from werkzeug.exceptions import NotFound
from odoo.http import request
from odoo.addons.payment.controllers import portal
from werkzeug.utils import secure_filename


class SupportServicePortalTicket(portal.PaymentPortal):
    """ Class to define all the details needed for the portal view """

    @http.route(['/support_service_ticket'], type='http', auth="user", website=True)
    def get_my_support_service_tickets(self):
        """This route is called whenever the user clicks on the
        'Support Service Ticket' menu on the website.
        :return: HTTP response containing the 'my_support_service_ticket' template
        with relevant data for the user's support service ticket.
        """
        serviceticket = request.env['support.service.ticket'].sudo()
        partner_id = request.env.user.partner_id.id
        values = {'support_service_tickets': serviceticket.search([('customer_id', '=', partner_id)]),
                  'support_service_ticket_count': serviceticket.search_count([('customer_id', '=', partner_id)]),
                  'draft_support_service_tickets': serviceticket.search(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref('cyllo_support_service.support_service_stage_new').id)]),
                  'draft_support_service_ticket_count': serviceticket.search_count(
                      [('customer_id', '=', partner_id), ('stage_id', '=', request.env.ref(
                           'cyllo_support_service.support_service_stage_new').id)]),
                  'in_progress_support_service_tickets': serviceticket.search(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref(
                           'cyllo_support_service.support_service_stage_in_progress').id)]),
                  'in_progress_support_service_ticket_count': serviceticket.search_count(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref(
                           'cyllo_support_service.support_service_stage_in_progress').id)]),
                  'on_hold_support_service_tickets': serviceticket.search(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref('cyllo_support_service.support_service_stage_on_hold').id)]),
                  'on_hold_support_service_ticket_count': serviceticket.search_count(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref('cyllo_support_service.support_service_stage_on_hold').id)]),
                  'solved_support_service_tickets': serviceticket.search(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref('cyllo_support_service.support_service_stage_solved').id)]),
                  'solved_support_service_ticket_count': serviceticket.search_count(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref('cyllo_support_service.support_service_stage_solved').id)]),
                  'closed_support_service_tickets': serviceticket.search(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=',request.env.ref('cyllo_support_service.support_service_stage_closed').id)]),
                  'closed_support_service_ticket_count': serviceticket.search_count(
                      [('customer_id', '=', partner_id),
                       ('stage_id', '=', request.env.ref('cyllo_support_service.support_service_stage_closed').id)]),
                  'page_name': 'support_service_tickets'
                  }
        return request.render("cyllo_support_service.support_service_ticket_template", values)

    @http.route(['/support_service_ticket/details/ticket/<int:ticket_id>'], type='http', auth="user", website=True)
    def get_support_service_ticket_details(self, ticket_id, report_type=None, access_token=None, download=True):
        """ This route is called whenever the user clicks on 'Support Service Ticket'
        menu in website"""
        try:
            current_record = self._document_check_access(
                'support.service.ticket', ticket_id,
                access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        total_record = request.env['support.service.ticket'].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id)]).ids
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=current_record,
                report_type=report_type,
                report_ref='cyllo_support_service.support_service_report_document',
                download=download,
            )
        if ticket_id in total_record:
            index = total_record.index(ticket_id)
            return request.render("cyllo_support_service.support_service_ticket_details", {
                    'object': current_record,
                    'support_service_ticket': request.env['support.service.ticket'].sudo().browse(ticket_id),
                    'page_name': 'support_service_ticket_details',
                    'prev_record': total_record[index - 1] if index > 0 else False,
                    'next_record': total_record[index + 1] if index < len(total_record) - 1 else False
                })
        else:
            return request.redirect('/support_service_ticket/create')

    @http.route(['/support_service_ticket/create'], type='http', auth="user", website=True)
    def support_service_ticket_form(self):
        """ This route is called whenever the user clicks on 'Create Ticket'
        button in website"""
        priority_field_info = request.env['support.service.ticket'].sudo().fields_get(['priority'])
        priority_values = priority_field_info['priority']['selection']
        return request.render("cyllo_support_service.support_service_ticket_form", {
            'customers': request.env['res.partner'].sudo().search([]),
            'categories': request.env['support.service.category'].sudo().search([]),
            'sale_order_items': request.env['sale.order'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id)]),
            'priority_values': priority_values,
            'page_name': 'create_ticket'
        })

    @http.route(['/support_service_ticket/close/<int:req_id>'], type='http', auth="user", website=True)
    def support_service_ticket_close(self, req_id):
        """ This route is called whenever the user hits the 'Close' button """
        support_service_ticket = request.env[
            'support.service.ticket'].sudo().browse(req_id)
        support_service_ticket.stage_id = request.env.ref(
            'cyllo_support_service.support_service_stage_closed').id
        return request.render(
            'cyllo_support_service.support_service_ticket_closing_template')

    @http.route(['/ticket/submit'], type='http', auth="user", website=True)
    def submit_appointment(self, **kwargs):
        """ This route is called whenever the user hits the 'Submit' button """
        ticket = request.env['support.service.ticket'].sudo().create({
            'customer_id': request.env.user.partner_id.id,
            'name': kwargs.get('ticket_name'),
            'phone': kwargs.get('phone'),
            'email': kwargs.get('email'),
            'category_id': kwargs.get('category_name'),
            'sale_order_item_id': kwargs.get('sale_order'),
            'description': kwargs.get('description'),
            'priority': kwargs.get('priority'),
            'ticket_type': kwargs.get('ticket_type')
        })
        if 'attachments' in request.httprequest.files:
            attached_files = request.httprequest.files.getlist('attachments')
            attachments = []
            for attachment in attached_files:
                filename = secure_filename(attachment.filename)
                file_data = attachment.read()
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'res_model': 'support.service.ticket',
                    'res_id': ticket.id,
                    'type': 'binary',
                    'public': True,
                    'datas': base64.b64encode(file_data),
                })
                attachments.append(Command.link(attachment.id))
            ticket = ticket.sudo()
            partner_id = request.env.user.partner_id if request.env.user.partner_id else False
            if not partner_id:
                raise NotFound()
            post_values = dict(body="Submitted records", message_type="comment", subtype_xmlid="mail.mt_comment",
                               author_id=partner_id.id)
            if partner_id.email:
                post_values['email_from'] = partner_id.email_formatted
            message = ticket.with_context(mail_create_nosubscribe=True).message_post(**post_values)
            message.sudo().write({'attachment_ids': attachments})
        return request.render("cyllo_portal.request_submit_template", {'url': '/support_service_ticket'})
