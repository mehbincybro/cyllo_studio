# -*- coding: utf-8 -*-
from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    """Inherit model mail.compose.message with additional fields and methods."""
    _inherit = 'mail.compose.message'

    marketing_activity_id = fields.Many2one('marketing.activity', ondelete='cascade', help="Marketing activity")

    def _prepare_mail_values_mailing_traces(self, mail_values_all):
        """
            Override method to link mail automation activity with mail
            statistics.

            This method prepares the mail trace values and adds the link to the
            corresponding marketing activity line.

            Args:
                mail_values_all (dict): A dictionary containing mail trace
                values.

            Returns:
                dict: The updated mail trace values with the link to marketing
                activity line.
        """
        mail_trace_vals = super()._prepare_mail_values_mailing_traces(
            mail_values_all)
        if not self.marketing_activity_id:
            return mail_trace_vals
        # Retrieve marketing activity lines related to the current marketing
        # activity
        activity_line = self.env['marketing.activity.line'].search([('activity_id', '=', self.marketing_activity_id.id),
                                                                    ('record_id', 'in', list(mail_trace_vals.keys()))])
        # Create a dictionary mapping record_id to marketing activity line id
        mail_trace = {record.record_id: record.id for record in activity_line}
        # Update mail trace values with the link to marketing activity line
        for record_id, vals in mail_trace_vals.items():
            vals['marketing_activity_line_id'] = mail_trace[record_id]
        return mail_trace_vals
