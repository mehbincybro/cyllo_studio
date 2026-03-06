from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AuditRule(models.Model):
    _name = 'audit.rule'
    _description = 'Audit Rule'
    _order = 'sequence, name'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, domain=[('transient', '=', False)],
                               ondelete='cascade', help='Select the model to audit')
    model_name = fields.Char(string='Model Name', related='model_id.model', store=True)
    log_level = fields.Selection([('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')],
                                 string='Log Level', default='info', required=True)
    # Operation Types
    track_create = fields.Boolean(string='Track Create', default=True)
    track_write = fields.Boolean(string='Track Update', default=True)
    track_unlink = fields.Boolean(string='Track Delete', default=True)
    track_read = fields.Boolean(string='Track Read', default=False,
                                help="Warning: Enabling read tracking can generate a large number of logs")
    # Field Tracking
    tracking_scope = fields.Selection([('all', 'All Fields'), ('tracked', 'Only Tracked Fields'),
                                       ('excluded', 'All Except Excluded')], string='Tracking Scope', default='all',
                                      required=True)
    tracked_field_ids = fields.Many2many('ir.model.fields', 'audit_rule_tracked_field_rel',
                                         'rule_id', 'field_id', string='Tracked Fields',
                                         domain="[('model_id', '=', model_id)]")
    excluded_field_ids = fields.Many2many('ir.model.fields', 'audit_rule_excluded_field_rel',
                                          'rule_id', 'field_id', string='Excluded Fields',
                                          domain="[('model_id', '=', model_id)]")
    # User Tracking Selection - NEW ENHANCED FIELD
    user_selection_type = fields.Selection([('all', 'All Users'), ('specific', 'Specific Users'),
                                            ('exclude', 'Exclude Specific Users'), ('group', 'Users by Group')],
                                           string='User Selection', default='all', required=True)
    # User IDs for specific tracking
    user_ids = fields.Many2many('res.users', 'audit_rule_user_rel', 'rule_id', 'user_id',
                                string='Users', help='Select specific users to track or exclude')
    # Group selection for group-based tracking
    group_ids = fields.Many2many('res.groups', 'audit_rule_group_rel', 'rule_id',
                                 'group_id', string='User Groups',
                                 help='Select groups whose members should be tracked')
    # User domain filter (advanced)
    user_domain = fields.Char(string='User Domain',
                              help='Advanced domain filter for users (e.g., [("company_id", "=", 1)])')
    # Additional Options
    track_ip = fields.Boolean(string='Track IP Address', default=True)
    track_session = fields.Boolean(string='Track Session', default=False)
    # Retention Policy
    has_retention = fields.Boolean(string='Enable Retention Policy', default=False)
    retention_days = fields.Integer(string='Keep Logs for (Days)', default=30)
    # Statistics
    log_count = fields.Integer(string='Log Count', compute='_compute_log_count')
    notes = fields.Text(string='Notes')
    user_count = fields.Integer(string='Affected Users', compute='_compute_user_count', store=True)

    @api.depends('model_id')
    def _compute_log_count(self):
        for rule in self:
            rule.log_count = self.env['audit.log'].search_count([
                ('model_id', '=', rule.model_id.id)
            ])

    @api.onchange('tracking_scope')
    def _onchange_tracking_scope(self):
        if self.tracking_scope == 'all':
            self.tracked_field_ids = [(5, 0, 0)]
            self.excluded_field_ids = [(5, 0, 0)]
        elif self.tracking_scope == 'tracked':
            self.excluded_field_ids = [(5, 0, 0)]
        elif self.tracking_scope == 'excluded':
            self.tracked_field_ids = [(5, 0, 0)]

    @api.constrains('tracked_field_ids', 'excluded_field_ids')
    def _check_fields(self):
        for rule in self:
            if rule.tracked_field_ids and rule.excluded_field_ids:
                raise models.ValidationError(
                    'You cannot set both Tracked Fields and Excluded Fields. '
                    'Please choose one scope.'
                )

    def _get_tracked_users(self):
        """Get the list of users that should be tracked concisely."""
        self.ensure_one()
        from odoo.tools.safe_eval import safe_eval

        domain = [('share', '=', False)]
        if self.user_selection_type == 'specific':
            return self.user_ids
        elif self.user_selection_type == 'exclude':
            return self.env['res.users'].search(domain) - self.user_ids
        elif self.user_selection_type == 'group':
            return self.group_ids.mapped('users').filtered(lambda u: not u.share)

        if self.user_domain and self.user_domain != '[]':
            try:
                domain += safe_eval(self.user_domain)
            except Exception:
                pass
        return self.env['res.users'].search(domain)

    def _should_track_user(self, user):
        """Check if a specific user should be tracked including domain check."""
        self.ensure_one()
        uid = user.id
        if uid == 1: return False  # Never track OdooBot/Superuser unless specifically needed

        # User Selection Check
        match = True
        if self.user_selection_type == 'specific':
            match = uid in self.user_ids.ids
        elif self.user_selection_type == 'exclude':
            match = uid not in self.user_ids.ids
        elif self.user_selection_type == 'group':
            match = any(uid in g.users.ids for g in self.group_ids)

        if not match: return False

        # Domain Check
        if self.user_domain and self.user_domain != '[]':
            from odoo.tools.safe_eval import safe_eval
            try:
                domain = safe_eval(self.user_domain)
                return uid in self.env['res.users'].search(domain).ids
            except Exception:
                return False  # Default to not tracking if domain is broken

        return True

    @api.depends('user_selection_type', 'user_ids', 'group_ids', 'user_domain')
    def _compute_user_count(self):
        """Compute the number of users affected by this rule accurately."""
        for rule in self:
            rule.user_count = len(rule._get_tracked_users())

    def write(self, vals):
        """
        If track_session is toggled ON, proactively create a session record for
        the current user to show immediate feedback.
        """
        res = super().write(vals)
        if 'track_session' in vals and vals['track_session']:
            # Call centralized session logic
            self.env['audit.session'].sudo().get_or_create_session()
        return res

    def action_cleanup_logs(self):
        """Manually clean up ALL audit logs linked to this rule."""
        self.ensure_one()
        logs = self.env['audit.log'].sudo().search([('model_id', '=', self.model_id.id)])
        count = len(logs)
        if logs:
            logs.unlink()
            _logger.info("Audit Manual Cleanup: Removed %d log(s) for rule '%s'.", count, self.name)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cleanup Complete',
                'message': f"Successfully removed {count} log(s) for rule '{self.name}'.",
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _cron_audit_log_retention(self):
        """Scheduled action to clean up expired logs based on per-rule settings."""
        rules = self.search([('has_retention', '=', True), ('retention_days', '>', 0)])
        for rule in rules:
            limit_date = fields.Datetime.subtract(fields.Datetime.now(), days=rule.retention_days)
            logs = self.env['audit.log'].sudo().search([
                ('model_id', '=', rule.model_id.id),
                ('create_date', '<', limit_date)
            ])
            if logs:
                _logger.info("Audit: Cleaned up %d expired logs for rule %s", len(logs), rule.name)
                logs.unlink()