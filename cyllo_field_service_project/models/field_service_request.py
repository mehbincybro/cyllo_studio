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
from datetime import date

from odoo import api, fields, models


class FieldServiceRequest(models.Model):
    """
    In this class we are defining the additional fields required for the model
        field.service.request.
            """
    _inherit = 'field.service.request'

    task_id = fields.Many2one('project.task', readonly=True,
                              help="Task which related to this request",copy=False)
    project_id = fields.Many2one('project.project',
                                 related="task_id.project_id",
                                 help="Project of the request")
    timesheet_ids = fields.One2many(related='task_id.timesheet_ids',
                                    readonly=False)
    workers_ids = fields.Many2many('hr.employee',
                                   compute='compute_workers_ids')
    is_invoiced = fields.Boolean(default=False)

    @api.depends('field_service_worker_ids.employee_id')
    def compute_workers_ids(self):
        """Get employee id's from workers record"""
        self.workers_ids = False
        for rec in self:
            rec.workers_ids = rec.field_service_worker_ids.employee_id.ids

    def action_assign_workers(self):
        """Override method to create project and task for field service"""
        res = super(FieldServiceRequest, self).action_assign_workers()
        if not res:
            employee_ids = self.field_service_worker_ids.mapped('employee_id').ids
            task_id = self.env['project.task'].create({
                'name': self.name,
                'project_id': self.env.ref(
                    'cyllo_field_service_project.project_project_field_service').id,
                'partner_id': self.partner_id.id,
                'date_assign': date.today(),
                'employee_ids': employee_ids,
                'company_id': self.company_id.id,
            })
            self.sudo().write({
                'task_id': task_id.id,
            })
        return res

    def action_create_invoices(self, type, total_amount = None):
        """Method to create invoice individually for service, timesheet or both for a service request"""
        if type == 'service_timesheet' and (total_amount and total_amount == 0) and \
            sum(self.service_checklist_ids.filtered(lambda s: s.status == 'completed').mapped('service_cost')) == 0:
            return False
        if type == 'service' and sum(self.service_checklist_ids.filtered(lambda s: s.status == 'completed').mapped('service_cost')) == 0:
            return False
        if type == 'timesheet' and total_amount == 0:
            return False
        sale_order_line_obj = self.env['sale.order.line']
        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.company_id.currency_id.id,
            'invoice_date': date.today(),
            'invoice_origin': self.name,
        }])
        self.write({
            'move_ids': [fields.Command.link(invoice.id)]
        })
        if type in ['service', 'service_timesheet']:
            for checklist in self.service_checklist_ids.filtered(lambda s: s.status == 'completed'):
                self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'product_id': checklist.product_id.id,
                    'price_unit': checklist.service_cost,
                })
        if type in ['timesheet', 'service_timesheet'] and total_amount != 0:
            field_service_product = self.env.ref('cyllo_field_service.product_product_field_service_timesheet')
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': field_service_product.id,
                'price_unit': total_amount,
            })
        if self.sale_order_id and invoice:
            for line in invoice.invoice_line_ids:
                order_line = sale_order_line_obj.create({
                        'order_id': self.sale_order_id.id,
                        'product_id': line.product_id.id,
                        'product_uom_qty': 1,
                        'qty_delivered': 1,
                        'price_unit': line.price_unit,
                        'tax_id': [fields.Command.link(tax.id) for tax in line.tax_ids]
                    })
                line.write({
                    'sale_line_ids': [fields.Command.link(order_line.id)]
                })
            self.sale_order_id.write({
                'invoice_ids': [fields.Command.link(invoice.id)]
            })
        self.is_invoiced = True
        return invoice


    def action_create_invoice(self):
        """
        Method to either create invoice for services or open wizard to configure invoicing if task is created
        Returns:
            dict: Action to open the created invoice in a new window or invoice configuration wizard.
        """
        if self.task_id:
            timesheets = []
            timesheet_ids = self.task_id.timesheet_ids
            for timesheet in timesheet_ids:
                timesheets.append(
                    fields.Command.create({
                        'employee_id': timesheet.employee_id.id,
                        'hours':timesheet.unit_amount,
                        'description':timesheet.name,
                        'date': timesheet.date
                    }))
            invoice_wizard = self.env['field.service.invoice'].create({
                'invoice_service': True if self.service_checklist_ids else False,
                'invoice_timesheet': True if self.timesheet_ids else False,
                'timesheet_ids': timesheets,
            })
            if invoice_wizard:
                return {
                    'name': 'Invoice Method',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'field.service.invoice',
                    'res_id': invoice_wizard.id,
                    'target': 'new'
                }
        else:
            invoice = self.action_create_invoices('service')
            if invoice:
                return {
                    'name': 'create_invoice',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'target': 'current'
                }
