# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class AccountReturnChecks(models.Model):
    _name = 'account.return.checks'
    _description = 'Validation Rule'
    _order = 'name'

    name = fields.Char(required=True)
    model_name = fields.Selection([
        ('account.move', 'Journal Entry'),
        ('account.move.line', 'Journal Item'),
        ('account.payment', 'Payment'),
        ('res.partner', 'Contact'),
    ], required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    # dynamic domain field
    domain = fields.Char(string="Condition", default="[]")

    @api.onchange('model_name')
    def _onchange_model_name(self):
        """Reset result when model changes"""
        pass


class AccountReturnValidation(models.Model):
    _name = 'account.return.validation'
    _description = 'Tax Return Validation'
    _order = 'template_id'

    name = fields.Char(related='template_id.name', string="Check Name", readonly=True)
    template_id = fields.Many2one('account.return.checks', string="Template", required=True, ondelete='cascade')
    return_id = fields.Many2one('account.return', string="Tax Return", required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='return_id.company_id', store=True)
    state = fields.Selection([('draft', 'Draft'),('passed', 'Passed'),('failed', 'Failed')], default='draft',
                             readonly=True)
    record_count = fields.Integer(string="Matched Records", readonly=True)
    result_message = fields.Text(string="Result", readonly=True)

    def _get_failing_records_domain(self):
        """Build the domain used to identify failing records"""
        self.ensure_one()
        template = self.template_id
        model_name = template.model_name
        active_domain = template.domain

        if not active_domain or active_domain == "[]":
            return []

        try:
            full_domain = safe_eval(active_domain)
            if not isinstance(full_domain, list):
                full_domain = []
        except Exception:
            full_domain = []

        # Add company filter if model has company_id
        if hasattr(self.env[model_name], 'company_id'):
            full_domain.append(('company_id', '=', self.company_id.id))

        # Add period filter
        if self.return_id.date_from and self.return_id.date_to:
            date_field = 'date'
            full_domain.extend([
                (date_field, '>=', self.return_id.date_from),
                (date_field, '<=', self.return_id.date_to)
            ])
        return full_domain

    def action_run_validation(self):
        """Execute validation rule based on template"""
        self.ensure_one()
        model_name = self.template_id.model_name
        full_domain = self._get_failing_records_domain()

        # Search records
        records = self.env[model_name].search(full_domain)
        count = len(records)

        # Update result
        self.record_count = count
        self.state = 'failed' if records else 'passed'
        self.result_message = f"Found {count} matching record(s)." if records else "No matching records found."

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Validation Completed'),
                'message': self.result_message,
                'sticky': False,
                'type': 'danger' if records else 'success',
            }
        }

    def action_view_failed_records(self):
        """Open a list view of the records that caused the validation failure"""
        self.ensure_one()
        model_name = self.template_id.model_name
        domain = self._get_failing_records_domain()

        return {
            'name': _('Failing Records: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': model_name,
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

    @api.onchange('model_name')
    def _onchange_model_name(self):
        """Reset result when model changes"""
        self.result_message = False