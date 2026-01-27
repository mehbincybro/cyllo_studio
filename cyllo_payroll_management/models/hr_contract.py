# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    """To create employee contract """
    _inherit = 'hr.contract'

    employee_salary_structure_id = fields.Many2one('employee.salary.structure', string='Salary Structure',
                                                   domain="[('country_id', '=', ""company_country_id)]")
    yearly_wage = fields.Float(string='Yearly Cost', help='To get the yearly cost',
                               compute='_compute_yearly_wage', store=True)
    training_date_from = fields.Date(string='Training Start Date')
    training_date_to = fields.Date(string='Training End Date')
    wage_type = fields.Selection([('monthly', 'Monthly Fixed Wage'), ('hourly', 'Hourly Wage')])
    default_schedule_pay = fields.Selection(related='employee_salary_structure_id.schedule_pay',
                                            string='Scheduled Pay', index=True,
                                            help="Defines the frequency of the wage payment.", readonly=False)
    state = fields.Selection(selection_add=[('training', 'Training Period'), ('open',)])
    is_approved = fields.Boolean(default=False, help='To check the contract is approved or not')
    hourly_wage = fields.Monetary('Hourly Wage', digits=(16, 2), default=0, required=True, tracking=True,
                                  help="Employee's hourly gross wage.")
    training_date_start = fields.Date(string='Start Date', help='This field to show the starting date of the employees '
                                                                'training period')
    training_date_end = fields.Date(string='End Date', help='This field to show the end date of the employees training'
                                                            ' period')
    house_rent = fields.Monetary(string='HRA', help="House rent allowance of the employee")
    travel_allowance = fields.Monetary(help="Travel allowance for the employee")
    dearness_allowance = fields.Monetary(help="The dearness allowance for the employee")
    meal_allowance = fields.Monetary(help="The meal allowance for the employees")
    medical_allowance = fields.Monetary(help="The medical allowance for the employees")
    other_allowance = fields.Monetary(help="The other allowance for employees")
    employee_training_period_id = fields.Many2one('employee.training.period')
    half_time_off_ids = fields.Many2many('hr.leave')

    @api.depends('wage')
    def _compute_yearly_wage(self):
        """To calculate the yearly wage based on working days"""
        for contract in self.filtered(lambda x: x.wage):
            contract.yearly_wage = contract.wage * 12

    @api.onchange('state')
    def _onchange_state(self):
        """The function is used to check while changing the state the contract is approved or not"""
        for rec in self:
            if not rec.is_approved and rec.state in ['training']:
                raise ValidationError(_("You cannot change the status of non-approved Contracts"))
            elif rec.state in ['open', 'close', 'cancel']:
                return
            else:
                return

    def get_all_structures(self):
        """ @return: the structures linked to the given contracts, ordered by hierarchy (parent=False first,then
        first level children and so on) and without duplicate"""
        structures = self.mapped('employee_salary_structure_id')
        if not structures:
            return []
        return list(set(structures._get_parent_structure().ids))

    def action_approve_contract(self):
        """The button is used to approve the contract after ending the training period,
        it will move to the open state, that means the contract is running"""
        for contract in self:
            if not contract.training_date_from and not contract.training_date_to:
                raise ValidationError(_("Please add the Training Start Date and End Date"))
            if contract.training_date_from and contract.training_date_to:
                contract.sudo().write({'is_approved': True})
                if contract.state == 'training':
                    contract.sudo().write({'state': 'open',
                                           'date_start': contract.training_date_to,
                                           'date_end': False})
            training_period = self.env['employee.training.period'].sudo().search(
                [('employee_id', '=', self.employee_id.id)])
            for rec, training in zip(self, training_period):
                if rec.state == 'open' and training:
                    rec.training_date_start = training.start_date
                    rec.training_date_end = training.end_date

    @api.model
    def create(self, vals_list):
        """Function for create a record based on training details of an employee in a model"""
        if not vals_list.get('employee_id'):
            raise ValidationError(_("Please choose an employee for the contract"))
        if not vals_list.get('training_end_date') and vals_list.get('state') == 'draft':
            training_details = self.env['employee.training.period'].sudo().create({
                'employee_id': vals_list.get('employee_id'),
                'start_date': vals_list.get('training_date_from'),
                'end_date': vals_list.get('training_date_to'),
            })
            vals_list['employee_training_period_id'] = training_details.id
            vals_list['state'] = 'training'
        res = super(HrContract, self).create(vals_list)
        return res
