# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.payment.controllers import portal


class IncidentManagement(portal.PaymentPortal):
    """ Class to define all the details needed for incident management the 
    portal view """

    @http.route(['/incident_management'], type='http', auth="user", website=True)
    def get_user_incident_requests(self):
        """This route is called whenever the user clicks on the
        'Incident Management' menu on the website.
        :return: HTTP response containing the 'user incident requests' template
        with relevant data for the user's incident requests."""
        if request.env.user.has_group('base.group_user'):
            incident = request.env['hr.incident'].sudo()
            employee_id = request.env.user.employee_ids.id
            values = {
                'user_incidents': incident.search([('incident_initiator_id', '=', employee_id)]),
                'incident_count': incident.search_count([('incident_initiator_id', '=', employee_id)]),
                'new_incidents': incident.search([('incident_initiator_id', '=', employee_id),
                                                  ('incident_stage', '=', 'new')]),
                'new_incidents_count': incident.search_count([('incident_initiator_id', '=', employee_id),
                                                              ('incident_stage', '=', 'new')]),
                'submitted_incidents': incident.search([('incident_initiator_id', '=', employee_id),
                                                        ('incident_stage', '=', 'submitted')]),
                'submitted_incidents_count': incident.search_count([('incident_initiator_id', '=', employee_id),
                                                                    ('incident_stage', '=', 'submitted')]),
                'ongoing_incidents': incident.search([('incident_initiator_id', '=', employee_id),
                                                      ('incident_stage', '=', 'ongoing')]),
                'ongoing_incidents_count': incident.search_count([('incident_initiator_id', '=', employee_id),
                                                                  ('incident_stage', '=', 'ongoing')]),
                'completed_incidents': incident.search([('incident_initiator_id', '=', employee_id),
                                                        ('incident_stage', '=', 'completed')]),
                'completed_incidents_count': incident.search_count([('incident_initiator_id', '=', employee_id),
                                                                    ('incident_stage', '=', 'completed')]),
                'page_name': 'incident_page'
            }
            return request.render("cyllo_hr_incident_management.incident_request_template", values)
        else:
            return request.render("portal.portal_my_home")

    @http.route(['/incident_management/details/request/<int:incident_id>'], type='http', auth="user", website=True)
    def get_incident_request_details(self, incident_id, report_type=None, access_token=None, download=True):
        """ This route is called whenever the user clicks on a 'Incident
        request' in website"""
        try:
            current_record = self._document_check_access('hr.incident', incident_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        total_record = (request.env['hr.incident'].sudo().search(
            [('incident_initiator_id', '=', request.env.user.employee_ids.id)]).ids)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=current_record, report_type=report_type, download=download,
                                     report_ref='cyllo_hr_incident_management.report_hr_incident_pdf')
        if incident_id in total_record:
            index = total_record.index(incident_id)
            return request.render("cyllo_hr_incident_management.incident_requests_details", {
                'object': current_record,
                'incident_req': request.env['hr.incident'].sudo().browse(incident_id),
                'page_name': 'incident_details',
                'prev_record': total_record[index - 1] if index > 0 else False,
                'next_record': total_record[index + 1] if index < len(total_record) - 1 else False
            })
        else:
            return request.redirect('/incident_management/create')

    @http.route(['/incident_management/create'], type='http', auth="user", website=True)
    def incident_request_form(self):
        """ This route is called whenever the user clicks on 'Create Request'
        button in website"""
        if request.env.user.has_group('base.group_user'):
            return request.render("cyllo_hr_incident_management.incident_request_form", {
                'categories': request.env['hr.incident.category'].sudo().search([]),
                'employee_ids': request.env['hr.employee'].sudo().search([]),
                'page_name': 'create_incident',
                'is_manager': request.env.user.has_group('hr.group_hr_manager')
            })
        else:
            return request.render("portal.portal_my_home")

    @http.route(['/incident_request/submit/<int:req_id>'], type='http', auth="user", website=True)
    def hr_incident_submit(self, req_id):
        """ This route is called whenever the user hits the 'Submit request'
        button from each record's detailed view"""
        incident_request = request.env['hr.incident'].sudo().browse(req_id)
        incident_request.action_submit_incident_request()
        return request.render('cyllo_hr_incident_management.incident_request_submitting_template')

    @http.route(['/request/submit'], type='http', auth="user", website=True)
    def submit_request(self, **kwargs):
        """ This route is called whenever the user hits the 'Submit' button
        in request form"""
        if kwargs.get('initiator'):
            incident_req = request.env['hr.incident'].sudo().create({
                'incident_initiator_id': kwargs.get('initiator'),
                'incident_category_id': kwargs.get('category_name'),
                'incident_receptor_phone': kwargs.get('phone'),
                'incident_receptor_email': kwargs.get('email'),
                'incident_receptor_id': kwargs.get('receptor'),
                'incident_description': kwargs.get('incident_desc')})
        else:
            incident_req = request.env['hr.incident'].sudo().create({
                'incident_initiator_id': request.env.user.employee_ids.id,
                'incident_category_id': kwargs.get('category_name'),
                'incident_receptor_phone': kwargs.get('phone'),
                'incident_receptor_email': kwargs.get('email'),
                'incident_receptor_id': kwargs.get('receptor'),
                'incident_description': kwargs.get('incident_desc')})
        incident_req.action_submit_incident_request()
        return request.render("cyllo_portal.request_submit_template", {'url': '/incident_management'})

    @http.route(['/employee/parent'], type='json', auth="user", website=True)
    def employee_handler(self, **kwargs):
        """
        To retrieve the parent or department manager of an employee.
        :param: Contains the 'employee_id' key with the ID of the employee.
        :return: JSON response with the name of the employee's parent or
        department manager.
        """
        employee_id = request.env['hr.employee'].sudo().browse(kwargs.get('employee_id'))
        receptor_id = employee_id.parent_id if employee_id.parent_id else employee_id.department_id.manager_id
        return {'receptor_id': receptor_id.name}
