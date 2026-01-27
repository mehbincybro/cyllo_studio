# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class AddressCount(CustomerPortal):
    """
    This class extends the CustomerPortal class to add the functionality of
    counting addresses. It overrides the '_prepare_home_portal_values' method
    to include the count of addresses related to the user's employee.
    """

    def _prepare_home_portal_values(self, counters):
        """
        Prepare the values for the home portal page.
        :param counters(dict): A dictionary containing various counters for
        different features on the portal.
        :return: A dictionary containing the prepared values for the home
        portal page.
        """
        vals = super()._prepare_home_portal_values(counters)
        if 'address_count' in counters:
            vals['address_count'] = request.env['res.partner'].search_count([
                ('parent_id', '=', request.env.user.partner_id.id), ("type", "in", ["delivery", "other"])]) + 1
        if 'login_and_security' in counters:
            vals['login_and_security'] = 1 if request.env.user else 0
        return vals


class PortalAddress(http.Controller):
    """
    This class defines HTTP routes for handling user addresses in portal view.

    The routes handle displaying, adding, editing, and removing user addresses
    on the portal.
    """

    @http.route(['/your_address'], type='http', auth="user", website=True)
    def your_address_views(self):
        """
        Display the user's addresses on the website.This method handles the
        HTTP route '/your_address', which is responsible for rendering the
        user's addresses on the portal.

        Returns:
            An HTTP response that renders the template to show all addresses
            of the user.
        """
        partner = request.env.user.partner_id.with_context(show_address=1).sudo()
        shippings = partner.search([("id", "child_of", request.env.user.partner_id.commercial_partner_id.ids),
                                    '|', ("type", "in", ["delivery", "other"]),
                                    ("id", "=", request.env.user.partner_id.commercial_partner_id.id)], order='id desc')
        return request.render("cyllo_portal.portal_your_address_template", {'shippings': shippings,
                                                                            'page_name': 'addresses'})

    @http.route(['/login/security'], type='http', auth="user", website=True)
    def login_and_security(self):
        """
        Display the login and security details of the user on the website.
        This method handles the HTTP route '/login/security', which is
        responsible for rendering the user's login and security details on
        the portal.
        Returns:
            An HTTP response that renders the 'portal_details_template' with
            the user's login and security details.
        """
        return request.render("cyllo_portal.portal_details_template", {'user': request.env.user,
                                                                       'page_name': 'login_and_security'})

    @http.route(['/login/security/edit/name'], type='http', auth="user", website=True)
    def edit_name_details(self):
        """
        Display the form for editing the user's name.
        This method handles the HTTP route '/login/security/edit/name', which
        is responsible for rendering the form to edit the user's name on
        the portal.
        Returns:
            An HTTP response that renders the 'portal_details_edit_template'
             with the form for editing the user's name.
        """
        return request.render("cyllo_portal.portal_details_edit_template", {'user_name': request.env.user.name,
                                                                            'page_name': 'edit_name_details'})

    @http.route(['/login/security/edit/email'], type='http', auth="user", website=True)
    def edit_email_details(self):
        """
        Display the form for editing the user's email.
        This method handles the HTTP route '/login/security/edit/email', which
        is responsible for rendering the form to edit the user's email on the
         portal.
        Returns:
            An HTTP response that renders the 'portal_details_edit_template'
             with the form for editing the user's email.
        """
        return request.render("cyllo_portal.portal_details_edit_template", {'user_mail': request.env.user.email,
                                                                            'page_name': 'edit_email_details'})

    @http.route(['/login/security/edit/phone'], type='http', auth="user", website=True)
    def edit_phone_details(self):
        """
        Display the form for editing the user's phone number.
        This method handles the HTTP route '/login/security/edit/phone', which
        is responsible for rendering the form to edit the user's phone number
        on the portal.
        Returns:
            An HTTP response that renders the 'portal_details_edit_template'
            with the form for editing the user's phone number.
        """
        return request.render("cyllo_portal.portal_details_edit_template", {'user_phone': request.env.user.phone,
                                                                            'page_name': 'edit_phone_details'})

    @http.route(['/login/security/save'], type='http', auth="user", website=True)
    def save_details(self, **post):
        """
        Save the edited details of the user.
        This method handles the HTTP route '/login/security/save', which is
        responsible for saving the edited details of the user.
        Parameters:
        **post (dict): A dictionary containing the edited details of the user.
        Returns:
            An HTTP response that renders the 'portal_details_template' with
            the updated details of the user.
        """
        user_vals = {key: post[key] for key in ['name', 'phone', 'email'] if post.get(key)}
        request.env.user.sudo().write(user_vals)
        return request.render("cyllo_portal.portal_details_template",
                              {'user': request.env.user, 'change': True, 'page_name': 'login_and_security'})

    @http.route(['/add/address'], type='http', auth="user", website=True)
    def add_address_views(self):
        """
        Display the 'Add Address' form on the portal.
        This method handles the HTTP route '/add/address',which is responsible
        for rendering the 'Add Address' form on the portal.
        Returns:
            An HTTP response that renders the 'portal_add_address_template'
            template with the 'countries' values, representing the list of
            countries to be displayed in the form.
        """
        return request.render("cyllo_portal.portal_add_address_template",
                              {'countries': request.env['res.country'].search([])})

    @http.route(['/address/added'], type='http', auth="user", website=True, csrf=False)
    def address_added(self, **kwargs):
        """
        Handle the form submission to add a new address.
        This method handles the HTTP route '/address/added', which is
        responsible for adding a new address to the user's account based on
        the submitted form data.

        Parameters:
        **kwargs (dict): A dictionary containing the form data submitted by
        the user.

        Returns:
        An HTTP redirect response that redirects the user to the 'your_address'
        page after the new address has been added to their account.
        """
        if kwargs:
            request.env['res.partner'].sudo().create([{
                'name': kwargs.get('name_address'),
                'parent_id': request.env.user.partner_id.id,
                'email': kwargs.get('email'),
                'phone': kwargs.get('phone'),
                'country_id': int(kwargs.get('country_id')),
                'state_id': int(kwargs.get('state_id')) if kwargs.get('state_id') else False,
                'city': kwargs.get('city'),
                'zip': kwargs.get('zipcode'),
                'street': kwargs.get('street_and_number'),
                'street2': kwargs.get('street2'),
                'type': 'delivery'
            }])
        return request.redirect('/your_address')

    @http.route(['/address/edit'], type='http', auth="user", website=True, csrf=False)
    def address_edit(self):
        """
        Display the address edit form. This method handles the HTTP route
        '/address/edit', which is responsible for displaying the edit form for
        a specific address.

        Returns:
        An HTTP response containing the rendered template
        'portal_address_edit_template' with the necessary data to display the
        edit form.
        """
        partner = request.env['res.partner'].browse(int(request.params.get('res_id')))
        return request.render("cyllo_portal.portal_address_edit_template", {
            'partner': partner, 'countries': request.env['res.country'].search([]),
            'states': request.env['res.country.state'].search([('country_id', '=', partner.country_id.id)])})

    @http.route(['/address/save_changes'], type='http', auth="user", website=True, csrf=False)
    def address_save_changes(self, **kwargs):
        """
        Save the changes made to an address. This method handles the HTTP
        route '/address/save_changes', which is responsible for saving the
        changes made to a specific address.

        Parameters:
        **kwargs (dict): A dictionary containing the updated address details.

        Returns:
        An HTTP redirect response to the '/your_address' route to display
        the updated list of addresses.
        """
        partner = request.env['res.partner'].browse(int(request.params.get('res_id')))
        partner.update({
            'name': kwargs.get('name_address'),
            'parent_id': request.env.user.partner_id.id,
            'email': kwargs.get('email'),
            'phone': kwargs.get('phone'),
            'country_id': int(kwargs.get('country_id')),
            'state_id': int(kwargs.get('state_id')) if kwargs.get(
                'state_id') and request.env['res.country'].browse(int(kwargs.get('country_id'))).state_ids else False,
            'city': kwargs.get('city'),
            'zip': kwargs.get('zipcode'),
            'street': kwargs.get('street_and_number'),
            'street2': kwargs.get('street2'),
        })
        return request.redirect('/your_address')

    @http.route(['/address/remove/<int:res_id>'], type='http', auth="user", website=True)
    def address_remove(self, res_id):
        """
        Remove an address. This method handles the HTTP route
        '/address/remove/<int:res_id>', which is responsible for removing
        a specific address from the user's address list.

        Parameters:
        res_id (int): The ID of the address to be removed.

        Returns:
        An HTTP redirect response to the '/your_address' route to display
        the updated list of addresses.
        """
        request.env['res.partner'].browse(res_id).unlink()
        return request.redirect('/your_address')
