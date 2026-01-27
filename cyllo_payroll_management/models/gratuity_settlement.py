# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class GratuitySettlement(models.Model):
    """To create gratuity settlement of the employee"""
    _name = 'gratuity.settlement'
    _description = 'Gratuity Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'

    reference = fields.Char(copy=False, readonly=True, default=lambda self: _('New'), help='Reference of the record')
    employee_id = fields.Many2one('hr.employee', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, help="Company",
                                 index=True, default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('submit', 'Submitted'), ('approve', 'Approved'),
                              ('cancel', 'Cancelled')], default='draft', tracking=True)
    contract_type = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], readonly=True,
                                     help="If the contract have the end date then the contract type is limited, "
                                          "if the contract have not the end date the contract type will be unlimited")
    joining_date = fields.Date(readonly=True, help="Employee joining date")
    wage_type = fields.Selection([('monthly', 'Monthly Fixed Wage'), ('hourly', 'Hourly Wage')],
                                 help="Select the wage type monthly or hourly")
    total_working_years = fields.Float(string='Total Years Worked', readonly=True, help="Total working years")
    leave_taken = fields.Float(string='Training Period(Years)', readonly=True, help="Employee training years")
    gratuity_years = fields.Float(string='Gratuity Calculation Years', readonly=True, help="Employee gratuity years")
    basic_salary = fields.Float(readonly=True, help="Employee's basic salary.")
    gratuity_duration_line_id = fields.Many2one('gratuity.configuration.line',
                                                readonly=True, string='Configuration Line')
    gratuity_configuration_id = fields.Many2one('gratuity.configuration', readonly=True)
    gratuity_amount = fields.Float(string='Gratuity Payment', readonly=True,
                                   help="It is calculated, If the wage type is hourly then gratuity payment is "
                                        "calculated as employee basic salary * Employee Working days * gratuity "
                                        "configration rule percentage * gratuity calculation years."
                                        "If the wage type is monthly then gratuity payment is calculated as "
                                        "employee basic salary * (Working Days/Employee Daily Wage Days) *  gratuity "
                                        "configration rule percentage * gratuity calculation years.")
    credit_account_id = fields.Many2one('account.account', help="Gratuity credit account", required=True)
    debit_account_id = fields.Many2one('account.account', help="Gratuity debit account", required=True)
    journal_id = fields.Many2one('account.journal', help="Gratuity journal", required=True)
    currency_id = fields.Many2one(related="company_id.currency_id", help="To get the Currency")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Filling the necessary details for the gratuity after choosing the employee, and calculating the gratuity
        amount based on the worked years of the employee and the configuration we set in the gratuity configuration"""
        if self.employee_id:
            employee_contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id),
                                                                 ('state', '=', 'open')], order='date_start')
            if not employee_contracts:
                raise ValidationError(_('There are no running contracts available for the chosen employee.'
                                        'The employee needs to be under an running contract in '
                                        'order to calculate their gratuity settlement.'))
            latest_contract = employee_contracts[0]
            if latest_contract:
                self.write({
                    'joining_date': latest_contract.date_start,
                    'wage_type': latest_contract.wage_type,
                    'contract_type': 'limited' if latest_contract.date_end else 'unlimited'
                })
                if self.wage_type == 'monthly' or not self.wage_type:
                    self.basic_salary = employee_contracts.wage
                else:
                    self.basic_salary = employee_contracts.hourly_wage
            if len(employee_contracts) > 1:
                raise ValidationError(_('The employee has multiple running contracts. Please ensure there is only '
                                        'one active contract for gratuity calculation.'))

            training_period = self.env['employee.training.period'].search([('employee_id', '=', self.employee_id.id)])
            employee_training_days = 0
            for training in training_period:
                start_date = training.start_date
                end_date = training.end_date
                employee_training_days += (end_date - start_date).days

            if latest_contract.date_end:
                self.contract_type = 'limited'
                working_days = (latest_contract.date_end - self.joining_date).days
                self.total_working_years = working_days / 365
                self.leave_taken = employee_training_days / 365
                gratuity_years = (working_days - employee_training_days) / 365
                self.gratuity_years = gratuity_years
            else:
                self.contract_type = 'unlimited'
                working_days = (fields.date.today() - self.joining_date).days
                self.total_working_years = working_days / 365
                self.leave_taken = employee_training_days / 365
                gratuity_years = (working_days - employee_training_days) / 365
                self.gratuity_years = round(gratuity_years, 2)

        # Set gratuity configuration based on contract type
        gratuity_config_id = False
        if self.contract_type:
            configuration = self.env['gratuity.configuration'].search(
                [('contract_type', '=', self.contract_type), '|', ('end_date', '>=', fields.date.today()),
                 ('end_date', '=', False), '|', ('start_date', '<=', fields.date.today()), ('start_date', '=', False)])
            if not configuration:
                raise ValidationError(_('No gratuity configuration found, please check the dates.'))
            if len(configuration) > 1:
                raise ValidationError(_("In Gratuity's configuration, there is a date conflict. "
                                        "Kindly resolve the disagreement and give it another go."))
            else:
                pass
            self.gratuity_configuration_id = configuration.id
            configuration_ids = configuration.gratuity_configuration_ids.mapped('id')
            configuration_line_ids = self.env['gratuity.configuration.line'].browse(configuration_ids)
            for config in configuration_line_ids:
                if (config.from_year and config.to_year and config.from_year <=
                        self.total_working_years <= config.to_year):
                    gratuity_config_id = config
                    break
                elif config.from_year and not config.to_year and config.from_year <= self.total_working_years:
                    gratuity_config_id = config
                    break
                elif config.to_year and not config.from_year and self.total_working_years <= config.to_year:
                    gratuity_config_id = config
                    break

            if gratuity_config_id:
                self.gratuity_duration_line_id = gratuity_config_id.id
            else:
                raise ValidationError(_('No configuration for an acceptable gratuity was found!'))
            if self.total_working_years < 1 and self.employee_id.id:
                raise ValidationError(_('Gratuity Settlement is not available to Selected Employees.'))
            self.journal_id = configuration.journal_id.id
            self.credit_account_id = configuration.credit_account_id.id
            self.debit_account_id = configuration.debit_account_id.id

            if self.gratuity_duration_line_id and self.wage_type == 'hourly':
                if self.gratuity_duration_line_id.working_days != 0:
                    if self.employee_id.resource_calendar_id and self.employee_id.resource_calendar_id.hours_per_day:
                        daily_wage = self.basic_salary * self.employee_id.resource_calendar_id.hours_per_day
                    else:
                        daily_wage = self.basic_salary * 8
                    salary_of_worked_days = daily_wage * self.gratuity_duration_line_id.working_days
                    gratuity_amount_of_a_year = salary_of_worked_days * self.gratuity_duration_line_id.percentage
                    gratuity_amount = gratuity_amount_of_a_year * round(self.gratuity_years, 2)
                    self.gratuity_amount = round(gratuity_amount, 2)
                else:
                    raise ValidationError(_("Working days of the employee is not configured in "
                                            "the gratuity configuration!"))
            elif self.gratuity_duration_line_id and self.wage_type == 'monthly' or not self.wage_type:
                if self.gratuity_duration_line_id.daily_wage != 0:
                    daily_wage = self.basic_salary / self.gratuity_duration_line_id.daily_wage
                    salary_of_worked_days = daily_wage * self.gratuity_duration_line_id.working_days
                    gratuity_amount_of_a_year = salary_of_worked_days * self.gratuity_duration_line_id.percentage
                    gratuity_amount = gratuity_amount_of_a_year * round(self.gratuity_years, 2)
                    self.gratuity_amount = round(gratuity_amount, 2)
                else:
                    raise ValidationError(_("Wage days of employee is not configured in the gratuity configuration!"))

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('gratuity.settlement') or 'New'
        return super(GratuitySettlement, self).create(vals)

    def action_submit(self):
        """To submit the gratuity settlement"""
        self.write({'state': 'submit'})

    def action_approve(self):
        """To approve the gratuity settlement"""
        for rec in self:
            debit_account_values = {
                'name': rec.employee_id.name,
                'account_id': rec.debit_account_id.id,
                'partner_id': rec.employee_id.user_partner_id.id or False,
                'journal_id': rec.journal_id.id,
                'date': fields.date.today(),
                'debit': rec.gratuity_amount > 0.0 and rec.gratuity_amount or 0.0,
                'credit': rec.gratuity_amount < 0.0 and -rec.gratuity_amount or 0.0,
            }
            credit_account_values = {
                'name': rec.employee_id.name,
                'account_id': rec.credit_account_id.id,
                'partner_id': rec.employee_id.user_partner_id.id or False,
                'journal_id': rec.journal_id.id,
                'date': fields.date.today(),
                'debit': rec.gratuity_amount < 0.0 and -rec.gratuity_amount or 0.0,
                'credit': rec.gratuity_amount > 0.0 and rec.gratuity_amount or 0.0,
            }
            values = {
                'name': rec.reference + " - " + 'Gratuity Settlement for' + ' ' + rec.employee_id.name,
                'ref': rec.reference,
                'partner_id': rec.employee_id.user_partner_id.id or False,
                'journal_id': rec.journal_id.id,
                'date': fields.date.today(),
                'line_ids': [fields.Command.create(debit_account_values), fields.Command.create(credit_account_values)],
            }
            move_id = self.env['account.move'].create(values)
            move_id.action_post()
        self.write({'state': 'approve'})

    def action_cancel(self):
        """To cancel the gratuity settlement"""
        self.write({'state': 'cancel'})
