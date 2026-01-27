# -*- coding: utf-8 -*-
import calendar
from datetime import date

from odoo import _,api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import date_utils


class EmployeePayslipBatch(models.Model):
    """ The model is used to generate the payslip batch wise"""
    _name = 'employee.payslip.batch'
    _description = 'Employee Payslip Batches'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, help='Name for the batch payslip')
    employee_payslip_ids = fields.One2many('employee.payslip', 'employee_payslip_batch_id',
                                           string='The payslips that in the batch')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('paid', 'Paid'),
                              ('close', 'Closed')], string='Status', index=True, readonly=True, copy=False,
                             default='draft', help='State of the batch')
    start_date = fields.Date(string='Date From', required=True, help="Start date of batch payslip period",
                             default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    end_date = fields.Date(string='Date To', required=True, help="End date of batch payslip period",
                           compute='_compute_end_date')
    is_batch_payslip = fields.Boolean(string='Batch Payslip Enabled', default=False,
                                      help="If its checked, indicates that it generated batch payslip")
    journal_entry_count = fields.Integer()
    batch_move_line = fields.Boolean(string='Batch Payroll Move Line', related='company_id.batch_move_line')

    @api.depends('start_date')
    def _compute_end_date(self):
        """ Compute method to calculate the end date of the batch payslip"""
        for record in self:
            if record.start_date:
                end_of_month = calendar.monthrange(record.start_date.year, record.start_date.month)[1]
                record.end_date = record.start_date.replace(day=end_of_month)
            else:
                record.end_date = date_utils.end_of(fields.Date.today(), 'month')

    def action_draft(self):
        """ To rest into draft"""
        return self.write({'state': 'draft'})

    def action_close(self):
        """ To close the batch payslip"""
        for data in self.employee_payslip_ids:
            data.action_cancel()
        return self.write({'state': 'close'})

    def action_generate_batch(self):
        """This method is used to generate the payslip batch wise, that we
        selected in the batch list"""
        self.is_batch_payslip = True
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_payroll_management.action_view_employee_payslip_batch_list")
        return action

    def action_create_entry(self):
        """To generate the journal entry for the payslip"""
        self.write({'state': 'done'})
        for data in self.employee_payslip_ids:
            data.write({'batch': self.id})
            data.action_create_entry()

    def action_validate(self):
        """To create the move entry for the batch payslip if the batch move line is enabled"""
        payslip_ids = self.employee_payslip_ids
        amount_total = {}
        # Calculate total amounts for each type of entry
        for payslip in payslip_ids:
            sorted_lines = sorted(payslip.employee_payslip_line_ids,
                                  key=lambda line: line.id)
            for line in sorted_lines:
                if line.name in amount_total:
                    amount_total[line.name] += line.total
                else:
                    amount_total[line.name] = line.total
        # Create the account move
        account_move_vals = {
            'state': 'draft',
            'date': payslip_ids[0].to_date,
            'journal_id': payslip_ids[0].journal_id.id,
            'ref': payslip_ids[0].batch_payslip_name if payslip_ids[0].is_batch_payslip else payslip_ids[0].reference,
        }
        account_move = self.env['account.move'].create(account_move_vals)
        journal_item_ids = []
        line_ids = []
        # Create journal items for each type of entry
        for entry_name, total_amount  in amount_total.items():
            debit_lines = payslip_ids.employee_payslip_line_ids.filtered(lambda line: line.name.strip() == entry_name and line.account_debit_id)
            credit_lines = payslip_ids.employee_payslip_line_ids.filtered(lambda line: line.name.strip() == entry_name and line.account_credit_id)
            if not debit_lines or not credit_lines:
                raise ValidationError(
                    _('Please add both Credit and Debit accounts in the rules.'))
            debit_account_vals = {
                'account_id': debit_lines[0].account_debit_id.id,
                'debit': total_amount,
                'label': entry_name,
                'partner_id': payslip_ids[0].employee_id.user_partner_id.id,
                'account_move_id': account_move.id,
            }
            credit_account_vals = {
                'account_id': credit_lines[0].account_credit_id.id,
                'credit': total_amount,
                'label': entry_name,
                'partner_id': payslip_ids[0].employee_id.user_partner_id.id,
                'account_move_id': account_move.id,
            }
            debit_journal_item = self.env['account.journal.item'].create(debit_account_vals)
            credit_journal_item = self.env['account.journal.item'].create(credit_account_vals)
            journal_item_ids.append(fields.Command.link(debit_journal_item.id))
            journal_item_ids.append(fields.Command.link(credit_journal_item.id))
            line_vals = {
                'name': entry_name,
                'account_id': debit_account_vals['account_id'],
                'debit': total_amount,
                'credit': 0.0,
                'move_id': account_move.id,
                'batch_id': self.id
            }
            line_ids.append(fields.Command.create(line_vals))
            line_vals = {
                'name': entry_name,
                'account_id': credit_account_vals['account_id'],
                'debit': 0.0,
                'credit': total_amount,
                'move_id': account_move.id,
                'batch_id': self.id
            }
            line_ids.append(fields.Command.create(line_vals))

        account_move.line_ids = line_ids
        line_count = self.env['account.move.line'].sudo().search_count([('batch_id', '=', self.id)])
        self.journal_entry_count = line_count
        account_move.journal_item_ids = journal_item_ids
        payslip_ids.account_move_id = account_move.id
        payslip_ids.write({'state': 'done'})
        self.write({'state': 'done'})

    def action_paid(self):
        """To make payment for the payslips"""
        self.write({'state': 'paid'})
        for data in self.employee_payslip_ids:
            data.action_paid()

    def action_view_journal_entry(self):
        """To view corresponding journal entry"""
        return {
            'name': 'Journal Entry',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tree').id, 'list'], [False, 'form']],
            'context': {'search_default_group_by_move': 1},
            'type': 'ir.actions.act_window',
            'domain': [('batch_id', '=', self.id)],
        }
