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
from odoo import fields, models


class AccountTax(models.Model):
    """Class of inherited model account_tax. Contains fields for Woocommerce
    id and instance id of tax and tax class."""
    _inherit = 'account.tax'

    woo_id = fields.Char(string="WooCommerce ID", readonly=True, copy=False,
                         help='Id in WooCommerce')
    instance_id = fields.Many2one('woo.commerce.instance', string="Instance",
                                  readonly=True, copy=False,
                                  help='WooCommerce Instance id.')
    tax_class = fields.Char(string="Tax Class", readonly=True, copy=False,
                            help='Class of the tax')


class AccountTaxGroup(models.Model):
    """Class of inherited model account_tax_group. Contains fields for
    Woocommerce id and instance id of tax group."""
    _inherit = 'account.tax.group'
    _description = 'Account Tax Group'

    woo_id = fields.Char(string="WooCommerce ID", readonly=True, copy=False,
                         help='Id in WooCommerce')
    instance_id = fields.Many2one('woo.commerce.instance', string="Instance",
                                  readonly=True, copy=False,
                                  help='WooCommerce Instance id.')
