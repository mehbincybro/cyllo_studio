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

from odoo import _, exceptions, fields, models


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

    # warning block fields
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

    #search block fields
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

    # create block fields
    create_name = fields.Char()
    create_model_field_value = fields.Char(default="[]")
    create_req_fields_values = fields.Json("createFields")
    create_tree_fields_values = fields.Json("createTreeFields")
    create_required_field = fields.Json("createRequiredField")

    #Write block fields
    write_field_value = fields.Char(default="[]")
    write_selected_record = fields.Json("Record")

    #Function call block fields
    function_name = fields.Json("Function Name")
    function_type = fields.Char(string="Function Type", default="server_action")
    function_record = fields.Json()
    function_args = fields.Json("Function Arguments", default={})

    #Variables block fields
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

    #codeNode block fields
    code_code = fields.Char(string="Code")

    # mailNode block fields
    mailCustomData = fields.Json(string="Mail Custom Data")
    mail_record = fields.Json(string="MailRecord")
    mail_template = fields.Json(string="MailTemplate")
    mail_isTemplate = fields.Json(string="MailIsTemplate")
    mail_from = fields.Json(string="MailFrom")
    mail_to = fields.Json(string="MailTo")
    mail_subject = fields.Json(string="MailSubject")
    mail_body = fields.Json(string="MailBody")

    # smsNode block fields
    sms_record = fields.Json(string="sms record")
    sms_template = fields.Json(string="sms template")
    sms_partner_ids = fields.Json(string="Recipients")
    recipients = fields.Json(string='reciep')
    sms_isTemplate = fields.Boolean(string="SMSIsTemplate")
    sms_message = fields.Char(string="smsMessage")

    # WhatsApp node block fields
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

    # FollowersNode block fields
    isRemoveFollower = fields.Json()
    followers = fields.Json()
    follower_record = fields.Json()

    # ActivityNode block fields
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
            'active': False,
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
