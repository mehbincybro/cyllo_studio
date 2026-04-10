# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
import random
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import email_split
from odoo.addons.web.controllers.utils import clean_action


class HelpDeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _description = "HelpDesk Ticket"
    _inherit = ['mail.activity.mixin', 'rating.mixin']

    ticket = fields.Char(string='Ticket Id', readonly=True,
                         default=lambda self: _('New'),
                         help="Helpdesk ticket Id")
    name = fields.Char(string="Name", help="Small description about the issue",
                       required=True)
    team_id = fields.Many2one('helpdesk.team', string="Team",
                              help="Helpdesk team", required=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'Low'), ('2', 'High'),
                                 ('3', 'Very High')], default='0',
                                string="Priority")
    customer_id = fields.Many2one('res.partner', string="Customer",
                                  help="Customer of the ticket")
    email = fields.Char(string="Email", help="Customer email id")
    phone = fields.Char(string="Phone", help="Customer phone number")
    category_id = fields.Many2one('helpdesk.category', string="Category",
                                  help="Ticket category")
    tag_id = fields.Many2one('helpdesk.tag', string="Tag",
                             help="Legacy single ticket tag")
    tag_ids = fields.Many2many('helpdesk.tag', string="Tags",
                               help="Ticket tags")
    user_id = fields.Many2one('res.users', string="Assigned to",
                              default=lambda self: self.env.user,
                              help="The person to whom the ticket assigned to")
    company_id = fields.Many2one('res.company', string="Company",
                                 required=True,
                                 default=lambda self: self.env.company,
                                 help="Company for the helpdesk ticket")
    invoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        help="Invoice linked to this ticket (filtered by the selected customer).",
    )
    invoice_line_ids = fields.Many2many(
        'account.move.line',
        string="Invoice line Items",
        help="Items belonging to the selected invoice.",
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        help="Sale Order linked to this ticket (filtered by the selected customer).",
    )
    description = fields.Html(string="Description",
                              help="Description about the issue or question")
    internal_notes = fields.Html(string="Internal Notes",
                                 help="Internal notes visible only to staff")
    timesheet_ids = fields.One2many('account.analytic.line', 'ticket_id',
                                    string="Timesheet",
                                    help="Time spent by the employee for this ticket")
    timesheet_bool = fields.Boolean(related='team_id.timesheet')
    use_field_service = fields.Boolean(related='team_id.use_field_service')
    sla_ids = fields.Many2many('helpdesk.sla', string="SLA policy",
                               help="SLA policy for this ticket")
    sla_flag = fields.Boolean(default=False,
                              help="To check SLA policy set or not")
    sla_failed = fields.Boolean(string="SLA failed ticket", default=False,
                                help="Ticket that failed SLA policy")
    sla_deadline = fields.Datetime(compute='_compute_sla_deadline',
                                   string="SLA Deadline", store=True)
    sla_reached_date = fields.Datetime(compute='_compute_sla_deadline',
                                       string="SLA Reached Date", store=True)
    activity_ids = fields.One2many('mail.activity', string="Activity")
    stage_id = fields.Many2one('helpdesk.stage', string="Status",
                               default=lambda self: self.env.ref(
                                   'cyllo_help_desk.new_ticket').id,
                               readonly=False, copy=False, tracking=True,
                               group_expand='_expand_states',
                               ondelete="restrict",
                               track_visibility='onchange',
                               help="Help desk stages")
    stage_name = fields.Char(related='stage_id.name')
    sequence = fields.Integer(related='stage_id.sequence', string="Sequence",
                              help="Stage sequence number")
    date = fields.Datetime(default=fields.Datetime.now)
    closed_date = fields.Datetime()
    sla_status_ids = fields.One2many('sla.status', 'ticket_id',
                                     string="SLA Status",
                                     help="Status of helpdesk ticket")
    last_seven_days = fields.Datetime(compute="_compute_last_seven_days")
    open_ticket_average_hours = fields.Float(string="Open Hours",
                                             compute="_compute_average_open_hours",
                                             store=True)
    high_priority_ticket_average_hours = fields.Float(
        string="High Priority Open Hours",
        compute="_compute_high_priority_average_open_hours", store=True)
    urgent_ticket_average_hours = fields.Float(
        string="Urgent Ticket Open Hours",
        compute="_compute_urgent_ticket_average_open_hours", store=True)
    is_closed_today = fields.Boolean(string='Closed Today',
                                     compute='_compute_is_closed_today')
    sla_status_label = fields.Char(compute='_compute_sla_status_label',
                                   string="SLA Status")

    def _compute_sla_status_label(self):
        for ticket in self:
            ticket.sla_status_label = _(
                "Failed") if ticket.sla_failed else False

    # Parent-Child Linking
    parent_id = fields.Many2one('helpdesk.ticket', string='Parent Ticket',
                                help='Reference to the main ticket')
    child_ids = fields.One2many('helpdesk.ticket', 'parent_id',
                                string='Sub-tickets')
    source = fields.Selection([
        ('manual', 'Manual'),
        ('website', 'Website'),
        ('livechat', 'Livechat'),
        ('email', 'Email'),
    ], string='Source', default='manual', help='The source from which the ticket was created.')

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise UserError(
                _('Error! You cannot create recursive ticket dependencies.'))
    # Dependencies
    dependency_ids = fields.Many2many('helpdesk.ticket',
                                      'helpdesk_ticket_dependency_rel',
                                      'ticket_id', 'dependency_id',
                                      string='Dependencies')
    # Skills and Assignment
    skill_ids = fields.Many2many('hr.skill', string='Required Skills')
    team_member_ids = fields.Many2many('res.users',
                                       related='team_id.member_ids')
    # SLA Pause
    sla_paused = fields.Boolean(string='SLA Paused', default=False)
    sla_pause_date = fields.Datetime()
    sla_progress = fields.Float(string='SLA Progress',
                                compute='_compute_sla_progress',
                                help="Progress towards the next SLA deadline")
    use_sla = fields.Boolean(related='team_id.use_sla', string="Use SLA")
    use_credit_notes = fields.Boolean(related='team_id.use_credit_notes', string="Use Credit Notes")
    use_coupons = fields.Boolean(related='team_id.use_coupons', string="Use Coupons")
    use_returns = fields.Boolean(related='team_id.use_returns', string="Use Returns")
    use_replacements = fields.Boolean(related='team_id.use_replacements', string="Use Replacements")
    use_repairs = fields.Boolean(related='team_id.use_repairs', string="Use Repairs")
    use_timesheet = fields.Boolean(related='team_id.use_timesheet', string="Use Timesheets")
    use_sale_order = fields.Boolean(related='team_id.use_sale_order',
                                    string="Use Sale Order")
    # Integrations
    sale_order_ids = fields.One2many('sale.order', 'helpdesk_ticket_id',
                                     string='Sales Orders')
    repair_ids = fields.One2many('repair.order', 'helpdesk_ticket_id',
                                 string='Repair Orders')
    task_ids = fields.One2many('project.task', 'helpdesk_ticket_id',
                               string='Field Service Tasks')
    crm_lead_ids = fields.One2many('crm.lead', 'helpdesk_ticket_id',
                                   string='CRM Leads')
    refund_ids = fields.One2many('account.move', 'helpdesk_ticket_id',
                                 string='Refund/Credit Notes')
    coupon_ids = fields.Many2many('loyalty.card', string='Coupons')
    picking_ids = fields.Many2many('stock.picking',
                                   string='Returns/Replacements')
    field_service_request_ids = fields.One2many('field.service.request',
                                                'helpdesk_ticket_id',
                                                string='Field Service Requests')
    sale_order_count = fields.Integer(compute='_compute_integration_counts')
    refund_count = fields.Integer(compute='_compute_integration_counts')
    task_count = fields.Integer(compute='_compute_integration_counts')
    repair_count = fields.Integer(compute='_compute_integration_counts')
    crm_lead_count = fields.Integer(compute='_compute_integration_counts')
    coupon_count = fields.Integer(compute='_compute_integration_counts')
    picking_count = fields.Integer(compute='_compute_integration_counts')
    field_service_request_count = fields.Integer(
        compute='_compute_integration_counts')
    customer_sale_order_count = fields.Integer(
        compute='_compute_customer_record_counts')
    customer_purchase_order_count = fields.Integer(
        compute='_compute_customer_record_counts')
    customer_invoice_count = fields.Integer(
        compute='_compute_customer_record_counts')
    customer_subscription_count = fields.Integer(
        compute='_compute_customer_record_counts')
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string="Sale Order Line",
        help="Sale Order Line linked to this ticket (filtered by the selected sale order).",
    )
    use_product_warranty = fields.Boolean(related='team_id.use_product_warranty', string="Use Product Warranty")
    warranty_status = fields.Selection([
        ('under_warranty', 'Under Warranty'),
        ('expired', 'Warranty Expired'),
        ('none', 'No Warranty')
    ], compute='_compute_warranty_status', string="Warranty Status Evaluation")

    @api.depends('sale_order_line_id', 'use_product_warranty')
    def _compute_warranty_status(self):
        today = fields.Date.today()
        for ticket in self:
            if not ticket.use_product_warranty or not ticket.sale_order_line_id:
                # ticket.warranty_status_label = False
                ticket.warranty_status = False
                continue
            expiration_date = ticket.sale_order_line_id.warranty_expiration_date
            if not expiration_date:
                ticket.warranty_status = 'none'
            elif expiration_date > today:
                ticket.warranty_status = 'under_warranty'
            else:
                ticket.warranty_status = 'expired'
    # Portal
    website_published = fields.Boolean(string='Visible in Portal', default=True)
    # Duplicate Detection
    duplicate_ticket_ids = fields.Many2many('helpdesk.ticket',
                                            compute='_compute_duplicate_tickets',
                                            string='Duplicate Tickets')
    has_duplicates = fields.Boolean(compute='_compute_duplicate_tickets',
                                    string='Has Duplicates')
    # Canned Response
    canned_response_ids = fields.Many2many('mail.shortcode',
                                           string='Canned Response')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',
                                      help='Attach files to this ticket')

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        stage_one = self.env.ref('cyllo_help_desk.new_ticket')
        if self._origin.stage_id and self._origin.stage_id != stage_one and self.stage_id == stage_one:
            raise UserError('Cannot go back')

        # Dependency Check
        if self.stage_id.is_closed:
            unresolved_deps = self.dependency_ids.filtered(
                lambda t: not t.stage_id.is_closed)
            if unresolved_deps:
                raise UserError(
                    _("Cannot close ticket until dependencies are resolved: %s") % (
                        ", ".join(unresolved_deps.mapped('ticket'))))

    @api.onchange('team_id', 'skill_ids')
    def _onchange_team_id_assignment(self):
        """Handle automated assignment when the team or skills are changed."""
        if not self.team_id:
            return

        method = self.team_id.assignment_method
        members = self.team_id.member_ids

        if method == 'manual':
            self.user_id = False
        elif method == 'random' and members:
            self.user_id = random.choice(members.ids)
        elif method == 'round_robin' and members:
            # Load-balanced assignment: find member with least open tickets
            ticket_counts = {}
            for member in members:
                count = self.env['helpdesk.ticket'].search_count([
                    ('user_id', '=', member.id),
                    ('stage_id.is_closed', '=', False)
                ])
                ticket_counts[member] = count
            if ticket_counts:
                best_member = min(ticket_counts, key=ticket_counts.get)
                self.user_id = best_member.id
        elif method == 'skill' and members:
            # Unified Best Match assignment (HR Skills)
            required_skill_ids = self.skill_ids.ids
            # Fetch employees for all team members
            employees = self.env['hr.employee'].search([
                ('user_id', 'in', members.ids)
            ])
            member_data = []
            for emp in employees:
                emp_skill_ids = emp.employee_skill_ids.mapped('skill_id.id')
                # Intersection of IDs
                match_count = len(set(emp_skill_ids) & set(required_skill_ids))

                # We always consider team members for load balancing, 
                # but if skill matching is preferred, we prioritize those with matches.
                ticket_count = self.env['helpdesk.ticket'].search_count([
                    ('user_id', '=', emp.user_id.id),
                    ('stage_id.is_closed', '=', False)
                ])
                member_data.append({
                    'user_id': emp.user_id.id,
                    'matches': match_count,
                    'tickets': ticket_count
                })
            if member_data:
                # Primary: Most matches | Secondary: Least tickets
                best_candidates = sorted(member_data,
                                         key=lambda x: (-x['matches'],
                                                        x['tickets']))
                self.user_id = best_candidates[0]['user_id']

    @api.onchange('customer_id')
    def _onchange_customer_id_clear_invoice(self):
        """Keep the selected Invoice and Sale Order consistent with the chosen customer."""
        invoice_domain = [('id', '=', False)]
        so_domain = [('id', '=', False)]
        if self.customer_id:
            commercial = self.customer_id.commercial_partner_id
            invoice_domain = [
                ('move_type', '=', 'out_invoice'),
                ('partner_id', 'child_of', commercial.id),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('paid', 'in_payment')),
            ]
            so_domain = [
                ('partner_id', 'child_of', commercial.id),
                ('state', 'in', ['sale', 'done']),
            ]
            if self.invoice_id and self.invoice_id.partner_id.commercial_partner_id != commercial:
                self.invoice_id = False
                self.invoice_line_ids = [(5, 0, 0)]
            if self.sale_order_id and self.sale_order_id.partner_id.commercial_partner_id != commercial:
                self.sale_order_id = False
        else:
            self.invoice_id = False
            self.invoice_line_ids = [(5, 0, 0)]
            self.sale_order_id = False
        return {'domain': {
            'invoice_id': invoice_domain,
            'sale_order_id': so_domain,
        }}

    @api.onchange('invoice_id')
    def _onchange_invoice_id_clear_items(self):
        """Clear invoice items when the invoice is changed."""
        self.invoice_line_ids = [(5, 0, 0)]

    @api.depends('create_date', 'sla_ids', 'stage_id', 'sla_paused')
    def _compute_sla_progress(self):
        for ticket in self:
            if not ticket.sla_ids or not ticket.create_date or ticket.stage_id.is_closed:
                ticket.sla_progress = 0
                continue
            # Simple linear progress estimate based on earliest deadline
            statuses = ticket.sla_status_ids.filtered(
                lambda s: s.state == 'ongoing')
            if not statuses:
                ticket.sla_progress = 100 if ticket.sla_failed else 0
                continue
            earliest_status = min(statuses, key=lambda
                s: s.deadline or fields.Datetime.now())
            if not earliest_status.deadline:
                ticket.sla_progress = 0
                continue
            elapsed_raw = (
                                      fields.Datetime.now() - ticket.create_date).total_seconds() / 3600.0
            excluded_hours = ticket._get_excluded_duration(
                earliest_status.sla_id)
            effective_elapsed = max(elapsed_raw - excluded_hours, 0)
            progress = (effective_elapsed / (
                        earliest_status.sla_id.within_hour or 1)) * 100
            ticket.sla_progress = min(max(progress, 0), 100)

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime',
                 'sla_status_ids.state')
    def _compute_sla_deadline(self):
        for ticket in self:
            ongoing = ticket.sla_status_ids.filtered(
                lambda s: s.state == 'ongoing')
            ticket.sla_deadline = min(
                ongoing.mapped('deadline')) if ongoing else False
            reached = ticket.sla_status_ids.filtered(
                lambda s: s.state == 'pass' and s.reached_datetime)
            ticket.sla_reached_date = max(
                reached.mapped('reached_datetime')) if reached else False

    @api.depends('name', 'customer_id', 'description', 'create_date',
                 'category_id', 'canned_response_ids')
    def _compute_duplicate_tickets(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.duplicate_ticket_ids = [(5, 0, 0)]
                ticket.has_duplicates = False
                continue
            # Mandatory criteria: Same customer and Same day
            ticket_date = (ticket.create_date or fields.Datetime.now()).date()
            date_start = datetime.combine(ticket_date, datetime.min.time())
            date_end = datetime.combine(ticket_date, datetime.max.time())
            domain = [
                ('customer_id', '=', ticket.customer_id.id),
                ('create_date', '>=', date_start),
                ('create_date', '<=', date_end),
                ('stage_id.is_closed', '=', False),
            ]
            if ticket.id:
                domain.append(('id', '!=', ticket._origin.id))
            potential_matches = self.search(domain)
            duplicate_ids = []
            for match in potential_matches:
                score = 0
                if ticket.name and match.name == ticket.name:
                    score += 1
                if ticket.category_id and match.category_id == ticket.category_id:
                    score += 1
                if ticket.description and match.description == ticket.description:
                    score += 1
                # Comparing many2many field (only if not empty)
                if ticket.canned_response_ids and set(
                        match.canned_response_ids.ids) == set(
                        ticket.canned_response_ids.ids):
                    score += 1
                if score >= 2:
                    duplicate_ids.append(match.id)
            ticket.duplicate_ticket_ids = [(6, 0, duplicate_ids)]
            ticket.has_duplicates = bool(duplicate_ids)

    @api.depends('sale_order_ids', 'refund_ids', 'task_ids', 'repair_ids',
                 'crm_lead_ids', 'coupon_ids', 'picking_ids',
                 'field_service_request_ids')
    def _compute_integration_counts(self):
        for ticket in self:
            ticket.sale_order_count = len(ticket.sale_order_ids)
            ticket.refund_count = len(ticket.refund_ids.filtered(
                lambda move: move.move_type == 'out_refund'))
            ticket.task_count = len(ticket.task_ids)
            ticket.repair_count = len(ticket.repair_ids)
            ticket.crm_lead_count = len(ticket.crm_lead_ids)
            ticket.coupon_count = len(ticket.coupon_ids)
            ticket.picking_count = len(ticket.picking_ids)
            ticket.field_service_request_count = len(
                ticket.field_service_request_ids)

    @api.depends('customer_id')
    def _compute_customer_record_counts(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.customer_sale_order_count = 0
                ticket.customer_purchase_order_count = 0
                ticket.customer_invoice_count = 0
                ticket.customer_subscription_count = 0
                continue
            commercial_partner = ticket.customer_id.commercial_partner_id
            domain = [('partner_id', 'child_of', commercial_partner.id)]
            ticket.customer_sale_order_count = self.env[
                'sale.order'].search_count(domain)
            ticket.customer_purchase_order_count = self.env[
                'purchase.order'].search_count(domain)
            ticket.customer_invoice_count = self.env[
                'account.move'].search_count(
                domain + [('move_type', 'in', ('out_invoice', 'out_refund'))])
            ticket.customer_subscription_count = self.env[
                'subscription.order'].search_count(domain)

    def action_view_customer_sale_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_orders")
        action['domain'] = [('partner_id', 'child_of',
                             self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        action['view_mode'] = 'tree'
        action['views'] = [
            (self.env.ref('sale.view_quotation_tree').id, 'tree')]
        return action

    def action_view_customer_purchase_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase.purchase_form_action")
        action['domain'] = [('partner_id', 'child_of',
                             self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        action['view_mode'] = 'tree'
        action['views'] = [
            (self.env.ref('purchase.purchase_order_view_tree').id, 'tree')]
        return action

    def action_view_customer_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type")
        action['domain'] = [
            ('partner_id', 'child_of',
             self.customer_id.commercial_partner_id.id),
            ('move_type', 'in', ('out_invoice', 'out_refund'))
        ]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        action['view_mode'] = 'tree'
        action['views'] = [
            (self.env.ref('account.view_out_invoice_tree').id, 'tree')]
        return action

    def action_view_customer_subscriptions(self):
        self.ensure_one()
        # Assuming the action exists in cyllo_subscription
        try:
            action = self.env["ir.actions.actions"]._for_xml_id(
                "cyllo_subscription.subscription_order_action")
        except ValueError:
            # Fallback if the XML ID is different
            action = {
                'type': 'ir.actions.act_window',
                'name': _('Subscriptions'),
                'res_model': 'subscription.order',
                'view_mode': 'tree',
                'target': 'current',
            }
        action['domain'] = [('partner_id', 'child_of',
                             self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        action['view_mode'] = 'tree'
        # Try to find a tree view for subscription.order
        subscription_tree = self.env.ref(
            'cyllo_subscription.subscription_order_view_tree',
            raise_if_not_found=False)
        if subscription_tree:
            action['views'] = [(subscription_tree.id, 'tree')]
        else:
            action['views'] = [(False, 'tree')]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        """ Sequence for helpdesk tickets and stage history """
        for vals in vals_list:
            if vals.get('ticket', _('New')) == _('New'):
                vals['ticket'] = self.env['ir.sequence'].next_by_code(
                    'helpdesk.ticket') or 'New'
        res = super(HelpDeskTicket, self).create(vals_list)
        for ticket in res:
            ticket._assign_ticket()
            # Automatically apply SLA policies on creation if not manually specified
            if not ticket.sla_ids and ticket.team_id.use_sla:
                sla_policies = ticket._get_sla_policies()
                if sla_policies:
                    ticket.sla_ids = [(6, 0, sla_policies.ids)]
                    ticket.sla_flag = True
            # Trigger status sync and deadline calculation
            ticket._update_sla_statuses()
            if ticket.stage_id:
                self.env['helpdesk.stage.history'].create({
                    'ticket_id': ticket.id,
                    'stage_id': ticket.stage_id.id,
                    'start_date': fields.Datetime.now(),
                })

            # Auto-response for email-created tickets
            if ticket.source == 'email' and ticket.team_id.use_confirmation_email:
                mail_template = self.env.ref('cyllo_help_desk.help_desk_mail_template', raise_if_not_found=False)
                if mail_template:
                    mail_template.sudo().send_mail(ticket.id, force_send=True)
                    ticket.message_post(body=_("Automated confirmation email sent to %s", ticket.customer_id.name or ticket.email))
        return res


    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overriding to set custom values when creating a ticket from an email. """
        if custom_values is None:
            custom_values = {}
        email_from = msg_dict.get('from')
        if email_from:
            custom_values['email'] = email_from
        # Search for partner by email if not provided
        if not custom_values.get('customer_id') and email_from:
            email_list = email_split(email_from)
            if email_list:
                cleaned_email = email_list[0]
                partner = self.env['res.partner'].search(
                    [('email', '=', cleaned_email)], limit=1)
                if partner:
                    custom_values['customer_id'] = partner.id
        custom_values.update({
            'name': msg_dict.get('subject', _('No Subject')),
            'description': msg_dict.get('body', ''),
            'source': 'email',
        })
        return super().message_new(msg_dict, custom_values=custom_values)

    def message_post(self, **kwargs):
        """ Link attachments from incoming messages to the ticket's attachment_ids field. """
        message = super(HelpDeskTicket, self).message_post(**kwargs)
        if message.attachment_ids:
            self.attachment_ids = [(4, att.id) for att in
                                   message.attachment_ids]
        return message

    def _assign_ticket(self):
        self.ensure_one()
        if self.user_id or not self.team_id or self.team_id.assignment_method == 'manual':
            return
        team = self.team_id
        if team.assignment_method == 'random':
            members = self.env['res.users'].search([('groups_id', 'in',
                                                     self.env.ref(
                                                         'cyllo_help_desk.cyllo_help_desk_user').id)])
            if members:
                import random
                self.user_id = random.choice(members.ids)
        elif team.assignment_method == 'skill' and self.skill_ids:
            # Consistent Best Match logic for background assignment
            required_skill_ids = self.skill_ids.ids
            employees = self.env['hr.employee'].search([
                ('user_id', 'in', team.member_ids.ids)
            ])
            member_data = []
            for emp in employees:
                emp_skill_ids = emp.employee_skill_ids.mapped('skill_id.id')
                match_count = len(set(emp_skill_ids) & set(required_skill_ids))
                ticket_count = self.env['helpdesk.ticket'].search_count([
                    ('user_id', '=', emp.user_id.id),
                    ('stage_id.is_closed', '=', False)
                ])
                member_data.append({
                    'user_id': emp.user_id.id,
                    'matches': match_count,
                    'tickets': ticket_count
                })
            if member_data:
                best_candidates = sorted(member_data,
                                         key=lambda x: (-x['matches'],
                                                        x['tickets']))
                self.user_id = best_candidates[0]['user_id']
        elif team.assignment_method == 'round_robin':
            members = self.env['res.users'].search([
                ('groups_id', 'in',
                 self.env.ref('cyllo_help_desk.cyllo_help_desk_user').id)
            ], order='id')
            if members:
                last_user = team.last_assigned_user_id
                next_user = members[0]
                if last_user and last_user in members:
                    index = list(members).index(last_user)
                    if index < len(members) - 1:
                        next_user = members[index + 1]

                self.user_id = next_user.id
                team.last_assigned_user_id = next_user.id

    @api.onchange('customer_id', 'team_id')
    def _onchange_customer_id(self):
        if self.team_id and self.team_id.use_sla:
            sla_policies = self._get_sla_policies()
            if sla_policies:
                self.sla_flag = True
                self.sla_ids = [(6, 0, sla_policies.ids)]
            else:
                self.sla_flag = False
                self.sla_ids = [(5,)]
        else:
            self.sla_flag = False
            self.sla_ids = [(5,)]

    def _get_sla_policies(self):
        """ Return SLA policies matching the current ticket criteria """
        self.ensure_one()
        if not self.team_id:
            return self.env['helpdesk.sla']

        domain = [('team_id', '=', self.team_id.id)]
        if self.customer_id:
            domain += ['|', ('customer_ids', '=', False),
                       ('customer_ids', 'in', [self.customer_id.id])]
        else:
            domain += [('customer_ids', '=', False)]

        return self.env['helpdesk.sla'].search(domain)

    @api.onchange('tag_id')
    def _onchange_tag_id(self):
        for ticket in self:
            if ticket.tag_id and ticket.tag_id not in ticket.tag_ids:
                ticket.tag_ids = [(4, ticket.tag_id.id)]

    def _expand_states(self, states, domain, order):
        return self.env['helpdesk.stage'].search([])

    def write(self, vals):
        if 'stage_id' in vals:
            for ticket in self:
                if ticket.stage_id.id != vals['stage_id']:
                    # Close current history
                    last_history = self.env['helpdesk.stage.history'].search([
                        ('ticket_id', '=', ticket.id),
                        ('end_date', '=', False)
                    ], limit=1)
                    if last_history:
                        last_history.end_date = fields.Datetime.now()
                    # Create new history
                    self.env['helpdesk.stage.history'].create({
                        'ticket_id': ticket.id,
                        'stage_id': vals['stage_id'],
                        'start_date': fields.Datetime.now()
                    })
        result = super(HelpDeskTicket, self).write(vals)
        in_progress_stage = self.env.ref(
            'cyllo_help_desk.in_progress_ticket').id
        solved_stage = self.env.ref('cyllo_help_desk.solved_ticket').id
        mail_template = self.env.ref('cyllo_help_desk.help_desk_mail_template',
                                     raise_if_not_found=False)
        solved_mail_template = self.env.ref(
            'cyllo_help_desk.help_desk_mail_template_issue_solved',
            raise_if_not_found=False)
        if 'stage_id' in vals:
            for ticket in self:
                # Filter children to only those that actually need a stage update
                # to prevent recursion and redundant writes.
                children_to_update = ticket.child_ids.filtered(
                    lambda t: t.stage_id.id != vals['stage_id'])
                if children_to_update:
                    children_to_update.write({'stage_id': vals['stage_id']})
                # Check stages for email notifications
                if ticket.stage_id.id == in_progress_stage and mail_template:
                    mail_template['email_from'] = ticket.user_id.login
                    mail_template['email_to'] = ticket.customer_id.email
                    mail_template.sudo().send_mail(
                        ticket._origin.id or ticket.id, force_send=True)
                    body = f"""Email sent to {ticket.customer_id.name}"""
                    ticket.message_post(body=body, subject="TICKET CREATED")
                elif ticket.stage_id.id == solved_stage and solved_mail_template:
                    solved_mail_template['email_from'] = ticket.user_id.login
                    solved_mail_template['email_to'] = ticket.customer_id.email
                    solved_mail_template.sudo().send_mail(
                        ticket._origin.id or ticket.id, force_send=True)
                    body = f"""Work done mail sent to {ticket.customer_id.name}"""
                    ticket.message_post(body=body, subject="ISSUE SOLVED")
        # SLA Status Sync and Reach Logic
        if 'sla_ids' in vals:
            self._update_sla_statuses()
        if 'stage_id' in vals:
            for ticket in self:
                for status in ticket.sla_status_ids.filtered(
                        lambda s: s.state == 'ongoing'):
                    if ticket.stage_id.sequence >= status.sla_id.target_stage.sequence:
                        status.reached_datetime = fields.Datetime.now()
                        status.state = 'pass' if status.reached_datetime <= status.deadline else 'fail'
                        if status.state == 'fail':
                            ticket.sla_failed = True
        return result

    def _update_sla_statuses(self):
        """ Ensure every SLA policy on the ticket has a status record """
        for ticket in self:
            if not ticket.create_date:
                continue
            for sla in ticket.sla_ids:
                existing = ticket.sla_status_ids.filtered(
                    lambda s: s.sla_id == sla)
                if not existing:
                    work_hours = ticket.team_id.working_hour_id or ticket.company_id.resource_calendar_id
                    status = self.env['sla.status'].create({
                        'ticket_id': ticket.id,
                        'sla_id': sla.id,
                        'state': 'ongoing',
                    })
                    # Calculate deadline immediately
                    if work_hours:
                        excluded_hours = ticket._get_excluded_duration(sla)
                        deadline_in_hours = sla.within_hour + excluded_hours
                        status.deadline = work_hours.plan_hours(
                            deadline_in_hours,
                            ticket.create_date,
                            compute_leaves=True
                        )

    @api.model
    def get_overview(self):
        """ Function to calculate all values for the overview"""
        # Declaring a dictionary that contain all the values
        result = {
            'all_tickets': 0,
            'high_priority': 0,
            'urgent': 0,
            'average_open_hour': 0,
            'high_priority_average_open_hour': 0,
            'urgent_average_open_hour': 0,
            'failed_ticket_count': 0,
            'failed_high_priority_ticket_count': 0,
            'failed_urgent_ticket_count': 0,
            'my_today_closed_ticket_count': 0,
            'my_success_rate_ticket_count': 0,
            'my_average_rating': 0,
            'my_last_seven_days_closed_ticket_count': 0,
            'my_last_seven_days_success_rate': 0,
            'my_last_seven_days_average_rating': 0,
        }
        # Taking the count of tickets in priority base (filtered by my open tickets)
        my_open_tickets = self.search([
            ('user_id', '=', self.env.user.id),
            ('stage_id.is_closed', '=', False)
        ])
        all_tickets = len(my_open_tickets)
        high_priority = len(
            my_open_tickets.filtered(lambda t: t.priority == '2'))
        urgent = len(my_open_tickets.filtered(lambda t: t.priority == '3'))

        # Calculating the actual average open hours of the tickets (age)
        def compute_avg_age(tickets):
            if not tickets:
                return 0
            now = datetime.now()
            total_hours = sum(
                (now - t.create_date).total_seconds() / 3600.0 for t in tickets
                if t.create_date)
            return total_hours / len(tickets)

        average_open_hour = compute_avg_age(my_open_tickets)
        high_priority_average_open_hour = compute_avg_age(
            my_open_tickets.filtered(lambda t: t.priority == '2'))
        urgent_average_open_hour = compute_avg_age(
            my_open_tickets.filtered(lambda t: t.priority == '3'))
        # Calculating the number of failed tickets of the current user
        failed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False), ('sla_failed', '=', True)])
        # Calculating the number of failed high priority tickets of the
        # current user
        failed_high_priority_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('sla_flag', '=', True), ('stage_id.is_closed', '=', False),
             ('priority', '=', '2'), ('sla_failed', '=', True)])

        # Calculating the number of failed urgent tickets of the current user
        failed_urgent_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('sla_flag', '=', True), ('stage_id.is_closed', '=', False),
             ('priority', '=', '3'), ('sla_failed', '=', True)])
        # Calculating count of tickets closed today of current user
        today = fields.date.today()
        my_today_closed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('closed_date', '>=',
              datetime.combine(today, datetime.min.time())),
             ('closed_date', '<=',
              datetime.combine(today, datetime.max.time())),
             ('stage_id.is_closed', '=', True)])
        # Calculating success rate of current user
        closed_ticket_count = self.search_count([
            ('closed_date', '>=', datetime.combine(today, datetime.min.time())),
            ('closed_date', '<=', datetime.combine(today, datetime.max.time())),
            ('user_id', '=', self.env.user.id)])
        passed_ticket_count = self.search_count([
            ('closed_date', '>=', datetime.combine(today, datetime.min.time())),
            ('closed_date', '<=', datetime.combine(today, datetime.max.time())),
            ('user_id', '=', self.env.user.id),
            ('sla_failed', '=', False)])
        if passed_ticket_count:
            my_success_rate_ticket_count = round(
                ((passed_ticket_count / closed_ticket_count) * 100), 2)
        else:
            my_success_rate_ticket_count = 0
        # Calculating average rating for current user
        my_average_rating = 0
        # Calculating count of closed tickets in last seven days of
        # current user
        one_week_back_date = datetime.now() - timedelta(days=6)
        my_last_seven_days_closed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('stage_id.is_closed', '=', True),
             ('closed_date', '>=', one_week_back_date),
             ])
        # Calculating success rate in last seven days of current user
        closed_ticket_count = self.search_count([
            ('closed_date', '>=', one_week_back_date),
            ('user_id', '=', self.env.user.id)])
        passed_ticket_count = self.search_count([
            ('closed_date', '>=', one_week_back_date),
            ('user_id', '=', self.env.user.id), ('sla_failed', '=', False)])
        if passed_ticket_count:
            my_last_seven_days_success_rate = round(
                ((passed_ticket_count / closed_ticket_count) * 100), 2)
        else:
            my_last_seven_days_success_rate = 0
        # Calculating last seven days average rating of current user
        my_last_seven_days_average_rating = 0
        # Assigning all the values to the dictionary
        result['all_tickets'] = all_tickets
        result['high_priority'] = high_priority
        result['urgent'] = urgent
        result['average_open_hour'] = round(average_open_hour, 2)
        result['high_priority_average_open_hour'] = round(
            high_priority_average_open_hour, 2)
        result['urgent_average_open_hour'] = round(urgent_average_open_hour, 2)
        result['failed_ticket_count'] = failed_ticket_count
        result[
            'failed_high_priority_ticket_count'] = failed_high_priority_ticket_count
        result['failed_urgent_ticket_count'] = failed_urgent_ticket_count
        result['my_today_closed_ticket_count'] = my_today_closed_ticket_count
        result['my_success_rate_ticket_count'] = my_success_rate_ticket_count
        result['my_average_rating'] = my_average_rating
        result[
            'my_last_seven_days_closed_ticket_count'] = my_last_seven_days_closed_ticket_count
        result[
            'my_last_seven_days_success_rate'] = my_last_seven_days_success_rate
        result[
            'my_last_seven_days_average_rating'] = my_last_seven_days_average_rating
        return result

    def get_acton(self, action_ref, title, search_view_ref):
        action = self.env['ir.actions.actions']._for_xml_id(action_ref)
        action = clean_action(action, self.env)
        if title:
            action['display_name'] = title
        if search_view_ref:
            action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        if 'views' not in action:
            action['views'] = [(False, view) for view in
                               action['view_mode'].split(",")]
        return action

    @api.onchange('stage_id')
    def _onchange_ticket_stage_id(self):
        if self.stage_id.is_closed:
            self.closed_date = fields.Datetime.now()
        else:
            self.closed_date = False

    def _compute_last_seven_days(self):
        self.last_seven_days = datetime.now() - timedelta(days=6)

    @api.depends("sla_ids")
    def _compute_average_open_hours(self):
        max_within_hour_values = []
        open_sla_tickets = self.search(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False)])
        within_hour_values = open_sla_tickets.mapped(
            lambda open_ticket: open_ticket.sla_ids.mapped('within_hour'))
        if within_hour_values:
            for hours in within_hour_values:
                if hours:
                    max_within_hour_values.append(max(hours))
        if len(max_within_hour_values):
            self.open_ticket_average_hours = sum(max_within_hour_values) / len(
                max_within_hour_values)
        else:
            self.open_ticket_average_hours = 0

    @api.depends('closed_date')
    def _compute_is_closed_today(self):
        today = fields.Date.today()
        for ticket in self:
            if ticket.closed_date and ticket.closed_date.date() == today:
                ticket.is_closed_today = True
            else:
                ticket.is_closed_today = False

    @api.depends("sla_ids")
    def _compute_high_priority_average_open_hours(self):
        max_high_priority_within_hour_values = []
        high_priority_open_sla_tickets = self.search(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False), ('priority', '=', '2')])
        high_priority_within_hour_values = high_priority_open_sla_tickets.mapped(
            lambda high_priority_ticket: high_priority_ticket.sla_ids.mapped(
                'within_hour'))
        if high_priority_within_hour_values:
            for hours in high_priority_within_hour_values:
                if hours:
                    max_high_priority_within_hour_values.append(max(hours))
        if len(max_high_priority_within_hour_values):
            high_priority_average_open_hour = sum(
                max_high_priority_within_hour_values) / len(
                max_high_priority_within_hour_values)
            self.high_priority_ticket_average_hours = high_priority_average_open_hour
        else:
            self.high_priority_ticket_average_hours = 0

    @api.depends("sla_ids")
    def _compute_urgent_ticket_average_open_hours(self):
        max_urgent_within_hour_values = []
        urgent_open_sla_tickets = self.search(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False),
             ('priority', '=', '3')])
        urgent_within_hour_values = urgent_open_sla_tickets.mapped(
            lambda urgent_ticket: urgent_ticket.sla_ids.mapped('within_hour'))
        if urgent_within_hour_values:
            for hours in urgent_within_hour_values:
                if hours:
                    max_urgent_within_hour_values.append(max(hours))
        if len(max_urgent_within_hour_values):
            self.urgent_ticket_average_hours = sum(
                max_urgent_within_hour_values) / len(
                max_urgent_within_hour_values)
        else:
            self.urgent_ticket_average_hours = 0

    @api.model
    def _cron_auto_close_tickets(self):
        teams = self.env['helpdesk.team'].search([('auto_close_days', '>', 0)])
        for team in teams:
            # Auto-close tickets
            close_date = datetime.now() - timedelta(days=team.auto_close_days)
            tickets_to_close = self.search([
                ('team_id', '=', team.id),
                ('stage_id.is_closed', '=', False),
                ('write_date', '<', close_date)
            ])
            if tickets_to_close:
                solved_stage = team.auto_close_stage_id or self.env.ref(
                    'cyllo_help_desk.solved_ticket')
                tickets_to_close.write({'stage_id': solved_stage.id})
            # Send reminders
            if team.auto_close_reminder_days > 0:
                reminder_date = datetime.now() - timedelta(
                    days=team.auto_close_reminder_days)
                tickets_to_remind = self.search([
                    ('team_id', '=', team.id),
                    ('stage_id.is_closed', '=', False),
                    ('write_date', '<', reminder_date),
                    ('message_needaction', '=', False)
                    # Simple heuristic to avoid spamming
                ])
                for ticket in tickets_to_remind:
                    ticket._send_auto_close_reminder()

    def _send_auto_close_reminder(self):
        self.ensure_one()
        template = self.env.ref(
            'cyllo_help_desk.help_desk_mail_template_auto_close_reminder',
            raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_toggle_sla_pause(self):
        for record in self:
            if record.sla_paused:
                # Calculate how long it was paused and adjust deadline (conceptual)
                # In a real system, you'd store pause durations
                record.sla_paused = False
                record.message_post(body=_("SLA policy resumed."))
            else:
                record.sla_paused = True
                record.sla_pause_date = datetime.now()
                record.message_post(body=_("SLA policy paused."))

    def _escalate_ticket(self):
        """ Escalate ticket to manager if SLA fails """
        manager_group = self.env.ref('cyllo_help_desk.cyllo_help_desk_manager')
        managers = self.env['res.users'].search(
            [('groups_id', 'in', manager_group.id)])
        if managers:
            self.message_post(
                body=_(
                    "Ticket %s has failed SLA and is escalated to managers.") % self.ticket,
                partner_ids=managers.partner_id.ids,
                subtype_xmlid='mail.mt_comment'
            )

    def action_create_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_orders")
        action['res_model'] = 'sale.order'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_helpdesk_ticket_id': self.id,
        }
        self.message_post(body=_("Sale Order creation initiated."))
        return action

    def action_create_repair(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "repair.action_repair_order_tree")
        action['res_model'] = 'repair.order'
        action['view_mode'] = 'form'
        action['views'] = [
            (self.env.ref('repair.view_repair_order_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_ticket_id': self.id,
            'default_helpdesk_ticket_id': self.id,
        }
        self.message_post(body=_("Repair Order creation initiated."))
        return action

    def _get_excluded_duration(self, sla_policy):
        """ Calculate total duration spent in excluded stages for a given SLA policy """
        self.ensure_one()
        if not sla_policy.excluded_stage_ids:
            return 0.0
        history = self.env['helpdesk.stage.history'].search([
            ('ticket_id', '=', self.id),
            ('stage_id', 'in', sla_policy.excluded_stage_ids.ids)
        ])
        total_duration = 0.0
        for record in history:
            if record.end_date:
                total_duration += record.duration
            else:
                # Still in an excluded stage, calculate duration up until now
                diff = fields.Datetime.now() - record.start_date
                total_duration += diff.total_seconds() / 3600.0
        return total_duration

    def action_create_field_service_request(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_field_service.action_view_all_requests")
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref(
            'cyllo_field_service.view_field_service_request_form').id, 'form')]
        action['target'] = 'current'
        # Priority mapping
        priority_map = {
            '0': 'b',  # Normal -> Medium
            '1': 'a',  # Low -> Low
            '2': 'c',  # High -> High
            '3': 'd',  # Very High -> Very High
        }
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_description': self.description,
            'default_helpdesk_ticket_id': self.id,
            'default_priority': priority_map.get(self.priority, 'a'),
            'default_sale_order_id': self.sale_order_id.id,
        }
        self.message_post(body=_("Field Service Request creation initiated."))
        return action

    def action_create_crm_lead(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm.crm_lead_action_pipeline")
        action['res_model'] = 'crm.lead'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('crm.crm_lead_view_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_name': self.name,
            'default_helpdesk_ticket_id': self.id,
        }
        self.message_post(body=_("CRM Lead creation initiated."))
        return action

    @api.onchange('canned_response_ids')
    def onchange_canned_response_ids(self):
        for ticket in self:
            if ticket.canned_response_ids:
                new_content = []
                for response in ticket.canned_response_ids:
                    if response.substitution:
                        new_content.append(response.substitution)
                if new_content:
                    combined_content = '<br/>'.join(new_content)
                    ticket.description = combined_content

    def action_create_refund(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("Please select an invoice first."))

        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_view_account_move_reversal")
        action['context'] = {
            'active_model': 'account.move',
            'active_ids': [self.invoice_id.id],
        }
        self.message_post(body=_("Refund/Credit Note creation initiated."))
        return action

    def action_create_coupon(self):
        self.ensure_one()
        program = self.env['loyalty.program'].search(
            [('program_type', '=', 'coupons')], limit=1)
        if not program:
            raise UserError(
                _("No coupon program is configured. Create a coupon loyalty program first."))

        action = self.env["ir.actions.actions"]._for_xml_id(
            "loyalty.loyalty_generate_wizard_action")
        action['context'] = {
            'active_id': program.id,
            'default_program_id': program.id,
            'default_mode': 'selected' if self.customer_id else 'anonymous',
            'default_customer_ids': [
                (6, 0, [self.customer_id.id])] if self.customer_id else [],
            'default_coupon_qty': 1,
            'default_helpdesk_ticket_id': self.id,
        }
        self.message_post(body=_("Coupon generation initiated."))
        return action

    def action_create_return(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("Please select a Sale Order first."))

        pickings = self.env['stock.picking'].search([
            ('sale_id', '=', self.sale_order_id.id),
            ('state', '=', 'done'),
            ('picking_type_code', '=', 'outgoing'),
        ])

        if not pickings:
            raise UserError(_("No completed delivery available for return."))

        if len(pickings) == 1:
            action = self.env.ref('stock.act_stock_return_picking').read()[0]
            action['context'] = {
                'active_id': pickings.id,
                'active_ids': [pickings.id],
                'active_model': 'stock.picking',
                'default_helpdesk_ticket_id': self.id,
            }
            self.message_post(body=_("Return process initiated."))
            return action

        self.message_post(body=_("Return process initiated."))
        return {
            'name': _('Select Delivery to Return'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket.return.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'cyllo_help_desk.helpdesk_ticket_return_wizard_view_form').id,
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_sale_order_id': self.sale_order_id.id,
            }
        }

    def action_view_duplicates(self):
        self.ensure_one()
        return {
            'name': _('Duplicate Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.duplicate_ticket_ids.ids)],
            'target': 'current',
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_orders")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_refunds(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_refund_type")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id),
                            ('move_type', '=', 'out_refund')]
        return action

    def action_view_repairs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "repair.action_repair_order_tree")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_crm_leads(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm.crm_lead_action_pipeline")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_coupons(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "loyalty.loyalty_card_action")
        action['view_mode'] = 'list,form'
        action['domain'] = [('id', 'in', self.coupon_ids.ids)]
        return action

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all")
        action['view_mode'] = 'list,form'
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

    def action_view_field_service_requests(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_field_service.action_view_all_requests")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action
