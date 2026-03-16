from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
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
                              help="Helpdesk team")
    priority = fields.Selection([('0', 'Normal'), ('1', 'Low'), ('2', 'High'),
                                 ('3', 'Very High')], default='0',
                                string="Priority")
    customer_id = fields.Many2one('res.partner', string="Customer",
                                  help="Customer of the ticket")
    email = fields.Char(string="Email", help="Customer email id")
    phone = fields.Char(string="Phone", help="Customer phone number")
    category_id = fields.Many2one('helpdesk.category', string="Category",
                                  help="Ticket category")
    tag_id = fields.Many2one('helpdesk.tag', string="Tag", help="Legacy single ticket tag")
    tag_ids = fields.Many2many('helpdesk.tag', string="Tags", help="Ticket tags")
    user_id = fields.Many2one('res.users', string="Assigned to",
                              default=lambda self: self.env.user,
                              help="The person to whom the ticket assigned to")
    company_id = fields.Many2one('res.company', string="Company",
                                 required=True,
                                 default=lambda self: self.env.company,
                                 help="Company for the helpdesk ticket")
    description = fields.Html(string="Description",
                              help="Description about the issue or question")
    internal_notes = fields.Html(string="Internal Notes",
                                 help="Internal notes visible only to staff")
    timesheet_ids = fields.One2many('account.analytic.line', 'ticket_id',
                                    string="Timesheet",
                                    help="Time spent by the employee for this ticket")
    timesheet_bool = fields.Boolean(related='team_id.timesheet')
    sla_ids = fields.Many2many('helpdesk.sla', string="SLA policy",
                               help="SLA policy for this ticket")
    sla_flag = fields.Boolean(default=False,
                              help="To check SLA policy set or not")
    sla_failed = fields.Boolean(string="SLA failed ticket", default=False,
                                help="Ticket that failed SLA policy")
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
    date = fields.Datetime(default=datetime.now())
    closed_date = fields.Datetime()
    sla_status_ids = fields.One2many('sla.status', 'ticket_id',
                                     string="SLA Status",
                                     help="Status of helpdesk ticket")
    last_seven_days = fields.Datetime(compute="_compute_last_seven_days")
    open_ticket_average_hours = fields.Float(string="Open Hours", compute="_compute_average_open_hours", store=True)
    high_priority_ticket_average_hours = fields.Float(string="High Priority Open Hours", compute="_compute_high_priority_average_open_hours", store=True)
    urgent_ticket_average_hours = fields.Float(string="Urgent Ticket Open Hours", compute="_compute_urgent_ticket_average_open_hours", store=True)
    is_closed_today = fields.Boolean(string='Closed Today', compute='_compute_is_closed_today')

    # Parent-Child Linking
    parent_id = fields.Many2one('helpdesk.ticket', string='Parent Ticket', help='Reference to the main ticket')
    child_ids = fields.One2many('helpdesk.ticket', 'parent_id', string='Sub-tickets')

    # Dependencies
    dependency_ids = fields.Many2many('helpdesk.ticket', 'helpdesk_ticket_dependency_rel', 'ticket_id', 'dependency_id', string='Dependencies')

    # Skills and Assignment
    skill_ids = fields.Many2many('helpdesk.skill', string='Required Skills')

    # SLA Pause
    sla_paused = fields.Boolean(string='SLA Paused', default=False)
    sla_pause_date = fields.Datetime()
    sla_progress = fields.Float(string='SLA Progress', compute='_compute_sla_progress', help="Progress towards the next SLA deadline")

    # Integrations
    sale_order_ids = fields.One2many('sale.order', 'helpdesk_ticket_id', string='Sales Orders')
    repair_ids = fields.One2many('repair.order', 'helpdesk_ticket_id', string='Repair Orders')
    task_ids = fields.One2many('project.task', 'helpdesk_ticket_id', string='Field Service Tasks')
    crm_lead_ids = fields.One2many('crm.lead', 'helpdesk_ticket_id', string='CRM Leads')
    refund_ids = fields.One2many('account.move', 'helpdesk_ticket_id', string='Refund/Credit Notes')
    coupon_ids = fields.Many2many('loyalty.card', string='Coupons')
    picking_ids = fields.Many2many('stock.picking', string='Returns/Replacements')
    sale_order_count = fields.Integer(compute='_compute_integration_counts')
    refund_count = fields.Integer(compute='_compute_integration_counts')
    task_count = fields.Integer(compute='_compute_integration_counts')
    repair_count = fields.Integer(compute='_compute_integration_counts')
    crm_lead_count = fields.Integer(compute='_compute_integration_counts')
    coupon_count = fields.Integer(compute='_compute_integration_counts')
    picking_count = fields.Integer(compute='_compute_integration_counts')

    # Portal
    website_published = fields.Boolean(string='Visible in Portal', default=True)

    # Canned Response
    canned_response_id = fields.Many2one('mail.shortcode', string='Canned Response')

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        stage_one = self.env.ref('cyllo_help_desk.new_ticket')
        if self._origin.stage_id and self._origin.stage_id != stage_one and self.stage_id == stage_one:
            raise UserError('Cannot go back')
        
        # Dependency Check
        if self.stage_id.is_closed:
            unresolved_deps = self.dependency_ids.filtered(lambda t: not t.stage_id.is_closed)
            if unresolved_deps:
                raise UserError(_("Cannot close ticket until dependencies are resolved: %s") % (", ".join(unresolved_deps.mapped('ticket'))))

        if self._origin.sla_ids:
            sorted_records = sorted(self._origin.sla_ids,
                                    key=lambda x: x['within_hour'])
            for record in sorted_records:
                # Calculating the time difference between created datetime and
                # current datetime
                created_date = datetime.strptime(str(self._origin.create_date),
                                                 "%Y-%m-%d %H:%M:%S.%f")

                # Calculating the SLA deadline
                work_hours = self._origin.team_id.working_hour_id
                average_work_hours = work_hours.hours_per_day or 8
                deadline = record.within_hour / average_work_hours
                deadline_in_hours = deadline * average_work_hours
                deadline_date = work_hours.plan_hours(deadline_in_hours,
                                                      created_date,
                                                      compute_leaves=True)
                if record.target_stage.sequence >= self.stage_id.sequence and deadline_date >= datetime.now():
                    if record.target_stage.sequence == self.stage_id.sequence:
                        self.sla_status_ids.create(
                            {'id': record.id, 'ticket_id': self._origin.id,
                             'state': 'pass'})
                else:
                    if record.target_stage.sequence == self.stage_id.sequence or (
                            record.target_stage.sequence >= self.stage_id.sequence and deadline_date <= datetime.now()):
                        self.sla_status_ids.create(
                            {'id': record.id, 'ticket_id': self._origin.id,
                             'state': 'fail'})
                        self._escalate_ticket()
        if self._origin.stage_id.is_closed:
            self.closed_date = datetime.now()
            # If parent is closed, close children
            if self.child_ids:
                closed_stage = self.env.ref('cyllo_help_desk.solved_ticket')
                self.child_ids.write({'stage_id': closed_stage.id})

    @api.depends('create_date', 'sla_ids', 'stage_id', 'sla_paused')
    def _compute_sla_progress(self):
        for ticket in self:
            if not ticket.sla_ids or not ticket.create_date or ticket.stage_id.is_closed:
                ticket.sla_progress = 0
                continue
            
            # Simple linear progress estimate for demo purposes
            # In a real system, you'd find the earliest deadline
            elapsed = (datetime.now() - ticket.create_date).total_seconds() / 3600.0
            earliest_sla = min(ticket.sla_ids.mapped('within_hour')) or 1
            progress = (elapsed / earliest_sla) * 100
            ticket.sla_progress = min(max(progress, 0), 100)

    @api.depends('sale_order_ids', 'refund_ids', 'task_ids', 'repair_ids', 'crm_lead_ids', 'coupon_ids', 'picking_ids')
    def _compute_integration_counts(self):
        for ticket in self:
            ticket.sale_order_count = len(ticket.sale_order_ids)
            ticket.refund_count = len(ticket.refund_ids.filtered(lambda move: move.move_type == 'out_refund'))
            ticket.task_count = len(ticket.task_ids)
            ticket.repair_count = len(ticket.repair_ids)
            ticket.crm_lead_count = len(ticket.crm_lead_ids)
            ticket.coupon_count = len(ticket.coupon_ids)
            ticket.picking_count = len(ticket.picking_ids)

    @api.model_create_multi
    def create(self, vals):
        """ Sequence for helpdesk tickets """
        if vals[0].get('ticket', _('New')) == _('New'):
            vals[0]['ticket'] = self.env['ir.sequence'].next_by_code(
                'helpdesk.ticket') or 'New'
        res = super(HelpDeskTicket, self).create(vals)
        for ticket in res:
            ticket._assign_ticket()
        return res

    def _assign_ticket(self):
        self.ensure_one()
        if self.user_id or not self.team_id or self.team_id.assignment_method == 'manual':
            return
        
        team = self.team_id
        if team.assignment_method == 'random':
            members = self.env['res.users'].search([('groups_id', 'in', self.env.ref('cyllo_help_desk.cyllo_help_desk_user').id)])
            if members:
                import random
                self.user_id = random.choice(members.ids)
        elif team.assignment_method == 'skill':
            required_skills = self.skill_ids
            if required_skills:
                candidates = self.env['res.users'].search([
                    ('helpdesk_skill_ids', 'in', required_skills.ids),
                    ('groups_id', 'in', self.env.ref('cyllo_help_desk.cyllo_help_desk_user').id)
                ])
                if candidates:
                    candidate = max(candidates, key=lambda c: len(c.helpdesk_skill_ids & required_skills))
                    self.user_id = candidate.id
        elif team.assignment_method == 'round_robin':
            members = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('cyllo_help_desk.cyllo_help_desk_user').id)
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
        if self.customer_id or self.team_id:
            sla_record = self.env['helpdesk.sla'].search(
                ['|', ('customer_ids', '=', self.customer_id.id),
                 ('team_id', '=', self.team_id.id)]).ids
            if sla_record:
                self.sla_flag = True
                self.sla_ids = [(6, 0, sla_record)]
            else:
                self.sla_ids = [(5,)]

    @api.onchange('tag_id')
    def _onchange_tag_id(self):
        for ticket in self:
            if ticket.tag_id and ticket.tag_id not in ticket.tag_ids:
                ticket.tag_ids = [(4, ticket.tag_id.id)]

    def _expand_states(self, states, domain, order):
        return self.env['helpdesk.stage'].search([])

    def write(self, vals):
        result = super(HelpDeskTicket, self).write(vals)
        if self.stage_id.id == self.env.ref(
                'cyllo_help_desk.in_progress_ticket').id:
            mail_template_exec = self.env.ref(
                'cyllo_help_desk.help_desk_mail_template')
            mail_template_exec['email_from'] = self.user_id.login
            mail_template_exec['email_to'] = self.customer_id.email
            mail_template_exec.sudo().send_mail(self._origin.id,
                                                force_send=True)
            # Adding a message in the chatter to inform that the mail
            # sent or not
            body = f"""Email sent to {self.customer_id.name}"""
            self.message_post(body=body, subject="TICKET CREATED")
        if self.stage_id.id == self.env.ref('cyllo_help_desk.solved_ticket').id:
            mail_template_exec = self.env.ref(
                'cyllo_help_desk.help_desk_mail_template_issue_solved')
            mail_template_exec['email_from'] = self.user_id.login
            mail_template_exec['email_to'] = self.customer_id.email
            mail_template_exec.sudo().send_mail(self._origin.id,
                                                force_send=True)
            # Adding a message in the chatter to inform that the mail
            # sent or not
            body = f"""Work done mail sent to {self.customer_id.name}"""
            self.message_post(body=body, subject="ISSUE SOLVED")
        return result

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
        # Taking the count of tickets in priority base
        all_tickets = self.search_count([])
        high_priority = self.search_count([('priority', '=', '2')])
        urgent = self.search_count([('priority', '=', '3')])
        # Calculating the open average hours of the tickets of current user
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
            average_open_hour = sum(max_within_hour_values) / len(
                max_within_hour_values)
            self.open_ticket_average_hours = average_open_hour
        else:
            average_open_hour = 0
            self.open_ticket_average_hours = 0
        # Calculating the open average hours of the high priority tickets of
        # current user
        max_high_priority_within_hour_values = []
        high_priority_open_sla_tickets = self.search(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False),
             ('priority', '=', '2')])
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
            high_priority_average_open_hour = 0

        # Calculating the open average hours of the urgent tickets of
        # current user
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
            urgent_average_open_hour = sum(
                max_urgent_within_hour_values) / len(
                max_urgent_within_hour_values)
        else:
            urgent_average_open_hour = 0

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
            my_success_rate_ticket_count = round(((passed_ticket_count / closed_ticket_count) * 100), 2)
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
        result['my_last_seven_days_closed_ticket_count'] = my_last_seven_days_closed_ticket_count
        result['my_last_seven_days_success_rate'] = my_last_seven_days_success_rate
        result['my_last_seven_days_average_rating'] = my_last_seven_days_average_rating
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
            self.closed_date = fields.datetime.today()
        else:
            self.closed_date = ''

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
                solved_stage = self.env.ref('cyllo_help_desk.solved_ticket')
                tickets_to_close.write({'stage_id': solved_stage.id})
            
            # Send reminders
            if team.auto_close_reminder_days > 0:
                reminder_date = datetime.now() - timedelta(days=team.auto_close_reminder_days)
                tickets_to_remind = self.search([
                    ('team_id', '=', team.id),
                    ('stage_id.is_closed', '=', False),
                    ('write_date', '<', reminder_date),
                    ('message_needaction', '=', False) # Simple heuristic to avoid spamming
                ])
                for ticket in tickets_to_remind:
                    ticket._send_auto_close_reminder()

    def _send_auto_close_reminder(self):
        self.ensure_one()
        template = self.env.ref('cyllo_help_desk.help_desk_mail_template_auto_close_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_toggle_sla_pause(self):
        for record in self:
            if record.sla_paused:
                # Calculate how long it was paused and adjust deadline (conceptual)
                # In a real system, you'd store pause durations
                record.sla_paused = False
            else:
                record.sla_paused = True
                record.sla_pause_date = datetime.now()

    def _escalate_ticket(self):
        """ Escalate ticket to manager if SLA fails """
        manager_group = self.env.ref('cyllo_help_desk.cyllo_help_desk_manager')
        managers = self.env['res.users'].search([('groups_id', 'in', manager_group.id)])
        if managers:
            self.message_post(
                body=_("Ticket %s has failed SLA and is escalated to managers.") % self.ticket,
                partner_ids=managers.partner_id.ids,
                subtype_xmlid='mail.mt_comment'
            )

    def action_create_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['res_model'] = 'sale.order'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_helpdesk_ticket_id': self.id,
        }
        return action

    def action_create_repair(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("repair.action_repair_order_tree")
        action['res_model'] = 'repair.order'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('repair.view_repair_order_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_ticket_id': self.id,
            'default_helpdesk_ticket_id': self.id,
        }
        return action

    def action_create_fsm_task(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("project.action_view_task")
        action['res_model'] = 'project.task'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('project.view_task_form2').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_name': self.name,
            'default_description': self.description,
            'default_helpdesk_ticket_id': self.id,
        }
        return action

    def action_create_crm_lead(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_action_pipeline")
        action['res_model'] = 'crm.lead'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('crm.crm_lead_view_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_name': self.name,
            'default_helpdesk_ticket_id': self.id,
        }
        return action

    @api.onchange('canned_response_id')
    def onchange_canned_response_id(self):
        for ticket in self:
            if not ticket.canned_response_id:
                continue
            canned_html = ticket.canned_response_id.substitution or ''
            if canned_html:
                ticket.description = (
                    '%s<br/>%s' % (ticket.description, canned_html)
                    if ticket.description else canned_html
                )
            ticket.canned_response_id = False

    def action_create_refund(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_refund_type")
        action['res_model'] = 'account.move'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_move_type': 'out_refund',
            'default_partner_id': self.customer_id.id,
            'default_helpdesk_ticket_id': self.id,
        }
        return action

    def action_create_coupon(self):
        self.ensure_one()
        program = self.env['loyalty.program'].search([('program_type', '=', 'coupons')], limit=1)
        if not program:
            raise UserError(_("No coupon program is configured. Create a coupon loyalty program first."))

        action = self.env["ir.actions.actions"]._for_xml_id("loyalty.loyalty_generate_wizard_action")
        action['context'] = {
            'active_id': program.id,
            'default_program_id': program.id,
            'default_mode': 'selected' if self.customer_id else 'anonymous',
            'default_customer_ids': [(6, 0, [self.customer_id.id])] if self.customer_id else [],
            'default_coupon_qty': 1,
            'default_helpdesk_ticket_id': self.id,
        }
        return action

    def action_create_return(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        action['res_model'] = 'stock.picking'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_picking_type_id': self.env['stock.picking.type'].search([('code', '=', 'incoming')], limit=1).id,
            'default_helpdesk_ticket_id': self.id,
        }
        return action

    def action_view_sale_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_refunds(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_refund_type")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id), ('move_type', '=', 'out_refund')]
        return action

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("project.action_view_task")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_repairs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("repair.action_repair_order_tree")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_crm_leads(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_action_pipeline")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_coupons(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("loyalty.loyalty_card_action")
        action['view_mode'] = 'list,form'
        action['domain'] = [('id', 'in', self.coupon_ids.ids)]
        return action

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        action['view_mode'] = 'list,form'
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action
