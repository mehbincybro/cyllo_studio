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

import re
import secrets

from odoo import _, api, exceptions, fields, models


class NodeStruct(models.Model):
    _name = 'node.struct'

    name = fields.Char()
    work_auto_id = fields.Many2one('work.auto', ondelete='cascade')
    reused_work_auto_id = fields.Many2one('work.auto', string="Reusable Automation", ondelete='set null')
    reused_variable = fields.Json("Reusable Record Variable")
    code = fields.Text("Code")
    label = fields.Char()
    type = fields.Selection(selection=[
        ("trigger", "Trigger"),
        ("model", "Model"),
        ("node", "Node"),
        ("action", "Action"),
        ("action_to_do", "Action to do")
    ])
    trigger_type = fields.Char("Trigger Type")
    ttype = fields.Char("UI Trigger Label")
    model_id = fields.Many2one('ir.model')
    used_variables = fields.Json("Used Variables")
    condition_tree_value = fields.Json("condition_tree_value")
    else_setup_code = fields.Text(string="Else Setup Code")

    # Warning block fields
    warning = fields.Selection(
        string="Warning",
        selection=[('UserError', 'User Error'),
                   ('AccessError', 'Access Error'),
                   ('AccessDenied', 'Access Denied'),
                   ('ValidationError', 'Validation Error'),
                   ('MissingError', 'Missing Error'),
        ])
    warning_text = fields.Char(string="Warning Text")
    model_name = fields.Char("Model Name", related="model_id.model")
    warning_type = fields.Char(string="Warning Type", default="error")
    notification_type = fields.Char(string="Notification Type")
    notification_title = fields.Char(string="Notification Title")
    notification_sticky = fields.Boolean(string="Sticky Notification", default=False)

    # Search block fields
    search_domain = fields.Char()
    search_limit = fields.Integer()
    search_order = fields.Selection(
        selection=[('asc', 'ASC'), ('desc', 'DESC')])
    search_order_field = fields.Char()
    search_domain_tree = fields.Json("Tree")
    search_variable = fields.Json("Variable")

    # Loop block fields
    loop_source_type = fields.Selection(
        selection=[
            ('field', 'Record Field'),
            ('variable', 'Variable'),
        ],
        string="Loop Source Type",
        default='field'
    )
    loop_collection = fields.Char(
        string="Loop Collection",
        help="Field name (e.g. order_line) or variable name to iterate over."
    )
    loop_variable_name = fields.Char(
        string="Loop Variable Name",
        help="Name of the loop iteration variable (e.g. current_line)."
    )

    # Create block fields
    create_name = fields.Char()
    create_model_field_value = fields.Char(default="[]")
    create_req_fields_values = fields.Json("createFields")
    create_tree_fields_values = fields.Json("createTreeFields")
    create_required_field = fields.Json("createRequiredField")

    # Write block fields
    write_field_value = fields.Char(default="[]")
    write_selected_record = fields.Json("Record")

    # Function call block fields
    function_name = fields.Json("Function Name")
    function_type = fields.Char(string="Function Type", default="server_action")
    function_record = fields.Json()
    function_args = fields.Json("Function Arguments", default={})

    # Variables block fields
    variable_name = fields.Char("Variable Name")
    variable_type = fields.Selection(
        string="Variable Type",
        selection=[
            ('string', 'String'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('datetime', 'DateTime'),
            ('boolean', 'Boolean'),
            ('dynamic', 'Dynamic Values'),
        ])
    variable_value = fields.Char(string="Variable Value")
    code_return_type = fields.Selection(
        string="Code Return Type",
        selection=[
            ('string', 'String'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('datetime', 'DateTime'),
            ('boolean', 'Boolean'),
            ('record', 'Record'),
            ('recordset', 'RecordSet'),
        ])

    # loop block fields
    loop_source_type = fields.Selection(
        selection=[('field', 'Record Field'), ('variable', 'Variable')],
        string="Source Type", default='field')
    loop_collection = fields.Char(string="Collection")
    loop_variable_name = fields.Char(string="Loop Variable Name")


    # Code block fields
    code_code = fields.Char(string="Code")

    # Mail block fields
    mailCustomData = fields.Json(string="Mail Custom Data")
    mail_record = fields.Json(string="MailRecord")
    mail_template = fields.Json(string="MailTemplate")
    mail_isTemplate = fields.Json(string="MailIsTemplate")
    mail_from = fields.Json(string="MailFrom")
    mail_to = fields.Json(string="MailTo")
    mail_subject = fields.Json(string="MailSubject")
    mail_body = fields.Json(string="MailBody")

    # SMS block fields
    sms_record = fields.Json(string="sms record")
    sms_template = fields.Json(string="sms template")
    sms_partner_ids = fields.Json(string="Recipients")
    recipients = fields.Json(string='reciep')
    sms_isTemplate = fields.Boolean(string="SMSIsTemplate")
    sms_message = fields.Char(string="smsMessage")

    # WhatsApp block fields
    wa_record = fields.Json(string="WA Record Variable")
    wa_is_template = fields.Boolean(string="Use WA Template", default=True)
    wa_template = fields.Json(string="WA Template")
    wa_partner_path = fields.Json(string="WA Partner Path")
    wa_partner_source = fields.Selection(
        [('customer', 'Customer'), ('other', 'Other')],
        string="WA Partner Source",
        default='customer',
    )
    wa_other_partner = fields.Json(string="WA Other Partner")
    wa_free_message = fields.Char(string="WA Free-form Message")
    wa_attachment_mode = fields.Selection(
        [
            ('none', 'No Attachment'),
            ('static', 'Static File(s)'),
            ('auto', 'Auto-generate from Record'),
        ],
        string="WA Attachment Mode",
        default='none',
    )
    wa_static_attachment_ids = fields.Many2many(
        'ir.attachment',
        'node_struct_wa_attachment_rel',
        'node_struct_id',
        'attachment_id',
        string="WA Static Attachments",
    )
    wa_auto_report_id = fields.Many2one(
        'ir.actions.report',
        string="WA Auto Report",
        ondelete='set null',
    )

    # Window block fields
    window_action_id = fields.Many2one(
        'ir.actions.act_window',
        string="Window Action",
        ondelete='set null',
        help="The act_window action to open when this node executes.",
    )
    window_view_type = fields.Selection(
        selection=[
            ('list', 'List'),
            ('form', 'Form'),
            ('kanban', 'Kanban'),
            ('calendar', 'Calendar'),
            ('pivot', 'Pivot'),
            ('graph', 'Graph'),
            ('activity', 'Activity'),
        ],
        string="View Type",
        default='list',
    )
    window_target = fields.Selection(
        selection=[
            ('current', 'Current'),
            ('new', 'New Tab / Dialog'),
            ('fullscreen', 'Fullscreen'),
            ('inline', 'Inline'),
        ],
        string="Target",
        default='current',
    )
    window_domain = fields.Char(
        string="Domain Filter",
        help="Optional domain expression to restrict records, e.g. [('state','=','done')]",
    )
    window_context = fields.Char(
        string="Context",
        help="Optional context dict to pass to the window action, e.g. {'default_partner_id': 1}",
    )

    # Webhook block fields
    webhook_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE')
    ], string="Webhook Method", default='POST')
    webhook_url = fields.Char(string="Webhook URL")
    webhook_headers = fields.Char(string="Headers (JSON)", default='{"Content-Type": "application/json"}')
    webhook_payload = fields.Text(string="Payload (JSON)")
    webhook_actions = fields.Json(string="Webhook Response Actions")
    webhook_secret_token = fields.Char(
        string="Webhook Secret Token",
        copy=False,
        index=True,
        help="URL-safe random token that uniquely identifies this webhook receiver endpoint."
             " Auto-generated on record creation. Regenerate to invalidate the old URL.",
    )
    # Try/Catch Scope node fields
    tc_error_handling_mode = fields.Selection([
        ('stop',                'Stop Workflow'),
        ('catch',               'Execute Catch Branch'),
        ('continue',            'Continue Workflow'),
        ('catch_then_continue', 'Execute Catch Branch Then Continue'),
    ], string="Error Handling Mode", default='catch')
    tc_catch_filters = fields.Json(
        string="Error Filters",
        help="List of exception class names to catch. Empty = catch all.",
    )
    tc_try_node_ids = fields.Many2many(
        'node.struct',
        'node_struct_tc_try_rel',
        'scope_id', 'child_id',
        string="TRY Branch Node IDs",
    )
    tc_catch_node_ids = fields.Many2many(
        'node.struct',
        'node_struct_tc_catch_rel',
        'scope_id', 'child_id',
        string="CATCH Branch Node IDs",
    )

    # Followers block fields
    isRemoveFollower = fields.Json()
    followers = fields.Json()
    follower_record = fields.Json()

    # Duplicate block fields
    duplicate_record = fields.Json(string="Duplicate Record Variable")
    duplicate_field_overrides = fields.Char(
        string="Field Overrides",
        default="[]",
        help="JSON list of {path, value, selectionType} to override on the copy"
    )
    duplicate_result_variable = fields.Char(
        string="Result Variable Name",
        help="Optional variable name to store the duplicated record(s) for use in downstream nodes"
    )

    # TryCatch block fields
    try_catch_error_variable = fields.Char(
        string="Error Variable Name",
        default="error",
        help="Python variable name that will hold the caught exception object.",
    )
    try_catch_error_types = fields.Char(
        string="Exception Types",
        default="Exception",
        help="Comma-separated exception class names to catch, e.g. 'UserError, ValidationError'.",
    )

    # Approval block fields
    approval_rule_type = fields.Selection([
        ('button', 'Button Click'),
        ('server', 'Server Action'),
        ('state', 'State Change'),
    ], string="Trigger Rule Type", default='button')
    approval_button_method = fields.Char(string="Button Method")
    approval_server_action_id = fields.Many2one('ir.actions.server', string="Server Action")
    approval_state_field_id = fields.Many2one('ir.model.fields', string="State Field")
    approval_state_to_selection_id = fields.Many2one('ir.model.fields.selection', string="Target State Selection")
    approval_state_to_m2o_value_id = fields.Integer(string="Target State M2O ID")

    approval_approver_type = fields.Selection(
        selection=[
            ('user', 'Specific User'),
            ('group', 'User Group'),
            ('dynamic', 'Dynamic Field (e.g. record.manager_id)'),
        ],
        string="Approver Type",
        default='user',
    )
    approval_approver_id = fields.Many2one(
        'res.users',
        string="Approver User",
        ondelete='set null',
    )
    approval_approver_group_id = fields.Many2one(
        'res.groups',
        string="Approver Group",
        ondelete='set null',
    )
    approval_approver_field = fields.Char(
        string="Approver Field",
        help="Python expression resolving to a res.users record, e.g. record.user_id",
    )
    approval_subject = fields.Char(
        string="Approval Subject",
        default="Your Approval is Required",
    )
    approval_message = fields.Text(
        string="Approval Message",
        help="Message body sent to the approver. Supports Jinja2 placeholders.",
    )
    approval_notify_email = fields.Boolean(string="Notify by Email", default=True)
    approval_notify_inbox = fields.Boolean(string="Notify in Odoo Inbox", default=True)
    approval_expire_after = fields.Float(
        string="Expire After (hours)",
        default=0.0,
        help="Set > 0 to automatically expire the approval request after this many hours. "
             "0 means no expiry.",
    )
    approval_auto_rule = fields.Char(
        string="Auto-Approve Rule",
        help="Python expression. If it evaluates to True the approval is auto-approved, "
             "skipping the human step. Example: record.amount_total < 1000",
    )
    approval_result_variable = fields.Char(
        string="Result Variable Name",
        help="Optional variable name to store the approval status string "
             "('approved', 'rejected', 'timeout') for use in downstream nodes.",
    )

    # Activity block fields
    activity_record = fields.Json()
    activity_summary = fields.Char()
    activity_user = fields.Json()
    activity_deadline = fields.Json()
    activity_type = fields.Json()
    activity_is_google_meet = fields.Boolean(
        string="Create as Google Meet",
        default=False,
        help="When enabled and cyllo_google_meet is installed, a Google Meet "
             "calendar event is created automatically.",
    )
    activity_meet_offset_hours = fields.Float(
        string="Schedule After (hours)",
        default=1.0,
        help="Number of hours after the workflow trigger to schedule the meeting start.",
    )
    activity_meet_duration_hours = fields.Float(
        string="Meeting Duration (hours)",
        default=1.0,
        help="Duration of the meeting in hours.",
    )
    activity_meet_summary = fields.Char(
        string="Meeting Name",
        help="Meeting title for the calendar event. Defaults to the activity summary.",
    )
    activity_also_schedule_activity = fields.Boolean(
        string="Also Schedule Activity Reminder",
        default=True,
        help="When enabled, the workflow also creates the regular chatter activity reminder.",
    )
    activity_is_zoom_meet = fields.Boolean(
        string="Create as Zoom Meet",
        default=False,
        help="When enabled and cyllo_zoom is installed, a Zoom meeting calendar "
             "event is created automatically.",
    )
    activity_zoom_offset_hours = fields.Float(
        string="Schedule After (hours)",
        default=1.0,
        help="Number of hours after the workflow trigger to schedule the meeting start.",
    )
    activity_zoom_duration_hours = fields.Float(
        string="Meeting Duration (hours)",
        default=1.0,
        help="Duration of the Zoom meeting in hours.",
    )
    activity_zoom_summary = fields.Char(
        string="Meeting Name",
        help="Meeting title for the Zoom calendar event. Defaults to the activity summary.",
    )
    activity_also_schedule_activity_zoom = fields.Boolean(
        string="Also Schedule Activity Reminder",
        default=True,
        help="When enabled, the workflow also creates the regular chatter activity reminder.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to auto-generate a unique webhook secret token for every
        new node.struct record that does not already carry one.

        Args:
            vals_list (list[dict]): List of field-value dicts for new records.

        Returns:
            node.struct: The newly created recordset.
        """
        for vals in vals_list:
            if not vals.get('webhook_secret_token'):
                vals['webhook_secret_token'] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def action_regenerate_webhook_token(self):
        """
        Regenerate the webhook secret token for this node, invalidating the old
        Secret URL immediately.

        Called by the frontend "Regenerate" button via a JSON-RPC controller
        endpoint.  The caller is responsible for showing a confirmation dialog
        *before* invoking this method.

        Returns:
            dict: A dict containing:
                - ``token`` (str): The newly generated token.
                - ``url``   (str): The full new Secret URL (base_url + route).

        Raises:
            exceptions.UserError: If the record does not exist.
        """
        self.ensure_one()
        new_token = secrets.token_urlsafe(32)
        self.write({'webhook_secret_token': new_token})
        base_url = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('web.base.url', default='')
            .rstrip('/')
        )
        secret_url = f"{base_url}/cyllo_webhook/trigger/{new_token}"
        return {'token': new_token, 'url': secret_url}

    def save_data(self, data):
        """
        Save or update the node structure data.

        This method checks if the current record exists. If it doesn't, a new record is created with the provided data.
        If it exists, the method updates the existing record with the new data.

        Args:
            data (dict): The data to be saved or updated in the record.

        Returns:
            int: The ID of the saved or updated record.
        """
        struct_node_id = self or False
        if 'wa_static_attachment_ids' in data:
            raw_attachments = data.get('wa_static_attachment_ids') or []
            attachment_ids = []
            for item in raw_attachments:
                if isinstance(item, dict):
                    attachment_id = item.get('id')
                elif isinstance(item, (list, tuple)):
                    attachment_id = item[0] if item else False
                else:
                    attachment_id = item
                if attachment_id:
                    attachment_ids.append(attachment_id)
            data['wa_static_attachment_ids'] = [(6, 0, attachment_ids)]

        if 'wa_auto_report_id' in data and isinstance(data['wa_auto_report_id'], dict):
            data['wa_auto_report_id'] = data['wa_auto_report_id'].get('id') or False

        if not self:
            struct_node_id = self.create(data)
        else:
            self.write(data)
        return struct_node_id.id

    def create_editable_reuse_copy(self):
        """
            Create an editable copy of a reusable automation and link it to the node.

            This method allows a user to modify a reusable workflow without affecting
            the original one. It performs the following steps:

            - Ensures a reusable automation is selected.
            - Creates a duplicate of the selected reusable workflow.
            - Marks the copied workflow as non-reusable.
            - Updates the node's code to reference the newly copied workflow.
            - Updates the node fields to link the new workflow and reflect its name.

            Returns:
                dict: Dictionary containing details of the copied automation:
                      - id (int): ID of the copied workflow
                      - name (str): Name of the copied workflow
                      - label (str): Label updated in the node
                      - code (str): Updated code referencing the copied workflow

            Raises:
                ValidationError: If no reusable automation is selected.
            """
        self.ensure_one()
        if not self.reused_work_auto_id:
            raise exceptions.ValidationError(
                _("Please select a reusable automation before editing it.")
            )

        copied_automation = self.reused_work_auto_id.copy()
        copied_automation.write({
            'is_reusable': False,
        })

        updated_code = self.code or ''
        if updated_code:
            updated_code = re.sub(
                r'env\["work\.auto"\]\.browse\(\d+\)',
                f'env["work.auto"].browse({copied_automation.id})',
                updated_code,
                count=1,
            )

        self.write({
            'reused_work_auto_id': copied_automation.id,
            'label': copied_automation.name,
            'code': updated_code,
        })

        return {
            'id': copied_automation.id,
            'name': copied_automation.name,
            'label': copied_automation.name,
            'code': updated_code,
        }
