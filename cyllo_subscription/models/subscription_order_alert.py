# -*- coding: utf-8 -*-
from odoo import _, fields, models


class SubscriptionOrderAlert(models.Model):
    """Model to give alert based on condition"""
    _name = 'subscription.order.alert'
    _inherit = 'mail.thread'
    _description = 'Subscription Order Alert'

    name = fields.Char(help='Name of the alert', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company,
                                 help='Current logged company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', help='Current company currency')
    monthly_recurrence_min = fields.Monetary(string='Minimum MRR', help='Give the minimum MRR')
    monthly_recurrence_max = fields.Monetary(string='Maximum MRR', help='Give the maximum MRR')
    state_of_order = fields.Selection(selection=[('draft', 'Draft'), ('posted', 'Posted')], string='State',
                                      help='Choose which state order is need to show')
    subscription_plan_ids = fields.Many2many('sale.order.template', help='Choose a subscription plan',
                                             domain="[('is_subscription', '=', True)]")
    subscription_products_ids = fields.Many2many('product.template', string='Products',
                                                 help='Select products to applicable the rule',
                                                 domain="[('is_subscription', '=', True)]")
    partner_ids = fields.Many2many('res.partner', string='Customer', help='Choose the partners in the filed')
    action = fields.Selection(
        selection=[('create_next_activity', 'Create next activity'), ('set_to_renew', 'Set state to renew'),
                   ('send_mail', 'Send Mail to Customer')], help='Choose which action is to perform')
    order_count = fields.Integer(help='Count of subscription order', compute='_compute_order_count')
    activity_type_id = fields.Many2one('mail.activity.type', help='Choose the activity to perform')
    summary = fields.Char(help='Activity summary')
    note = fields.Html(help='Write note')
    dead_line = fields.Date(string='Deadline', help='Add dead line for the activity', default=fields.Date.today())
    email_template_id = fields.Many2one('mail.template', help='Choose the email template',
                                        domain=[('is_subscription_template', '=', True)])

    def action_show_subscription(self):
        """Return subscription order satisfies the trigger condition"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Order'),
            'res_model': 'subscription.order',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', self.env['subscription.order'].search(self.filter_records()).ids)]
        }

    def _compute_order_count(self):
        """Compute the total orders that satisfy trigger condition"""
        for record in self:
            record.order_count = self.env['subscription.order'].search_count(self.filter_records())

    def filter_records(self):
        """Domain to filter the records"""
        domain = []
        if self.monthly_recurrence_min:
            domain += [('recurring_revenue', '>=', self.monthly_recurrence_min)]
        if self.monthly_recurrence_max:
            domain += [('recurring_revenue', '<=', self.monthly_recurrence_max)]
        if self.subscription_plan_ids:
            domain += [('sale_order_template_id', 'in', self.subscription_plan_ids.ids)]
        if self.state_of_order:
            domain += [('state', '=', self.state_of_order)]
        if self.subscription_products_ids:
            domain += [('subscription_order_line_ids.product_tmpl_id.id', 'in', self.subscription_products_ids.ids)]
        if self.partner_ids:
            domain += [('partner_id', 'in', self.partner_ids.ids)]
        return domain

    def action_trigger(self):
        """Methode to run the trigger manually"""
        for record in self.env['subscription.order'].search(self.filter_records()):
            if self.action == 'set_to_renew':
                record.state_subscription = 'renew'
            elif self.action == 'create_next_activity':
                record.env['mail.activity'].create({
                    'summary': self.summary,
                    'activity_type_id': self.activity_type_id.id,
                    'note': self.note,
                    'date_deadline': self.dead_line,
                    'res_model_id': self.env['ir.model']._get_id('subscription.order'),
                    'res_id': record.id})
            elif self.action == 'send_mail':
                template = self.env['mail.template'].browse(
                    self.email_template_id.id)
                related_record = self.env['subscription.order'].browse(record.id)
                template.send_mail(template.id, force_send=True, email_values={
                    'email_to': related_record.partner_id.email,
                    'partner_ids': [related_record.partner_id.id],
                })
