# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import logging
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class JobCron(models.Model):
    """ Class for recording jobs to be done to sync woo commerce and odoo.
        Methods:
            _do_job(self):cron function to perform job created in specific
            interval.
    """
    _name = 'job.cron'
    _description = 'Cron Job '
    _rec_name = "model_id"

    model_id = fields.Many2one('ir.model', string='Model',
                               help="Model where the function written")
    instance_id = fields.Many2one('woo.commerce.instance',
                                  help="Instance Id on which have to "
                                       "sync the record", string='Instance',)
    function = fields.Char(string="Function", help="Function to be performed")
    data = fields.Json(string="Data", help="Data, arguments for the function")
    wizard = fields.Integer(string="Wizard Id", help="Current Wizards Id")
    state = fields.Selection([('pending', 'Pending'), ('done', 'Done'),
                              ('failed', 'Failed')], help="Status of record",
                             string='State', default='pending', readonly=True)

    @api.model
    def _do_job(self):
        """Method to do cron jobs for exporting and importing data."""
        job = self.env['job.cron'].sudo().search([('state', '=', 'pending')],
                                                 order='id asc')
        for rec in job:
            if rec:
                model = self.env[rec.model_id.model].sudo().search([])
                if rec.function == "product_create":
                    try:
                        model.product_create(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.error('Some error has been occurred in the '
                                      'processing of function:product_create')
                        rec.state = "failed"

                if rec.function == "product_data_post":
                    try:
                        model.product_data_post(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.error(
                            'Some error has been occurred in the processing'
                            ' of function:product_data_post')
                        rec.state = "failed"

                if rec.function == "customer_data_post":
                    try:
                        model.customer_data_post(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.error(
                            'Some error has been occurred in the processing'
                            ' of function:customer_data_post')
                        rec.state = "failed"

                if rec.function == "customer_data_woo_update":
                    try:
                        model.customer_data_woo_update(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info('Some error has been occurred in the '
                                     'processing of '
                                     'function:customer_data_woo_update')
                        rec.state = "failed"

                if rec.function == "customer_create":
                    try:
                        model.customer_create(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info('Some error has been occurred in the '
                                     'processing of '
                                     'function:customer_create')
                        rec.state = "failed"

                if rec.function == "product_data_woo_update":
                    try:
                        model.product_data_woo_update(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info('Some error has been occurred in the '
                                     'processing of '
                                     'function:product_data_woo_update')
                        rec.state = "failed"

                if rec.function == "order_data_woo_update":
                    try:
                        model.order_data_woo_update(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info('Some error has been occurred in the'
                                     ' processing of '
                                     'function:order_data_woo_update')
                        rec.state = "failed"

                if rec.function == "create_order":
                    try:
                        model.create_order(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info('Some error has been occurred in the '
                                     'processing of function:create_order')
                        rec.state = "failed"

                if rec.function == "order_data_post":
                    try:
                        model.order_data_post(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info('Some error has been occurred in the'
                                     ' processing of function:create_order')
                        rec.state = "failed"

                # Sync all button

                if rec.function == "write_customer":
                    try:
                        model.write_customer(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info(
                            'Some error has been occurred in the processing'
                            ' of function:write_customer')
                        rec.state = "failed"

                if rec.function == "write_product_data":
                    try:
                        model.write_product_data(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info(
                            'Some error has been occurred in the processing'
                            ' of function:write_product_data')
                        rec.state = "failed"

                if rec.function == "write_order_data":
                    try:
                        model.write_order_data(rec.data, rec.instance_id)
                        rec.state = "done"
                    except Exception as e:
                        _logger.info(
                            'Some error has been occurred in the processing'
                            ' of function:write_order_data')
                        rec.state = "failed"
