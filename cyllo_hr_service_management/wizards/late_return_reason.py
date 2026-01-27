# -*- coding: utf-8 -*-
from odoo import _, fields, models


class LateReturnReason(models.TransientModel):
    """Model which handles late return reason"""
    _name = 'late.return.reason'
    _description = "Service Request"

    service_request_id = fields.Many2one('hr.service', help="Related service request")
    reason = fields.Text(help='The reason for late return')

    def action_return(self):
        self.service_request_id.write({
            'state': 'quality',
            'return_date': fields.Datetime.today(),
        })
        msg = _("Late Return Reason :%s", self.reason)
        email_values_handler = {'email_to': self.service_request_id.service_handler_id.private_email}
        mail_template_handler = self.env.ref('cyllo_hr_service_management.mail_template_equipment_ready_to_return')
        mail_template_handler.send_mail(self.service_request_id.id, email_values=email_values_handler, force_send=True)
        self.service_request_id.message_post(body="Equipment have been ready to return")
        self.service_request_id.message_post(body=msg)
