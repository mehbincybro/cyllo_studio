# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.payment.controllers import portal


class ServiceManagement(portal.PaymentPortal):
    """ Class to define all the details needed for service management the portal view"""

    @http.route(['/service_management'], type='http', auth="user", website=True)
    def get_user_service_requests(self):
        """This route is called whenever the user clicks on the
        'Service Management' menu on the website.
        :return: HTTP response containing the 'user service requests' template
        with relevant data for the user's service requests."""
        employee_id = request.env.user.employee_ids.id
        user_services = request.env['hr.service'].sudo().search([('employee_id', '=', employee_id)])
        values = {'support_service_tickets': user_services,
                  'service_count': user_services.search_count([('employee_id', '=', employee_id)]),
                  'draft_services': user_services.filtered(lambda service: service.state == 'draft'),
                  'submitted_services': user_services.filtered(lambda service: service.state == 'submit'),
                  'approved_services': user_services.filtered(lambda service: service.state == 'approved'),
                  'returned_services': user_services.filtered(lambda service: service.state == 'returned'),
                  'ongoing_services': user_services.filtered(lambda service: service.state == 'ongoing'),
                  'done_services': user_services.filtered(lambda service: service.state == 'done'),
                  'cancel_services': user_services.filtered(lambda service: service.state == 'cancel'),
                  'page_name': 'services_page'
                  }
        return request.render("cyllo_hr_service_management.service_request_template", values)

    @http.route(['/service_management/details/request/<int:service_id>'], type='http', auth="user", website=True)
    def get_service_request_details(self, service_id, report_type=None, access_token=None, download=True):
        """ This route is called whenever the user clicks on a 'Service
        request' in website"""
        try:
            current_record = self._document_check_access('hr.service', service_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        total_record = request.env['hr.service'].sudo().search(
            [('employee_id', '=', request.env.user.employee_ids.id)]).ids
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=current_record, report_type=report_type, download=download,
                                     report_ref='cyllo_hr_service_management.report_hr_service_request_form')
        if service_id in total_record:
            index = total_record.index(service_id)
            return request.render("cyllo_hr_service_management.service_requests_details", {
                'object': current_record,
                'service_req': request.env['hr.service'].sudo().browse(service_id),
                'page_name': 'service_details',
                'prev_record': total_record[index - 1] if index > 0 else False,
                'next_record': total_record[index + 1] if index < len(total_record) - 1 else False
             })
        else:
            return request.redirect('/service_management/create')

    @http.route(['/service_management/create'], type='http', auth="user", website=True)
    def service_request_form(self):
        """ This route is called whenever the user clicks on 'Create Ticket'
        button in website
        Returns:Template and Values to it."""
        employee_ids = request.env.user.employee_ids
        service_handlers = request.env['hr.employee'].sudo().search([])
        if len(employee_ids) == 1:
            if employee_ids.parent_id:
                service_handlers = employee_ids.parent_id
            elif employee_ids.department_id.manager_id:
                service_handlers = employee_ids.department_id.manager_id
            else:
                service_handlers = service_handlers
        values = {
            'categories': request.env['hr.service.category'].sudo().search([]),
            'equipment': request.env['maintenance.equipment'].sudo().search([('employee_id', '=', False)]),
            'service_equipment': request.env['maintenance.equipment'].sudo().search([
                ('employee_id', '=', employee_ids.id)]),
            'service_handlers': service_handlers,
            'page_name': 'create_service'
        }
        return request.render("cyllo_hr_service_management.service_request_form", values)

    @http.route(['/service_request/submit/<int:req_id>'], type='http', auth="user", website=True)
    def hr_incident_submit(self, req_id):
        """ This route is called whenever the user hits the 'Submit'
        button """
        request.env['hr.service'].sudo().browse(req_id).action_submit()
        return request.render('cyllo_hr_service_management.service_request_submitting_template')

    @http.route(['/request/submit'], type='http', auth="user", website=True)
    def submit_request(self, **kwargs):
        """ This route is called whenever the user hits the 'Submit' button
        in request form"""
        equipment = False
        if kwargs.get('request_type') == 'custody':
            equipment = kwargs.get('equipment')
        if kwargs.get('request_type') == 'service' and kwargs.get(
                'service_equipment') != '':
            equipment = kwargs.get('service_equipment')
        service = request.env['hr.service'].sudo().create({
            'state': 'submit',
            'service_request_type': kwargs.get('request_type'),
            'employee_id': request.env.user.employee_ids.id,
            'employee_department_id': kwargs.get('requester_dept'),
            'service_category_id': kwargs.get('category') if kwargs.get('category') != '' else False,
            'equipment_id': equipment,
            'maintenance_type': kwargs.get('maintenance_type') if kwargs.get(
                'request_type') == 'service' and kwargs.get(
                'service_equipment') != '' else False,
            'expected_return_date': kwargs.get('expected_return_date') if
            kwargs.get('expected_return_date') != '' else False,
            'service_handler_id': int(kwargs.get('handler')),
            'service_handler_department_id': kwargs.get('handlers_dept'),
        })
        service.action_submit()
        return request.render("cyllo_portal.request_submit_template", {'url': '/service_management'})
