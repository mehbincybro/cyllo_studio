# -*- coding: utf-8 -*-
import datetime
import json
import requests
from odoo.http import request
from odoo import fields, http


class CylloOffice365Authentication(http.Controller):
    """CylloOffice365Authentication class handles Office 365 authentication and webhooks for syncing data with Cyllo"""

    @http.route('/office/auth', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ Function to return the return url """
        state = json.loads(kw['state'])
        office_connector = request.env['cyllo.office.connector'].sudo().browse(state.get('office_connector_id'))
        office_connector.get_office_365_tokens(kw.get('code'))
        url_return = state.get('url_return')
        return request.redirect(url_return)

    @http.route('/office/contacts/create', type='http', auth='public', csrf=False)
    def office_contact_create(self, **kw):
        """Function to create a contact on office 365 contact creation"""
        validation_token = request.params.get('validationToken')
        if validation_token:
            return validation_token
        connector_id = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.contact_office_connector_id')
        connector = request.env['cyllo.office.connector'].sudo().browse(int(connector_id))
        if connector:
            if connector.onedrive_token_validity <= fields.Datetime.now():
                connector.action_refresh_office_365_tokens()
        request_body = json.loads(request.httprequest.data)
        resource_url = request_body['value'][0]['resource']
        api_url = f'https://graph.microsoft.com/v1.0/{resource_url}'
        access_token = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.contact_office_access_token')
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            contact = response.json()
            odoo_contact_name = request.env['cyllo.office.connector.line'].sudo().search([
                ('type', '=', 'partner')]).mapped('partner_id.name')
            country = False
            state = False
            if contact['displayName'] not in odoo_contact_name and contact['displayName']:
                if contact['homeAddress']:
                    country = request.env['res.country'].sudo().search(
                        [('name', '=', contact['homeAddress']['countryOrRegion'].capitalize())], limit=1)
                    state = request.env['res.country.state'].sudo().search(
                        [('name', '=', contact['homeAddress']['state'].capitalize()),
                         ('country_id', '=', country.id)], limit=1)
                created_contact = request.env['res.partner'].sudo().create({
                    'name': contact['displayName'],
                    'mobile': contact['mobilePhone'] if contact['mobilePhone'] else None,
                    'email': contact['emailAddresses'][0]['address'] if contact['emailAddresses'] else None,
                    'street': contact['homeAddress']['street'] if contact['homeAddress'] else None,
                    'city': contact['homeAddress']['city'] if contact['homeAddress'] else None,
                    'country_id': country.id if country else None,
                    'state_id': state.id if state else None,
                    'comment': contact['personalNotes'] if contact['personalNotes'] else None,
                    'zip': contact['homeAddress']['postalCode'] if contact['homeAddress'] else None,
                })
                created_contact.sudo().update({
                    'office_connectors_ids': [fields.Command.create({'office_365_identifier': contact['id'],
                                                                     'connector_id': connector_id,
                                                                     'type': 'partner',
                                                                     'partner_id': created_contact.id})]
                })

    @http.route('/office/contacts/updated', type='http', auth='public', csrf=False)
    def office_contact_update(self, **kw):
        """Function to update a contact on office 365 contact updation"""
        validation_token = request.params.get('validationToken')
        if validation_token:
            return validation_token
        connector_id = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.contact_office_connector_id')
        connector = request.env['cyllo.office.connector'].sudo().browse(int(connector_id))
        if connector:
            if connector.onedrive_token_validity <= fields.Datetime.now():
                connector.action_refresh_office_365_tokens()
        request_body = json.loads(request.httprequest.data)
        resource_url = request_body['value'][0]['resource']
        api_url = f'https://graph.microsoft.com/v1.0/{resource_url}'
        access_token = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.contact_office_access_token')
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            contact = response.json()
            odoo_contact_id = request.env[
                'cyllo.office.connector.line'].sudo().search([('type', '=', 'partner')]).mapped('office_365_identifier')
            country = False
            state = False
            if contact['id'] not in odoo_contact_id and contact['displayName']:
                if contact['homeAddress']:
                    country = request.env['res.country'].sudo().search(
                        [('name', '=', contact['homeAddress']['countryOrRegion'].capitalize())], limit=1)
                    state = request.env['res.country.state'].sudo().search(
                        [('name', '=', contact['homeAddress']['state'].capitalize()),
                         ('country_id', '=', country.id)], limit=1)
                created_contact = request.env['res.partner'].sudo().create({
                    'name': contact['displayName'],
                    'mobile': contact['mobilePhone'] if contact['mobilePhone'] else None,
                    'email': contact['emailAddresses'][0]['address'] if contact['emailAddresses'] else None,
                    'street': contact['homeAddress']['street'] if contact['homeAddress'] else None,
                    'city': contact['homeAddress']['city'] if contact['homeAddress'] else None,
                    'country_id': country.id if country else None,
                    'state_id': state.id if state else None,
                    'comment': contact['personalNotes'] if contact['personalNotes'] else None,
                    'zip': contact['homeAddress']['postalCode'] if contact['homeAddress'] else None,
                })
                created_contact.sudo().update({
                    'office_connectors_ids': [fields.Command.create({
                        'office_365_identifier': contact['id'],
                        'connector_id': connector_id,
                        'type': 'partner',
                        'partner_id': created_contact.id})]
                })
            else:
                contact_update = request.env['cyllo.office.connector.line'].sudo().search(
                    [('type', '=', 'partner'), ('office_365_identifier', '=', contact['id'])])
                if contact['homeAddress']:
                    country = request.env['res.country'].sudo().search(
                        [('name', '=', contact['homeAddress']['countryOrRegion'].capitalize())], limit=1)
                    state = request.env['res.country.state'].sudo().search(
                        [('name', '=', contact['homeAddress']['state'].capitalize()),
                         ('country_id', '=', country.id)], limit=1)
                contact_update.partner_id.sudo().write({
                    'name': contact['displayName'],
                    'mobile': contact['mobilePhone'] if contact['mobilePhone'] else None,
                    'email': contact['emailAddresses'][0]['address'] if contact['emailAddresses'] else None,
                    'street': contact['homeAddress']['street'] if contact['homeAddress'] else None,
                    'city': contact['homeAddress']['city'] if contact['homeAddress'] else None,
                    'country_id': country.id if country else None,
                    'state_id': state.id if state else None,
                    'comment': contact['personalNotes'] if contact['personalNotes'] else None,
                    'zip': contact['homeAddress']['postalCode'] if contact['homeAddress'] else None,
                })

    @http.route('/office/contacts/deleted', type='http', auth='public', csrf=False)
    def office_contact_delete(self, **kw):
        """Function to delete a contact on office 365 contact deletion"""
        validation_token = request.params.get('validationToken')
        if validation_token:
            return validation_token
        connector_id = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.contact_office_connector_id')
        connector = request.env['cyllo.office.connector'].sudo().browse(int(connector_id))
        if connector:
            if connector.onedrive_token_validity <= fields.Datetime.now():
                connector.action_refresh_office_365_tokens()
        request_body = json.loads(request.httprequest.data)
        if request_body:
            if request_body['value']:
                contact_update = request.env['cyllo.office.connector.line'].sudo().search(
                    [('type', '=', 'partner'),
                     ('office_365_identifier', '=', request_body['value'][0]['resourceData']['id'])])
                if contact_update:
                    contact_update.partner_id.unlink()

    @http.route('/office/to_do/create', type='http', auth='public', csrf=False)
    def office_todo_create(self, **kw):
        """Function to create to do on office 365 to do creation"""
        validation_token = request.params.get('validationToken')
        if validation_token:
            return validation_token
        connector_id = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.todo_office_connector_id')
        connector = request.env['cyllo.office.connector'].sudo().browse(int(connector_id))
        if connector:
            if connector.onedrive_token_validity <= fields.Datetime.now():
                connector.action_refresh_office_365_tokens()
        request_body = json.loads(request.httprequest.data)
        resource_id = request_body['value'][0]['resourceData']['id']
        api_url = f"https://graph.microsoft.com/v1.0/me/todo/lists('{connector.task_list}')/tasks('{resource_id}')"
        access_token = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.office_todo_access_token')
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            odoo_to_do_connectors = request.env['cyllo.office.connector.line'].sudo().search([
                ('type', '=', 'activity')]).mapped('office_365_identifier')
            task = response.json()
            if task['id'] not in odoo_to_do_connectors and task['id']:
                due_date = fields.Date.context_today(connector)
                if task['status'] != 'completed':
                    activity_type = request.env['mail.activity.type'].sudo().search([('name', '=', 'To-Do')])
                    if not activity_type:
                        activity_type = request.env['mail.activity.type'].sudo().create({
                            'name': 'To-Do', 'category': 'default'})
                    if 'dueDateTime' in task:
                        due_date_time = task['dueDateTime']['dateTime'][:-8]
                        due_date = datetime.strptime(due_date_time, '%Y-%m-%dT%H:%M:%S').date()
                    activity = request.env['mail.activity'].sudo().create({
                        'summary': task['title'],
                        'activity_type_id': activity_type.id,
                        'note': task['body']['content'],
                        'date_deadline': due_date if due_date else None,
                        'res_model_id': request.env['ir.model'].sudo()._get_id('res.partner'),
                        'res_id': request.env.user.partner_id.id,
                        'user_id': request.env.user.id,
                    })
                    activity.sudo().update({
                        'office_connectors_ids': [fields.Command.create({'office_365_identifier': task['id'],
                                                                         'connector_id': connector.id,
                                                                         'type': 'activity',
                                                                         'activity_id': activity.id})]
                    })

    @http.route('/office/to_do/deleted', type='http', auth='public', csrf=False)
    def office_todo_delete(self, **kw):
        """Function to delete to do on office 365 to do deletion"""
        validation_token = request.params.get('validationToken')
        if validation_token:
            return validation_token
        connector_id = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.todo_office_connector_id')
        connector = request.env['cyllo.office.connector'].sudo().browse(int(connector_id))
        if connector:
            if connector.onedrive_token_validity <= fields.Datetime.now():
                connector.action_refresh_office_365_tokens()
        request_body = json.loads(request.httprequest.data)
        if request_body:
            if request_body['value']:
                activity_update = request.env['cyllo.office.connector.line'].sudo().search(
                    [('type', '=', 'activity'),
                     ('office_365_identifier', '=', request_body['value'][0]['resourceData']['id'])])
                if activity_update:
                    activity_update.activity_id.unlink()

    @http.route('/office/to_do/updated', type='http', auth='public', csrf=False)
    def office_todo_update(self, **kw):
        """Function to update to do on office 365 to do updation"""
        validation_token = request.params.get('validationToken')
        if validation_token:
            return validation_token
        connector_id = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.todo_office_connector_id')
        connector = request.env['cyllo.office.connector'].sudo().browse(int(connector_id))
        if connector:
            if connector.onedrive_token_validity <= fields.Datetime.now():
                connector.action_refresh_office_365_tokens()
        request_body = json.loads(request.httprequest.data)
        resource_id = request_body['value'][0]['resourceData']['id']
        api_url = f"https://graph.microsoft.com/v1.0/me/todo/lists('{connector.task_list}')/tasks('{resource_id}')"
        access_token = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_office_365_connector.office_todo_access_token')
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            odoo_to_do_connectors = request.env['cyllo.office.connector.line'].sudo().search([
                ('type', '=', 'activity')]).mapped('office_365_identifier')
            task = response.json()
            if task['id'] not in odoo_to_do_connectors and task['id']:
                due_date = fields.Date.context_today(connector)
                if task['status'] != 'completed':
                    activity_type = request.env['mail.activity.type'].sudo().search([('name', '=', 'To-Do')])
                    if not activity_type:
                        activity_type = request.env['mail.activity.type'].sudo().create({
                            'name': 'To-Do', 'category': 'default'})
                    if 'dueDateTime' in task:
                        due_date_time = task['dueDateTime']['dateTime'][:-8]
                        due_date = datetime.strptime(due_date_time, '%Y-%m-%dT%H:%M:%S').date()
                    activity = request.env['mail.activity'].sudo().create({
                        'summary': task['title'],
                        'activity_type_id': activity_type.id,
                        'note': task['body']['content'],
                        'date_deadline': due_date if due_date else None,
                        'res_model_id': request.env['ir.model'].sudo()._get_id('res.partner'),
                        'res_id': request.env.user.partner_id.id,
                        'user_id': request.env.user.id,
                    })
                    activity.sudo().update({
                        'office_connectors_ids': [fields.Command.create({'office_365_identifier': task['id'],
                                                                         'connector_id': connector.id,
                                                                         'type': 'activity',
                                                                         'activity_id': activity.id})]
                    })
            else:
                odoo_to_do = request.env[
                    'cyllo.office.connector.line'].sudo().search([('type', '=', 'activity'),
                                                                  ('office_365_identifier', '=', task['id'])])
                due_date = fields.Date.context_today(connector)
                if task['status'] != 'completed':
                    activity_type = request.env['mail.activity.type'].sudo().search([('name', '=', 'To-Do')])
                    if not activity_type:
                        activity_type = request.env['mail.activity.type'].sudo().create({
                            'name': 'To-Do', 'category': 'default'})
                    if 'dueDateTime' in task:
                        due_date_time = task['dueDateTime']['dateTime'][:-8]
                        due_date = datetime.strptime(due_date_time, '%Y-%m-%dT%H:%M:%S').date()
                    odoo_to_do.activity_id.sudo().write({
                        'summary': task['title'],
                        'activity_type_id': activity_type.id,
                        'note': task['body']['content'],
                        'date_deadline': due_date if due_date else None,
                        'res_model_id': request.env['ir.model'].sudo()._get_id('res.partner'),
                        'res_id': request.env.user.partner_id.id,
                        'user_id': request.env.user.id,
                    })
