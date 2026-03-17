# -*- coding: utf-8 -*-
from odoo import models, fields


class NodeStruct(models.Model):
    _name = 'node.struct'

    name = fields.Char()
    work_auto_id = fields.Many2one('work.auto', ondelete='cascade')
    reused_work_auto_id = fields.Many2one('work.auto', string="Reusable Automation", ondelete='set null')
    reused_variable = fields.Json("Reusable Record Variable")
    code = fields.Char("Code")
    label = fields.Char()
    type = fields.Selection(selection=[("trigger", "Trigger"), ("model", "Model"), ("node", "Node")])
    model_id = fields.Many2one('ir.model')
    used_variables = fields.Json("Used Variables")
    condition_tree_value = fields.Json("condition_tree_value")
    else_setup_code = fields.Char(string="Else Setup Code")

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
        if not self:
            struct_node_id = self.create(
                {
                    'condition_value': data,
                })
        else:
            self.write(data)
        return struct_node_id.id

    def unlink(self):
        """
        Override the unlink method to handle specific business logic before deletion.

        This method checks each record before deletion. If the record has a `work_auto_id` and is of type 'trigger',
        it unlinks the associated `function_id` from the automation work record before proceeding with the deletion.

        Returns:
            bool: True if the records were successfully deleted.
        """
        for record in self:
            if record.work_auto_id and record.type == "trigger":
                record.work_auto_id.function_id = False
        return super().unlink()
