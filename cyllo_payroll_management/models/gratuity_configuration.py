# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class GratuityConfiguration(models.Model):
    """To create gratuity configuration for the employee"""
    _name = 'gratuity.configuration'
    _description = 'Gratuity Configuration'

    name = fields.Char(help='To add the name of the configuration', required=True)
    contract_type = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    start_date = fields.Date()
    end_date = fields.Date()
    journal_id = fields.Many2one('account.journal', required=True)
    credit_account_id = fields.Many2one('account.account', help="Credit account for the gratuity",
                                        required=True)
    active = fields.Boolean(default=True)
    debit_account_id = fields.Many2one('account.account', help="Debit account for the gratuity",
                                       required=True)
    gratuity_configuration_ids = fields.One2many('gratuity.configuration.line',
                                                 'gratuity_configuration_id')

    _sql_constraints = [('unique_name', "unique(name)", "The name must be unique")]

    @api.onchange('start_date', 'end_date')
    def _onchange_start_date(self):
        """ Function to check date if it is added correct or not"""
        if self.start_date and self.end_date and not self.start_date < self.end_date:
            raise ValidationError(_("End date must be grater than the start date "))


class GratuityConfigurationLine(models.Model):
    """To create gratuity configuration for the employee"""
    _name = 'gratuity.configuration.line'
    _description = 'Gratuity Configuration Line'

    name = fields.Char(required=True)
    from_year = fields.Float()
    to_year = fields.Float()
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    daily_wage = fields.Integer(default=30, help="Total number of employee wage days")
    working_days = fields.Integer(default=21, help='Number of working days per month')
    percentage = fields.Float(default=1, help='To add the percentage')
    gratuity_configuration_id = fields.Many2one('gratuity.configuration')

    _sql_constraints = [('unique_name', "unique(name)", "The name must be unique")]

    @api.onchange('from_year', 'to_year')
    def _onchange_from_year(self):
        """ The onchange function is used to check, the year is configured correctly or not """
        if self.from_year and self.to_year and not self.from_year < self.to_year:
            raise ValidationError(_("'From Year' should be less than 'To Year'."))
