# -*- coding: utf-8 -*-
from odoo import api, models


class ResCompany(models.Model):
    """ Inheriting res company for creating rental locations. """
    _inherit = 'res.company'
    _check_company_auto = True

    def _create_rental_location(self):
        """ Create rental location for company. """
        for company in self:
            parent_location = self.env.ref('stock.stock_location_locations', raise_if_not_found=False)
            self.env['stock.location'].create({
                'name': 'Rental',
                'usage': 'internal',
                'is_rental_location': True,
                'location_id': parent_location.lot_stock_id.id,
                'company_id': company.id,
            })

    @api.model
    def create_missing_rental_location(self):
        """ Create a rental location for companies that do not have one. """
        company_ids = self.env['res.company'].search([])
        company_with_rental_location = self.env['stock.location'].search(
            [('name', '=', 'Rental')]).mapped('company_id')
        company_without_rental_location = (company_ids - company_with_rental_location)
        for company in company_without_rental_location:
            parent_locations = self.env['stock.warehouse'].search([('company_id', '=', company.id)])
            for parent_location in parent_locations:
                self.env['stock.location'].create({
                    'name': 'Rental',
                    'usage': 'internal',
                    'is_rental_location': True,
                    'location_id': parent_location.lot_stock_id.id,
                    'company_id': company.id,
                })

    @api.model_create_multi
    def create(self, vals_list):
        """Create multiple company records and their associated rental locations."""
        companies = super().create(vals_list)
        for company in companies:
            company.sudo()._create_rental_location()
        return companies
