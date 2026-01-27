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
from ast import literal_eval
from lxml import etree

from odoo import api, Command, fields, models

view_arch = """
                    <xpath expr="//header" position="after">
                        <div class="alert alert-warning" role="alert" invisible="not approval_request_id">
                            <p>This Record Needs to be approved</p>
                            <div class="d-flex align-items-center">
                                <field name="approval_request_id" invisible="1"/>
                                <field name="allow_comment" invisible="1"/>
                                <field name="approval_transferred" invisible="1"/>
                                <field name="server_trigger" invisible="1"/>
                                <field name="can_approve" invisible="1"/>
                            </div>
                            <div class="mt-2">
                                <div class="form-group">
                                    <field name="approval_comment" invisible="not allow_comment" placeholder="Write your comment here..." class="form-control"/>
                                </div>
                            </div>
                            <div class="d-flex gap-2 mt-3">
                                <button name="action_approve" type="object" string="Accept" class="btn-icon btn-success" invisible="not can_approve"/>
                                <button name="action_reject" type="object" string="Reject" class="btn-icon btn-danger" invisible="not can_approve"/>
                                <button name="action_forward" type="object" string="Forward" invisible="not(approval_transferred and can_approve)" class="btn-icon btn-info"/>
                            </div>
                        </div>
                    </xpath>
                    """
view_arch_request = f"""
                    <xpath expr="//header" position="inside">
                        <field name="show_request_button" invisible="1"/>
                        <button name="action_request_approval" string="Request Approval" invisible="not (show_request_button or server_trigger)" type="object"/>
                    </xpath>"""
button_box_view = f"""<xpath expr="//div[@name='button_box']" position="inside">
                    <button name="action_view_approval_request"
                        class="oe_stat_button"
                        icon="fa-check"
                        invisible="approval_count == 0"
                        type="object">
                        <field name="approval_count" widget="statinfo" string="Approvals"/>
                    </button>
                </xpath>"""
approval_view = f"""<xpath expr="//notebook" position="inside">
                    <page name="approval_rules" string="Approvals" invisible="not approval_rule_ids">
                        <field name="approval_rule_ids" readonly="1">
                            <tree default_order="sequence_order asc">
                                <field name="sequence_order" width="20px"/>
                                <field name="name"/>
                                <field name="state_from_id"/>
                                <field name="state_to_id"/>
                            </tree>
                        </field>
                    </page>
                    </xpath>"""


class ApprovalRule(models.Model):
    _name = "approval.rule"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Approval rules"

    name = fields.Char(string="Name", required=True)
    model_id = fields.Many2one('ir.model', string="Model",
                               domain=lambda self: self._get_inherited_models(),
                               help="Select the model for which this approval rule applies.")
    state_value = fields.Char(string="State",
                              help="Technical name of the state field in the selected model.")
    state_values_ids = fields.Many2many('ir.model.fields.selection')
    state_from_id = fields.Many2one('ir.model.fields.selection',
                                    string="State From",
                                    help="The state from which the transition begins.")
    state_to_id = fields.Many2one('ir.model.fields.selection',
                                  string="State To",
                                  help="The state to which the transition occurs.")
    user_type = fields.Selection(
        [('user', 'Based on User'), ('group', 'Based on Group'),
         ('related', 'Based on Related Users')], string="User Type",
        help="Specify how approvers are determined for this rule.")
    user_id = fields.Many2one('res.users',
                              help="Specific user who can approve the request.")
    group_id = fields.Many2one('res.groups',
                               help="Specific group whose members can approve the request.")
    related_user_id = fields.Many2one('ir.model.fields', string="Related User",
                                      help="Field in the selected model that determines the related users for approval.")
    definition_type = fields.Selection(
        [('domain', 'Domain'), ('server_action', 'Server Action')],
        string="Definition Type", required=True,
        help="Define whether this rule is based on a domain or a server action.")
    model_select = fields.Char(string="Model Selected",
                               related='model_id.model')
    domain = fields.Char(string="Domain", required=True, default='[]',
                         help="Domain condition that set for this rule.")
    server_action_id = fields.Many2one('ir.actions.server',
                                       string="Server Action",
                                       help="Server action to execute when the rule is triggered.")
    state = fields.Selection([('enable', 'Enable'), ('disable', 'Disable')],
                             default='disable', store=True)
    is_sequenced = fields.Boolean(string="Approve in Sequence order")
    sequence_order = fields.Integer(string="Sequence")
    transferred = fields.Boolean(string="Can be Transferred")
    email_notification = fields.Boolean(string="Email Notification")
    allow_comment = fields.Boolean(string="Allow Comment")
    notify_on_request = fields.Boolean(string="Notify on Request")
    notify_on_approve = fields.Boolean(string="Notify on Approval")
    notify_on_reject = fields.Boolean(string="Notify on Rejection")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one("res.company", required=True,
                                 default=lambda self: self.env.company,
                                 help="Current company", tracking=True)
    approver_ids = fields.Many2many('res.users', string='Approvers',
                                    help="The person who approves the request", )
    admin_users = fields.Json()

    @api.model
    def _get_inherited_models(self):
        """
            Retrieves the IDs of models that inherit from the 'check.approval' model.
            """
        approval_model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'check.approval')]).id
        models_details = self.env['ir.model.inherit'].sudo().search(
            [('parent_id', '=', approval_model_id)]).model_id
        return [('id', 'in', models_details.ids)]

    @api.onchange('user_type')
    def _onchange_user_type(self):
        if self.user_type == 'user':
            self.group_id = False
            self.related_user_id = False
        elif self.user_type == 'group':
            self.user_id = False
            self.related_user_id = False
        elif self.user_type == 'related':
            self.user_id = False
            self.group_id = False

    @api.onchange('state_value', 'model_id')
    def _onchange_state_value(self):
        """
            Updates 'state_values_ids' and 'model_select' based on the selected
            'state_value' and 'model_id'. Handles both 'selection' and 'many2one'
            field types, dynamically linking or creating related state values.
            """
        if not self.state_value:
            self.sudo().write({
                'state_values_ids': [Command.clear()],
                'state_from_id': [Command.clear()],
                'state_to_id': [Command.clear()]
            })
            return
        if self.state_value or self.model_id:
            status_bar = self.env['ir.model.fields'].search(
                [('model_id', '=', self.model_id.id),
                 ('name', '=', self.state_value)])
            if status_bar.ttype == 'selection':
                state_values = status_bar.selection_ids.ids
                if self.state_value:
                    self.sudo().write({
                        'state_values_ids': [Command.clear()]
                    })
                self.sudo().write({
                    'state_values_ids': [Command.link(rec) for rec in
                                         state_values]
                })
            elif status_bar.ttype == 'many2one':
                state_values = self.env[status_bar.relation].search([])
                if state_values:
                    self.sudo().write({
                        'state_values_ids': [Command.clear()]
                    })
                    mapped_selection_ids = []
                    stage_field = self.env['ir.model.fields'].search(
                        [('model', '=', self._name),
                         ('name', '=', 'x_stage_id')])
                    for rec in state_values:
                        selection_record = self.env[
                            'ir.model.fields.selection'].sudo().search([
                            ('value', '=', str(rec.id)),
                            ('field_id', '=', stage_field.id)
                        ], limit=1)
                        if not selection_record:
                            selection_record = self.env[
                                'ir.model.fields.selection'].sudo().create({
                                'value': rec.id,
                                'name': rec.name,
                                'field_id': stage_field.id,
                                'sequence': rec.id,
                            })
                        mapped_selection_ids.append(selection_record.id)
                    self.sudo().write({
                        'state_values_ids': [Command.link(sel_id) for sel_id in
                                             mapped_selection_ids]
                    })

    @api.onchange('model_id', 'user_type')
    def _onchange_model_id(self):
        if self.model_id:
            admin_group = self.env['ir.model.access'].search([
                ('model_id', '=', self.model_id.id),
                ('perm_write', '=', True),
                ('perm_create', '=', True),
                ('perm_unlink', '=', True),
            ]).mapped('group_id')
            if self.user_type == 'user':
                admin_users = admin_group.mapped('users')
                self.admin_users = admin_users.ids if admin_users else []
            elif self.user_type == 'group':
                self.admin_users = admin_group.ids if admin_group else []
        else:
            self.admin_users = []

    @api.model
    def create(self, vals):
        """
        Overrides create to dynamically add approval-related UI elements to the
        associated model's form view if not already present.
        """
        record = super(ApprovalRule, self).create(vals)
        approvers = []
        if record.user_type == 'user':
            approvers.append(record.user_id.id)
        elif record.user_type == 'group' and record.group_id:
            group_users = record.group_id.users
            approvers.extend(group_users.ids)
        if record.model_id:
            model_name = record.model_id.model
            approval_request_form = self.env['ir.ui.view'].search(
                [('name', '=', f'view_{record.model_id.model}_approval_form')])
            if not approval_request_form:
                form_view = self.env['ir.ui.view'].search([
                    ('model', '=', model_name),
                    ('type', '=', 'form'),
                    ('mode', '=', 'primary')
                ], limit=1)
                if form_view:
                    view = form_view.arch_db
                    tree = etree.fromstring(view)
                    header = tree.xpath("//header")
                    notebook = tree.xpath("//notebook")
                    button_box = tree.xpath("//div[@name='button_box']")

                    if not header:
                        header = etree.Element("header")
                        tree.insert(0, header)
                        updated_arch = etree.tostring(tree, encoding='unicode',
                                                      pretty_print=True)
                        form_view.write({'arch_db': updated_arch})
                    self.create_view(record, model_name, form_view, view_arch,
                                     "approval_data")
                    self.create_view(record, model_name, form_view,
                                     view_arch_request, "approval_data_button")
                    if button_box:
                        self.create_view(record, model_name, form_view,
                                         button_box_view,
                                         "approval_requests")
                    if notebook:
                        self.create_view(record, model_name, form_view,
                                         approval_view,
                                         "approvals")
        return record

    @api.model
    def write(self, vals):
        """
        Overrides write to handle updates to approval-related UI elements when
        the model_id changes.
        """
        if 'model_id' in vals:
            record = self
            old_model_id = record.model_id.id
            new_model_id = vals.get('model_id')
            if old_model_id != new_model_id:
                model_name = self.env['ir.model'].sudo().search(
                    [('id', '=', new_model_id)], limit=1).model
                approval_request_form = self.env['ir.ui.view'].search(
                    [('name', '=', f'view_{model_name}_approval_form')])

                if not approval_request_form:
                    form_view = self.env['ir.ui.view'].search([
                        ('model', '=', model_name),
                        ('type', '=', 'form'),
                        ('mode', '=', 'primary')
                    ], limit=1)
                    if form_view:
                        view = form_view.arch_db
                        tree = etree.fromstring(view)
                        header = tree.xpath("//header")
                        notebook = tree.xpath("//notebook")
                        button_box = tree.xpath("//div[@name='button_box']")
                        if not header:
                            header = etree.Element("header")
                            tree.insert(0, header)
                            updated_arch = etree.tostring(tree,
                                                          encoding='unicode',
                                                          pretty_print=True)
                            form_view.write({'arch_db': updated_arch})
                        self.create_view(record, model_name, form_view,
                                         view_arch, "approval_data")
                        self.create_view(record, model_name, form_view,
                                         view_arch_request,
                                         "approval_data_button")
                        if button_box:
                            self.create_view(record, model_name, form_view,
                                             button_box_view,
                                             "approval_requests")
                        if notebook:
                            self.create_view(record, model_name, form_view,
                                             approval_view, "approvals")
        return super(ApprovalRule, self).write(vals)

    def action_enable(self):
        """
            Sets the state of the record to 'enable'.
            """
        self.state = 'enable'

    def action_disable(self):
        """
            Sets the state of the record to 'disable'.
            """
        self.state = 'disable'

    def refresh_dynamic_views(self):
        """Refresh dynamic approval views to match the latest `view_arch` template.

        This updates existing dynamically created "approval_data" views for all
        models linked to approval rules, ensuring recent template changes are applied.

        Can be run manually, via a Server Action, scheduled action, or custom trigger.
        Safe to run multiple times—only updates existing views.
        """
        for rule in self.sudo():
            if not rule.model_id:
                continue
            model_name = rule.model_id.model
            data_xml = self.env['ir.model.data'].sudo().search([
                ('module', '=', rule._module),
                ('name', '=', f'view_{model_name}_approval_data'),
                ('model', '=', 'ir.ui.view'),
            ], limit=1)
            if data_xml:
                view = self.env['ir.ui.view'].sudo().browse(data_xml.res_id)
                if view and view.exists():
                    view.write({'arch': view_arch})

    def create_view(self, record, model_name, form_view, arch, view_name):
        """
        Creates a dynamic UI view for approval-related elements and registers it in
        model data for the specified model.
        """
        view = self.env['ir.ui.view'].create({
            'name': f'view_{record.model_id.model}_approval_form',
            'type': 'form',
            'model': model_name,
            'inherit_id': form_view.id,
            'mode': 'extension',
            'arch': arch
        })
        self.env['ir.model.data'].create({
            'name': f'view_{record.model_id.model}_{view_name}',
            'model': 'ir.ui.view',
            'module': self._module,
            'res_id': view.id,
            'noupdate': True,
        })

    @api.model
    def _domain(self):
        """
            Evaluates and returns the domain as a Python expression.
            """
        return literal_eval(self.domain)