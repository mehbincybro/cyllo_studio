from datetime import datetime, timedelta
from itertools import groupby
from odoo import fields, models


class HelpDeskTeam(models.Model):
    _name = "helpdesk.team"
    _description = "HelpDesk Team"

    name = fields.Char(string="Name", help="Team name")
    description = fields.Html(string="Description", help="Description about the team")
    timesheet = fields.Boolean(string="Timesheet",
                               help="Can add timesheet for the ticket")
    ticket_id = fields.Many2one('helpdesk.ticket', string="All tickets")
    user_id = fields.Many2one(related='ticket_id.user_id', string="Stage")
    state_id = fields.Many2one(related='ticket_id.stage_id', string="Stage")
    priority = fields.Selection(related='ticket_id.priority',
                                string="Priority")
    sla_flag = fields.Boolean(related='ticket_id.sla_flag', string="SLA Flag")
    sla_failed = fields.Boolean(compute="_compute_sla_failed_ticket",
                                string="SLA failed ticket",
                                help="Ticket that failed SLA policy")
    open_count = fields.Integer(string="Open Ticket Count",
                                compute="_compute_open_helpdesk_ticket_count")
    unassigned_count = fields.Integer(string="Unassigned Ticket Count",
                                      compute="_compute_unassigned_ticket_count",
                                      help="Count of tickets in the team that are not assigned to a person")
    urgent_count = fields.Integer(string="Urgent Ticket Count",
                                  compute="_compute_urgent_ticket_count",
                                  help="Count of urgent priority tickets in the team")
    failed_sla_count = fields.Integer(string="Failed Ticket Count",
                                      compute="_compute_failed_ticket_count",
                                      help="Count of failed tickets in the team")
    color = fields.Integer(string="Color")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        help="Company for this helpdesk team",
    )
    success_rate = fields.Float(compute="_compute_success_rate",
                                string="Success Rate",
                                help="Team wise success rate")
    working_hour_id = fields.Many2one('resource.calendar',
                                      string="Working Hours",
                                      help="Working time of the team")
    sla_policy = fields.Boolean(string="SLA Policies",
                                help="To make sure the tickets are managed on time")
    customer_rating = fields.Boolean(string="Customer Rating",
                                     help="Know the customer rating about the service")
    use_sla = fields.Boolean(string="Use SLA", default=True)
    use_timesheet = fields.Boolean(string="Use Timesheets", default=True)
    use_credit_notes = fields.Boolean(string="Use Credit Notes")
    use_coupons = fields.Boolean(string="Use Coupons")
    use_replacements = fields.Boolean(string="Use Replacements")
    use_field_service = fields.Boolean(string="Use Field Service")
    use_gift_cards = fields.Boolean(string="Use Gift Cards")
    use_returns = fields.Boolean(string="Use Returns")
    use_repairs = fields.Boolean(string="Use Repairs")
    use_website_ticket_creation = fields.Boolean(
        string="Website Ticket Creation",
        help="Allow this team to receive tickets created from the website form.",
    )
    use_livechat_ticket_creation = fields.Boolean(
        string="LiveChat Ticket Creation",
        help="Allow this team to receive tickets created from the livechat /ticket command.",
    )
    
    # Assignment Settings
    assignment_method = fields.Selection([
        ('manual', 'Manual'),
        ('random', 'Random'),
        ('round_robin', 'Round Robin'),
        ('skill', 'Skill-based')
    ], string='Assignment Method', default='manual')
    last_assigned_user_id = fields.Many2one('res.users', string='Last Assigned User', help="Used for Round Robin assignment")
    member_ids = fields.Many2many('res.users', string='Team Members', help="Users who can be assigned to tickets in this team")
    
    # Auto-close settings
    auto_close_days = fields.Integer(string='Auto-close after (days)', default=0)
    auto_close_reminder_days = fields.Integer(string='Auto-close reminder after (days)', default=0)
    auto_close_stage_id = fields.Many2one('helpdesk.stage', string='Auto-close Stage', help="Ticket will be moved to this stage once it is auto-closed.")
    closed_ticket_count = fields.Integer(
        compute="_compute_closed_ticket_count", string="Closed Ticket Count",
        help="Count of closed tickets in the team")
    rating_avg = fields.Float(compute="_compute_rating_avg",
                               string="Average Rating")
    rating_count = fields.Integer(compute="_compute_rating_avg",
                                   string="Rating Count")

    def _compute_open_helpdesk_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('stage_id.is_closed', '=', False), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.open_count = ticket_dict.get(team.id)

    def _compute_unassigned_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('user_id', '=', False), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.unassigned_count = ticket_dict.get(team.id)

    def _compute_urgent_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('priority', '=', '3'), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.urgent_count = ticket_dict.get(team.id)

    def _compute_failed_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('sla_flag', '=', True), ('sla_failed', '=', True),
             ('stage_id.is_closed', '=', False), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.failed_sla_count = ticket_dict.get(team.id)

    def _compute_sla_failed_ticket(self):
        """Set team SLA flag when any ticket in the team has failed SLA."""
        failed_teams = self.env['helpdesk.ticket'].read_group(
            [('team_id', 'in', self.ids), ('sla_failed', '=', True)],
            ['team_id'],
            ['team_id'],
        )
        failed_team_ids = {
            data['team_id'][0] for data in failed_teams if data.get('team_id')
        }
        for team in self:
            team.sla_failed = team.id in failed_team_ids

    def action_get_team_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_help_desk.helpdesk_team_ticket_action")
        return action

    def get_team_open_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_help_desk.helpdesk_team_open_ticket_action")
        return action

    def get_team_unassigned_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_help_desk.helpdesk_team_unassigned_ticket_action")
        return action

    def get_team_urgent_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_help_desk.helpdesk_team_urgent_ticket_action")
        return action

    def get_team_failed_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_help_desk.helpdesk_team_failed_ticket_action")
        return action

    def _compute_success_rate(self):
        one_week_back_date = datetime.now() - timedelta(
            days=6)
        tickets = self.env['helpdesk.ticket'].search_read(
            [('closed_date', '>=', one_week_back_date), ('team_id', '!=', False)],
            ['sla_flag', 'team_id', 'closed_date', 'sla_failed'])
        sorted_tickets = sorted(tickets, key=lambda x: x['team_id'])
        grouped_tickets = {}
        closed_ticket_count_dict = {}
        passed_ticket_count_dict = {}
        for team_id, group in groupby(sorted_tickets,
                                      key=lambda x: x['team_id']):
            grouped_tickets[team_id] = list(group)
            ticket_count = len(grouped_tickets[team_id])
            closed_ticket_count_dict.update({team_id[0]: ticket_count})
        for team_id, tickets in grouped_tickets.items():
            passed_tickets = [ticket for ticket in tickets if
                              not ticket['sla_failed']]
            passed_ticket_count_dict[team_id[0]] = len(passed_tickets)
        for team in self:
            if team.id in closed_ticket_count_dict.keys():
                team.success_rate = (passed_ticket_count_dict[team.id] /
                                     closed_ticket_count_dict[team.id]) * 100
            else:
                team.success_rate = 0

    def _compute_closed_ticket_count(self):
        one_week_back_date = datetime.now() - timedelta(
            days=6)
        for team in self:
            team.closed_ticket_count = self.env[
                'helpdesk.ticket'].search_count(
                [('stage_id.is_closed', '=', True),
                 ('closed_date', '>=', one_week_back_date),
                 ('team_id', '=', team.id)])

    def get_team_closed_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_help_desk.helpdesk_team_closed_ticket_action")
        return action

    def get_team_solved_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_help_desk.helpdesk_team_successfully_solved_ticket_action")
        return action

    def _compute_rating_avg(self):
        for team in self:
            ratings = self.env['rating.rating'].search([
                ('helpdesk_team_id', '=', team.id),
                ('consumed', '=', True),
            ])
            if ratings:
                team.rating_avg = sum(ratings.mapped('rating')) / len(ratings)
                team.rating_count = len(ratings)
            else:
                team.rating_avg = 0
                team.rating_count = 0
