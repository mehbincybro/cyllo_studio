# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Users(models.Model):
    """
    Customization of 'res.users' model to add additional functionality.
    """
    _inherit = 'res.users'

    first_time = fields.Boolean(default=False, help="A field to determine first time login")

    @api.model
    def custom_user_data(self, user_id):
        """
        Retrieve custom user data for the specified user.
        :param user_id: ID of the user to fetch data for.
        :return: Dictionary containing user-related data.
        """
        user = self.browse(user_id)
        if user:
            log = len(self.env['res.users.log'].search([('create_uid', '=', user_id)]))
            if log > 2:
                user.first_time = True
            company_id = user.company_id.id
            country_id = user.company_id.country_id.id
            user_data = user.read()[0]
            users = self.search_read([])
            company_data = self.env['res.company'].search_read([('id', '=', company_id)])
            country_state_data = self.env['res.country.state'].search_read([('country_id', '=', country_id)])
            all_companies_data = self.env['res.company'].search_read([])
            res_lang = self.env['res.lang'].search_read([])
            countries = self.env['res.country'].search_read([])
            details = {
                'first_time': user.first_time,
                'users': users,
                'user_data': user_data,
                'company_data': company_data,
                'country_state_data': country_state_data,
                'all_companies_data': all_companies_data,
                'res_lang': res_lang,
                "countries": countries,
            }
            return details

    @api.model
    def update_company(self, **kwargs):
        """
        Update the company data.
        :param kwargs: Keyword arguments representing the data to be updated.
        """
        comp = self.env['res.company'].browse(kwargs.get('id'))
        comp.write(kwargs)

    @api.model
    def clean_up_menus(self, user_id):
        """
        Clean up menus and set the 'first_time' flag for the specified user.
        :param user_id: ID of the user to perform cleanup for.
        """
        try:
            users = self.env['res.users'].search([])
            for user in users:
                user.write({'first_time': True})
            app_mass_install_menu = self.env.ref("cyllo_app_mass_install.menu_action_first_time")
            if app_mass_install_menu:
                app_mass_install_menu.active = False
        except Exception as e:
            _logger.info("An error occurred while cleaning up menus: %s" % str(e))
