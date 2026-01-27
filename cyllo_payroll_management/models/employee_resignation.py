# -*- coding: utf-8 -*-
import base64
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EmployeeResignation(models.Model):
    """To create resignation request for the employee"""
    _name = 'employee.resignation'
    _description = 'Employee Resignation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'

    reference = fields.Char(readonly=True, copy=False, default='New', string='Sequence')
    employee_id = fields.Many2one('hr.employee', help='To choose the employee')
    image_1920 = fields.Binary(related='employee_id.image_1920')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    contract_id = fields.Many2one(domain="[('employee_id', '=', employee_id)]", readonly=False,
                                  related='employee_id.contract_id')
    department_id = fields.Many2one('hr.department', required=True)
    joining_date = fields.Date(related='contract_id.date_start')
    end_date = fields.Date(related='contract_id.date_end')
    confirmed_date = fields.Date(help='The date when the resignation request, is confirmed by the employee itself')
    approved_date = fields.Date(help='The date when the resignation request, is approved by the manager')
    leaving_date = fields.Date(help='The date when the employee leaving after the notice period',
                               compute='_compute_leaving_date', store=True)
    notice_period = fields.Integer(help='Notice period of the employee, in days')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('waiting', 'Waiting'),
                              ('approved', 'Approved'), ('cancel', 'Rejected')], string='Status', default='draft',
                             track_visibility="always")
    resignation_type_id = fields.Many2one('resigned.reasons',
                                          help="Select the type of resignation", required=True)
    reason = fields.Text(string='Reason In Detail', help='To add the reason of the resignation', required=True)
    total_working_years = fields.Float(string='Total Years Worked', readonly=True, help="Total working years")
    leave_taken = fields.Float(string='Training Period(Years)', readonly=True, help="Employee training years")
    gratuity_years = fields.Float(string='Gratuity Calculation Years', readonly=True, help="Employee gratuity years")
    basic_salary = fields.Float(readonly=True, help="Employee's basic salary.")
    gratuity_amount = fields.Float(readonly=True)
    gratuity_settlement_id = fields.Many2one('gratuity.settlement',
                                             help='Relation to the gratuity settlement')

    @api.depends('confirmed_date', 'notice_period')
    def _compute_leaving_date(self):
        """The function is used to confirm the leaving date after approving the request"""
        for rec in self:
            if rec.approved_date and rec.notice_period:
                approved_date = fields.Date.from_string(rec.approved_date)
                leaving_date = approved_date + timedelta(days=rec.notice_period)
                rec.leaving_date = fields.Date.to_string(leaving_date)
            else:
                rec.leaving_date = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Check for existing active requests when the employee is changed."""
        if self.employee_id:
            existing_requests = self.search([('employee_id', '=', self.employee_id.id),
                                             ('state', 'in', ['confirm', 'approved'])])
            if existing_requests and not self.env.user.has_group(
                    'cyllo_payroll_management.group_cyllo_payroll_management_manager'):
                raise ValidationError(
                    _('There is already an active or approved resignation request for this employee'))

    @api.constrains('employee_id')
    def _check_employee_id(self):
        """"To check the employee has the permission to create resignation request for another employee"""
        if not self.env.user.has_group('cyllo_payroll_management.group_cyllo_payroll_management_manager'):
            for rec in self.filtered(
                    lambda x: x.employee_id.user_id.id and rec.employee_id.user_id.id != self.env.uid):
                raise ValidationError(_('You cannot create a request for other employees'))

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('employee.resignation') or 'New'
        return super(EmployeeResignation, self).create(vals)

    def action_confirm_request(self):
        """The function is used to confirm the request"""
        return {
            'name': 'Confirm Resignation Request',
            'type': 'ir.actions.act_window',
            'res_model': 'resignation.request.confirm',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_reference': self.reference,
                        'default_employee_id': self.employee_id.id,
                        'default_department_id': self.department_id.id},
        }

    def action_cancel_request(self):
        """The function is used to cancel the request"""
        self.write({'state': 'cancel'})

    def action_approve_request(self):
        """The function is used to approve the request"""
        gratuity_details = self.env['gratuity.settlement'].sudo().search([('employee_id', '=', self.employee_id.id)],
                                                                         limit=1)
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_date': fields.datetime.now()
            })
            if rec.approved_date and not rec.notice_period:
                raise ValidationError(_('Please add the notice period for the employee(in days)'))
            for gratuity in gratuity_details:
                rec.write({
                    'gratuity_settlement_id': gratuity.id,
                    'leave_taken': gratuity.leave_taken,
                    'total_working_years': gratuity.total_working_years,
                    'basic_salary': gratuity.basic_salary,
                    'gratuity_years': gratuity.gratuity_years,
                    'gratuity_amount': gratuity.gratuity_amount
                })

    def action_reject_request(self):
        """The function is used to reject the request"""
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        """The function is used set the request in draft state"""
        self.write({'state': 'draft'})

    def action_send_mail(self):
        """To send the resignation request to the department
        manager and the employee's direct manager"""
        resignation_report_template_id = self.env['ir.actions.report']._render_qweb_pdf(
            report_ref='cyllo_payroll_management.report_resignation_request', data=None, res_ids=self.ids)
        data_record = base64.b64encode(resignation_report_template_id[0])
        ir_values = {
            'name': "Resignation Request",
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
        }
        data_id = self.env['ir.attachment'].create(ir_values)
        template_id = self.env.ref('cyllo_payroll_management.mail_template_resignation_request')
        template_id.attachment_ids = [fields.Command.set([data_id.id])]
        department_manager = self.department_id.manager_id.user_id.partner_id
        employee_manager = self.employee_id.parent_id.user_id.partner_id
        if not department_manager or not employee_manager:
            raise ValidationError(_("You can't send the mail because either "
                                    "the department manager or employee manager is missing."))
        else:
            for rec in self:
                rec.write({'state': 'waiting'})
            email_values = {
                'recipient_ids': [fields.Command.link(department_manager.id), fields.Command.link(employee_manager.id)],
                'email_from': self.employee_id.work_email
            }
            self.env['mail.template'].browse(template_id.id).send_mail(self.id, email_values=email_values,
                                                                       force_send=True)
            template_id.attachment_ids = [fields.Command.unlink(data_id.id)]
