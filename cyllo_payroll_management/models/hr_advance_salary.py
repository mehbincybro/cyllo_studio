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
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrAdvanceSalary(models.Model):
    _name = 'hr.advance.salary'
    _description = 'Advance Salary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'


    name = fields.Char(
        string="Reference",
        default="New",
        copy=False,
        readonly=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        tracking=True
    )

    request_date = fields.Date(
        string="Request Date",
        default=fields.Date.today
    )

    amount = fields.Float(
        string="Requested Amount",
        required=True,
        tracking=True
    )
    
    deduction_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Monthly Wage')
    ], string="Deduction Type", default='fixed', required=True,
        help="Choose how to calculate monthly deductions")
    
    deduction_amount = fields.Float(
        string="Fixed Deduction Amount",
        help="Fixed amount to deduct from each payslip"
    )
    
    deduction_percentage = fields.Float(
        string="Deduction Percentage",
        help="Percentage to deduct from each payslip (0-100)"
    )

    monthly_deduction_amount = fields.Float(
        string="Monthly Deduction Amount",
        compute="_compute_monthly_deduction_amount",
        help="Calculated monthly deduction amount based on the deduction type and percentage/fixed amount."
    )

    approval_date = fields.Date(
        string="Approval Date",
        readonly=True,
        tracking=True
    )

    reason = fields.Text(string="Reason")

    # Deduction tracking fields
    deducted_amount = fields.Float(
        string="Deducted Amount",
        compute="_compute_deducted_amount",
        store=True,
        help="Total amount already deducted from payslips"
    )
    remaining_amount = fields.Float(
        string="Remaining Amount",
        compute="_compute_remaining_amount",
        store=True,
        help="Amount still to be deducted from future payslips"
    )
    payslip_input_ids = fields.One2many(
        'employee.payslip.input',
        'advance_salary_id',
        string="Payslip Deductions",
        help="Payslip input lines that deducted from this advance"
    )

    bill_id = fields.Many2one(
        'account.move',
        string="Vendor Bill",
        readonly=True,
        tracking=True,
        help="Vendor bill created for this advance salary"
    )


    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('closed', 'Closed')
    ], default='draft', tracking=True)

    @api.onchange('deduction_type')
    def _onchange_deduction_type(self):
        """Clear the opposite field when switching deduction type"""
        if self.deduction_type == 'fixed':
            self.deduction_percentage = 0.0
        elif self.deduction_type == 'percentage':
            self.deduction_amount = 0.0
    
    @api.onchange('deduction_percentage')
    def _onchange_deduction_percentage(self):
        """Validate percentage is within valid range (0-100)"""
        if self.deduction_percentage < 0:
            self.deduction_percentage = 0.0
        elif self.deduction_percentage > 100:
            self.deduction_percentage = 100.0

    @api.depends('deduction_type', 'deduction_amount', 'deduction_percentage', 'employee_id')
    def _compute_monthly_deduction_amount(self):
        """Compute the monthly deduction amount based on the deduction type"""
        for rec in self:
            rec.monthly_deduction_amount = rec._get_monthly_deduction_amount()

    def _get_monthly_deduction_amount(self, contract=None):
        """Helper to calculate monthly deduction amount"""
        self.ensure_one()
        if self.deduction_type == 'fixed':
            return self.deduction_amount
        
        if not contract:
            contract = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
        
        if not contract:
            return 0.0

        if self.deduction_type == 'percentage':
            # Use contract.wage which is the monthly wage
            return (contract.wage or 0.0) * (self.deduction_percentage / 100.0)
        
        return 0.0
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'advance.salary.request'
            ) or 'New'
        return super().create(vals)

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            # Safety: if user forgot to set deduction
            if rec.deduction_type == 'fixed' and rec.deduction_amount <= 0:
                rec.deduction_amount = rec.amount
            elif rec.deduction_type == 'percentage' and rec.deduction_percentage <= 0:
                rec.deduction_percentage = 100.0
            rec.approval_date = fields.Date.today()
            rec.state = 'approved'
            
            # Generate schedule
            rec._generate_deduction_schedule()

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_create_bill(self):
        """Create a Vendor Bill for the advance salary amount"""
        for rec in self:
            if rec.bill_id:
                continue
                
            # Find the partner for the employee
            partner = rec.employee_id.work_contact_id or rec.employee_id.user_id.partner_id
            if not partner:
                partner = self.env['res.partner'].search([('name', '=', rec.employee_id.name)], limit=1)
                
            if not partner:
                raise UserError(_("Cannot find a related partner for this employee. Please set a work contact or user."))

            # Create Vendor Bill
            move_vals = {
                'move_type': 'in_invoice',
                'partner_id': partner.id,
                'date': fields.Date.today(),
                'invoice_date': fields.Date.today(),
                'ref': rec.name,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Advance Salary for {rec.employee_id.name} ({rec.name})",
                    'quantity': 1,
                    'price_unit': rec.amount,
                    # You might need an account here depending on config
                    # 'account_id': ... 
                })],
            }
            bill = self.env['account.move'].sudo().create(move_vals)
            rec.bill_id = bill.id
            rec.state = 'paid'
            return {
                'name': 'Vendor Bill',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': bill.id,
                'type': 'ir.actions.act_window',
            }

    def get_bill_action(self):
        """Action for the stat button to view the bill"""
        self.ensure_one()
        return {
            'name': 'Vendor Bill',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.bill_id.id,
            'type': 'ir.actions.act_window',
        }

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'

    @api.depends('payslip_input_ids', 'payslip_input_ids.amount')
    def _compute_deducted_amount(self):
        """Calculate total amount deducted from payslips"""
        for rec in self:
            # Sum absolute values since amounts are stored as negative
            rec.deducted_amount = abs(sum(rec.payslip_input_ids.mapped('amount')))

    @api.depends('amount', 'deducted_amount')
    def _compute_remaining_amount(self):
        """Calculate remaining amount to be deducted"""
        for rec in self:
            rec.remaining_amount = rec.amount - rec.deducted_amount

    @api.model
    def get_active_advances_for_employee(self, employee_id, date=None):
        """Get approved advances with remaining balance for an employee

        Args:
            employee_id: ID of the employee
            date: Reference date (default: today)

        Returns:
            recordset of hr.advance.salary with remaining balance
        """
        domain = [
            ('employee_id', '=', employee_id),
            ('state', '=', 'paid'),
            ('remaining_amount', '>', 0)
        ]
        return self.search(domain, order='request_date')

    @api.constrains('amount', 'deduction_type', 'deduction_amount')
    def _check_monthly_deduction_less_than_amount(self):
        for rec in self:
            if rec.deduction_type == 'fixed':
                if rec.deduction_amount >= rec.amount:
                    raise UserError(_(
                        "Monthly deduction amount must be less than the requested advance amount."
                    ))

    line_ids = fields.One2many(
        'hr.advance.salary.line',
        'advance_id',
        string="Deduction Schedule"
    )


    def _generate_deduction_schedule(self):
        """Generate predicted deduction lines"""
        self.ensure_one()
        self.line_ids.unlink()
        
        remaining = self.amount
        monthly = self.monthly_deduction_amount
        if monthly <= 0:
            return  # Or raise error?

        current_date = (self.approval_date or fields.Date.today()).replace(day=1)
        
        lines = []
        while remaining > 0:
            deduction = min(monthly, remaining)
            lines.append((0, 0, {
                'date': current_date,
                'amount': deduction,
            }))
            remaining -= deduction
            # Increment month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        self.write({'line_ids': lines})

class HrAdvanceSalaryLine(models.Model):
    _name = 'hr.advance.salary.line'
    _description = 'Advance Salary Deduction Line'
    _order = 'date asc'

    advance_id = fields.Many2one('hr.advance.salary', string="Advance Request", ondelete='cascade')
    date = fields.Date(string="Deduction Month")
    amount = fields.Float(string="Amount")
    payslip_id = fields.Many2one('employee.payslip', string="Payslip", readonly=True)
    state = fields.Selection([
        ('planned', 'Planned'),
        ('pending', 'Pending'),
        ('paid', 'Paid')
    ], string="Status", compute="_compute_state", store=True)

    @api.depends('payslip_id', 'payslip_id.state')
    def _compute_state(self):
        for rec in self:
            if not rec.payslip_id:
                rec.state = 'planned'
            else:
                rec.state = 'paid'

