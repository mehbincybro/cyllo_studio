# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import api, fields, models


class ResPartner(models.Model):
    """Inherit res.partner"""
    _inherit = 'res.partner'

    move_ids = fields.One2many('account.move', 'partner_id', string="Invoice Details",
                               readonly=True, domain=([('payment_state', '!=', 'paid'), ('state', '=', 'posted'),
                                                       ('invoice_date_due', '<', date.today())]))
    done_customer_followup_id = fields.Many2one('account.followup.line', string='Action Taken')
    to_do_customer_followup_id = fields.Many2one('account.followup.line',
                                                 compute='_compute_to_do_customer_followup_id',
                                                 string='Next Action', store=True)
    next_followup_action_date = fields.Char(string='Next Action Date')

    @api.depends('move_ids', 'done_customer_followup_id')
    def _compute_to_do_customer_followup_id(self):
        """Find next followup action"""
        for rec in self:
            rec.to_do_customer_followup_id = False
            line_obj = self.env['account.followup.line']
            followup_to_do = line_obj.search(
                [('delay', '>', rec.done_customer_followup_id.delay)],
                order='delay asc', limit=1) if rec.done_customer_followup_id else line_obj.search(
                [], order='delay asc', limit=1)
            rec.to_do_customer_followup_id = followup_to_do if followup_to_do else False

    def get_min_date(self):
        """For getting minimum date from the invoices"""
        for rec in self.filtered(lambda x: x.move_ids):
            return min(rec.move_ids.mapped('invoice_date_due'))

    def _execute_followup(self):
        """Execute this function-based cron job"""
        lines = self.env['account.followup.line'].search([])
        if lines:
            for partner in self.env['res.partner'].search([(
                    'move_ids', '!=', False)]):
                if partner.move_ids:
                    if not partner.to_do_customer_followup_id and partner.done_customer_followup_id:
                        continue
                    elif partner.to_do_customer_followup_id:
                        partner.send_invoice_mail(lines)
                else:
                    partner.next_followup_action_date = False
                    partner.done_customer_followup_id = False

    def send_invoice_mail(self, lines):
        """Send followup mails to the corresponding partners"""
        partner = self
        min_date = partner.get_min_date() + timedelta(
            days=partner.to_do_customer_followup_id.delay)
        date_min = str(min_date).split()[0]
        if str(date.today()) >= str(date_min):
            delay_list = lines.mapped('delay')
            partner.done_customer_followup_id = partner.to_do_customer_followup_id
            if len(delay_list) > delay_list.index(partner.done_customer_followup_id.delay) + 1:
                date_min = partner.get_min_date() + timedelta(
                    days=partner.to_do_customer_followup_id.delay)
                partner.next_followup_action_date = str(date_min).split()[0]
            else:
                partner.next_followup_action_date = False
            if partner.done_customer_followup_id.mail_template_id:
                partner.done_customer_followup_id.mail_template_id.send_mail(
                    partner.id)

    def action_send_followups(self):
        """Execute based on server action - Manually send mails from the
        partner form"""
        lines = self.env['account.followup.line'].search([])
        if lines:
            for partner in self:
                if partner.move_ids:
                    if not partner.to_do_customer_followup_id and partner.done_customer_followup_id:
                        continue
                    elif partner.to_do_customer_followup_id:
                        partner.send_invoice_mail(lines)
                else:
                    partner.next_followup_action_date = False
                    partner.done_customer_followup_id = False
