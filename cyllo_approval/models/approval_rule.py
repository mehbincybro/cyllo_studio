# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ApprovalRule(models.Model):
    _name = 'approval.rule'
    _description = 'Approval Rule'

    # ------------------------------------------------------------
    # BASIC FIELDS
    # ------------------------------------------------------------
    name = fields.Char(required=True)
    model_id = fields.Many2one('ir.model', string='Target Model')
    model_name = fields.Char(related='model_id.model', store=True)

    request_ids = fields.One2many('approval.request', 'rule_id')

    rule_type = fields.Selection([
        ('button', 'Button'),
        ('state', 'State Change'),
        ('server', 'Server Action'),
    ], required=True, default='button')

    # ------------------------------------------------------------
    # STATE FIELDS - IMPROVED APPROACH
    # ------------------------------------------------------------
    state_field_id = fields.Many2one(
        'ir.model.fields',
        string='State Field',
        domain="[('model_id', '=', model_id), ('name', 'in', ['state', 'stage_id'])]"
    )
    state_field_name = fields.Char(related='state_field_id.name', store=True)
    state_field_type = fields.Selection(
        related='state_field_id.ttype',
        string='Field Type'
    )
    state_field_relation = fields.Char(
        related='state_field_id.relation',
        string='Related Model',
        help='For many2one fields, this is the comodel'
    )

    # For selection-type states
    state_to_selection_id = fields.Many2one(
        'ir.model.fields.selection',
        string="Target State (Selection)",
        domain="[('field_id', '=', state_field_id)]"
    )

    # For many2one states (stage_id, etc.)
    state_values_m2o_ids = fields.Many2many(
        'approval.state.value',
        string='Available State Values',
        compute='_compute_state_values_m2o',
        store=False
    )
    state_to_m2o_value_id = fields.Many2one(
        'approval.state.value',
        string="Target State (Stage)",
        domain="[('id', 'in', state_values_m2o_ids)]"
    )

    # ------------------------------------------------------------
    # APPROVERS
    # ------------------------------------------------------------
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    group_id = fields.Many2one('res.groups', string='Approver Group')

    # ------------------------------------------------------------
    # TRIGGER FIELDS
    # ------------------------------------------------------------
    button_id = fields.Many2one('ir.buttons',
                                domain="[('model_id','=',model_id)]")
    server_action_id = fields.Many2one(
        'ir.actions.server',
        domain="[('model_id','=',model_id)]"
    )

    sequence = fields.Integer(default=1)
    domain = fields.Char(default='[]')

    is_comment = fields.Boolean('Allow Comment')
    is_email = fields.Boolean('Notify Email')
    is_email_request = fields.Boolean('Notify on Request')
    is_email_approve = fields.Boolean('Notify on Approval')
    is_email_reject = fields.Boolean('Notify on Rejection')

    @api.constrains('model_id')
    def _constraint_model_id(self):
        if not self.model_id:
            raise ValidationError('Please choose a Model.')

    # ------------------------------------------------------------
    # COMPUTE AVAILABLE STATE VALUES FOR MANY2ONE
    # ------------------------------------------------------------
    @api.depends('state_field_id', 'state_field_relation')
    def _compute_state_values_m2o(self):
        """Dynamically fetch all records from the related model."""
        for rec in self:
            rec.state_values_m2o_ids = False

            if not rec.state_field_relation:
                continue

            # Get all records from the comodel
            try:
                comodel = self.env[rec.state_field_relation]
                records = comodel.search([])

                # Create or update approval.state.value records
                StateValue = self.env['approval.state.value']
                value_ids = []

                for record in records:
                    display_name = record.display_name or record.name
                    value = StateValue.search([
                        ('res_model', '=', rec.state_field_relation),
                        ('res_id', '=', record.id),
                    ], limit=1)

                    if not value:
                        value = StateValue.create({
                            'res_model': rec.state_field_relation,
                            'res_id': record.id,
                            'name': display_name,
                        })
                    else:
                        # Update name in case it changed
                        value.write({'name': display_name})

                    value_ids.append(value.id)

                rec.state_values_m2o_ids = value_ids

            except Exception as e:
                _logger.warning(
                    f"Failed to load state values for {rec.state_field_relation}: {e}")
                rec.state_values_m2o_ids = False

    # ------------------------------------------------------------
    # ONCHANGE: CLEAR STATE VALUES WHEN FIELD CHANGES
    # ------------------------------------------------------------
    @api.onchange('state_field_id')
    def _onchange_state_field_id(self):
        """Clear state values when changing the state field."""
        self.state_to_selection_id = False
        self.state_to_m2o_value_id = False

    # ------------------------------------------------------------
    # CLEAN EMAIL LOGIC
    # ------------------------------------------------------------
    @api.onchange('is_email')
    def _onchange_is_email(self):
        if not self.is_email:
            self.is_email_request = False
            self.is_email_approve = False
            self.is_email_reject = False

    @api.model_create_multi
    def create(self, vals_list):
        """Patch the target model's method when a rule is created."""
        records = super().create(vals_list)
        for rec in records:
            rec._patch_method()
            rec._create_dynamic_fields()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in
               ['model_id', 'rule_type', 'button_id', 'state_field_id']):
            for rec in self:
                rec._patch_method()
                rec._create_dynamic_fields()
        return res

    def _create_dynamic_fields(self):
        """Create required fields on target model if missing."""
        IrModelFields = self.env['ir.model.fields']
        model_fields = self.env[self.model_id.model]._fields
        fields_to_create = [
            {
                'name': 'x_approval_request_ids',
                'field_description': 'Approval Requests',
                'ttype': 'many2many',
                'relation': 'approval.request',
            },
            {
                'name': 'x_is_state_approval',
                'field_description': 'Is State Approval',
                'ttype': 'boolean',
            },
            {
                'name': 'x_approval_comment',
                'field_description': 'Approval Comment',
                'ttype': 'text',
            },
            {
                'name': 'x_current_approver_id',
                'field_description': 'Current Approver',
                'ttype': 'many2one',
                'relation': 'res.users',
            },
            {
                'name': 'x_current_group_id',
                'field_description': 'Current Approver Group',
                'ttype': 'many2one',
                'relation': 'res.groups',
            },
            {
                'name': 'x_approval_request_count',
                'field_description': 'Approval Request Count',
                'ttype': 'integer',
            },
        ]

        for field_data in fields_to_create:
            if field_data['name'] not in model_fields:
                IrModelFields.create({
                    **field_data,
                    'model_id': self.model_id.id,
                })

        self.env['ir.ui.view']._invalidate_cache()

    @api.model
    def _register_hook(self):
        """Re-apply patches for all existing rules at module load."""
        res = super()._register_hook()
        rules = self.sudo().search([])
        for rule in rules:
            try:
                rule._patch_method()
            except Exception as e:
                _logger.warning("Failed to patch rule %s: %s", rule.name, e)
        return res

    def _patch_method(self):
        model = self.env[self.model_name]
        if self.rule_type == 'state':
            return self._patch_state_change(model)
        elif self.rule_type == 'button':
            return self._patch_button_method(model)

    def _get_target_state_value(self):
        """Get the target state value regardless of field type."""
        self.ensure_one()
        if self.state_field_type == 'selection':
            return self.state_to_selection_id.value
        elif self.state_field_type == 'many2one':
            return self.state_to_m2o_value_id.res_id if self.state_to_m2o_value_id else None
        return None

    @api.model
    def _get_ordered_rules(self, model_name, trigger_type,
                           state_field_name=None, trigger_value=None):
        """Get rules matching the trigger, ordered by sequence."""
        domain = [
            ('model_name', '=', model_name),
            ('rule_type', '=', trigger_type),
        ]

        if trigger_type == 'button':
            domain.append(('button_id', '=', trigger_value))
        else:  # state change
            domain.append(('state_field_name', '=', state_field_name))

            # Handle both selection and many2one state fields safely
            # trigger_value can be a string (selection) or int (ID)
            state_domain = [('state_to_selection_id.value', '=', trigger_value)]

            # Only search by res_id if trigger_value is numeric (Many2one)
            # This avoids ValueError when comparing string to integer field
            if isinstance(trigger_value, int) or (isinstance(trigger_value, str) and trigger_value.isdigit()):
                state_domain = ['|'] + state_domain + [('state_to_m2o_value_id.res_id', '=', int(trigger_value))]

            domain += state_domain

        return self.search(domain).sorted(lambda r: r.sequence)

    def _patch_button_method(self, model):
        button = self.button_id
        button_id = button.id
        method_name = button.name

        if not hasattr(model, method_name):
            raise ValidationError(
                f"Method '{method_name}' not found on model '{self.model_name}'.")

        if getattr(model.__class__, f"_approval_patched_{method_name}", False):
            return

        original_method = getattr(model.__class__, method_name)

        def intercepted_method(record, *args, **kwargs):
            Rule = record.env['approval.rule'].sudo()
            rules = Rule._get_ordered_rules(
                model_name=record._name,
                trigger_type='button',
                trigger_value=button_id
            )

            if rules:
                Request = record.env['approval.request'].sudo()

                for rule in rules:
                    if not record.sudo().filtered_domain(
                            literal_eval(rule.domain)):
                        continue

                    request = rule.request_ids.filtered(
                        lambda x: x.res_id == record.id)
                    if request:
                        existing = request.sorted("id", reverse=True)[0]

                        if existing.state == 'approved':
                            continue

                        if existing.state == 'pending':
                            raise ValidationError(
                                _("Approval '%s' (sequence %s) is pending.")
                                % (rule.name, rule.sequence)
                            )

                        if existing.state == 'rejected' or existing.is_used:
                            pass

                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'approval.request.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_rule_id': rule.id,
                            'default_res_model': record._name,
                            'default_res_id': record.id,
                        },
                    }

                result = original_method(record, *args, **kwargs)
                return result

            return original_method(record, *args, **kwargs)

        setattr(model.__class__, method_name, intercepted_method)
        setattr(model.__class__, f"_approval_patched_{method_name}", True)

    def _patch_state_change(self, model):
        if getattr(model.__class__, "_approval_patched_write", False):
            return

        original_write = model.__class__.write

        def intercepted_write(records, vals):
            Rule = records.env['approval.rule'].sudo()

            # Get the state field name dynamically from rules for this model
            state_rules_for_model = Rule.search([
                ('model_name', '=', records._name),
                ('rule_type', '=', 'state'),
            ])

            if state_rules_for_model:
                unique_state_fields = state_rules_for_model.mapped('state_field_name')
                records_to_process = records
                
                for state_field_name in unique_state_fields:
                    new_state = vals.get(state_field_name)
                    if new_state is None:
                        continue

                    # Filter records that need to be audited for this state change
                    for rec in records_to_process:
                        # Get rules for this specific state field and value
                        rules = Rule._get_ordered_rules(
                            model_name=records._name,
                            trigger_type='state',
                            state_field_name=state_field_name,
                            trigger_value=new_state
                        )

                        if not rules:
                            continue

                        Request = rec.env['approval.request'].sudo()
                        next_rule_to_approve = None

                        for rule in rules:
                            if not rec.sudo().filtered_domain(
                                    literal_eval(rule.domain)):
                                continue

                            existing = Request.search([
                                ('rule_id', '=', rule.id),
                                ('res_model', '=', rec._name),
                                ('res_id', '=', rec.id),
                            ], order="id desc", limit=1)

                            if existing and existing.state == 'approved':
                                continue

                            if existing and existing.state == 'pending':
                                raise ValidationError(
                                    _("Approval '%s' (sequence %s) pending.")
                                    % (rule.name, rule.sequence)
                                )

                            next_rule_to_approve = rule
                            break

                        if next_rule_to_approve:
                            if not rec.x_is_state_approval:
                                rec.sudo().write({
                                    'x_is_state_approval': True,
                                })
                                # Exclude this record from the final original_write call
                                records_to_process = records_to_process - rec
                                continue 

                            if rec.x_is_state_approval:
                                raise ValidationError(
                                    _("Approval required for '%s' (sequence %s). Use 'Request Approval'.")
                                    % (next_rule_to_approve.name,
                                       next_rule_to_approve.sequence)
                                )

                        # If all rules are approved for this record and this state field, we proceed.
                        # However, we need to handle the 'done' state for requests.
                        rule_ids = rules.mapped('id')
                        if rule_ids:
                            Request.search([
                                ('rule_id', 'in', rule_ids),
                                ('res_model', '=', rec._name),
                                ('res_id', '=', rec.id),
                                ('state', '=', 'approved'),
                            ]).sudo().write({'state': 'done'})
                
                # If some records are left, update them
                if records_to_process:
                    return original_write(records_to_process, vals)
                return True

            return original_write(records, vals)

        setattr(model.__class__, 'write', intercepted_write)
        setattr(model.__class__, "_approval_patched_write", True)


class ApprovalStateValue(models.Model):
    """Helper model to represent many2one state values like ir.model.fields.selection"""
    _name = 'approval.state.value'
    _description = 'Approval State Value (Many2one)'
    _rec_name = 'name'

    res_model = fields.Char(string='Model', required=True, index=True)
    res_id = fields.Integer(string='Record ID', required=True, index=True)
    name = fields.Char(string='Display Name', required=True)

    _sql_constraints = [
        ('unique_model_id', 'UNIQUE(res_model, res_id)',
         'Only one state value per model record allowed!')
    ]

    def name_get(self):
        """Display the actual record name in the dropdown"""
        return [(rec.id, rec.name) for rec in self]