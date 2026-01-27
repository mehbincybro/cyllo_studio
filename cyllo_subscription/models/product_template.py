# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """Inheriting the model to add some fields and can choose it
    subscription or not"""
    _inherit = "product.template"

    is_subscription = fields.Boolean(string="Subscription Product",
                                     help='If the product is recurring product enable the field')
    time_based_ids = fields.One2many('time.based.price', 'product_template_id', string='Time Based Price',
                                     help='Time based pricing')
    trial_period = fields.Integer(help='Trial period for the product (Only integers are supported.)')
    unit = fields.Selection(selection=[('weeks', 'Weeks'), ('months', 'Months'), ('days', 'Days')],
                            help='Unit for the trial period')

    @api.model_create_multi
    def create(self, vals_list):
        """ If the product being created is marked as a subscription and does
            not have any associated time-based pricing (time_based_ids), a
            ValidationError is raised, indicating that time-based pricing
            should be added.
            :param vals_list: List of dictionaries, each containing field-value
             pairs for creating multiple records.
            :raise ValidationError: If a product being created is a
             subscription and has no time-based pricing.
            :return: Result of the super().create() method.
        """
        for vals in vals_list:
            if ('is_subscription' in vals and vals['is_subscription'] and 'time_based_ids' in vals and not
            vals['time_based_ids']):
                raise ValidationError(_('Please add Time Based Pricing, because he product is a subscription product'))
            if 'unit' in vals and vals['unit'] and 'trial_period' in vals and vals['trial_period'] == 0:
                raise ValidationError(_('Trial period should be greater than zero if there is  trial unit'))
            if 'trial_period' in vals and vals['trial_period'] > 0 and 'unit' in vals and not vals['unit']:
                raise ValidationError(_('If Trial Period is added then Unit should be added'))
            return super().create(vals_list)

    def write(self, vals):
        """ If the product is marked as a subscription and does not have any
            associated time-based pricing (time_based_ids), a ValidationError
            is raised, indicating that time-based pricing should be added.
            :param vals: Dictionary of field-value pairs to be updated.
            :raise ValidationError: If the product is a subscription and has no
             time-based pricing.
            :return: Result of the super().write() method.
            """
        res = super().write(vals)
        if self.is_subscription and not self.time_based_ids:
            raise ValidationError(_('Please add Time Based Pricing, because the product is a subscription product'))
        if self.unit and self.trial_period == 0:
            raise ValidationError(_('Trial period should be greater than zero if there is trial unit'))
        elif self.trial_period > 0 and not self.unit:
            raise ValidationError(_('If Trial Period is added then Unit should be added'))
        return res
