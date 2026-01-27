# -*- coding: utf-8 -*-
from odoo import fields, models


class MailingTrace(models.Model):
    """
        This model inherits from the base 'mailing.trace' model and extends or
        overrides its functionality as needed.
    """
    _inherit = 'mailing.trace'

    marketing_activity_line_id = fields.Many2one('marketing.activity.line', index=True, ondelete='cascade',
                                                 help='Record corresponding to marketing line')

    def get_display_value(self, value):
        """
            Get the display value for a given key in the 'failure_type'
            selection field.
            Args:
                value (str): The key for which the display value is needed.
            Returns:
                str: The display value corresponding to the provided key.
        """
        selection_value = value  # Retrieve the key of the selection field
        display_value = dict(
            self._fields['failure_type'].selection).get(
            selection_value)  # Get the display value
        return display_value

    def set_clicked(self, domain=None):
        """
           Override the set_clicked method of MailingTrace to trigger the next
           marketing activity.
           Args:
               domain (list): A domain to filter the mailing traces
               (default is None).
           Returns:
               MailingTrace: The result of the super() call, typically a
               recordset of MailingTrace objects.
       """
        res = super(MailingTrace, self).set_clicked(domain=domain)
        res.marketing_activity_line_id.trigger_next_activity('click')
        return res

    def set_opened(self, domain=None):
        """
            Override the set_opened method of MailingTrace to trigger the next
            marketing activity.
            Args:
                domain (list): A domain to filter the mailing traces
                (default is None).
            Returns:
                MailingTrace: The result of the super() call, typically a
                recordset of MailingTrace objects.
        """
        res = super(MailingTrace, self).set_opened(domain=domain)
        res.marketing_activity_line_id.trigger_next_activity('opened')
        return res

    def set_replied(self, domain=None):
        """
           Override the set_replied method of MailingTrace to trigger the next
           marketing activity.
           Args:
               domain (list): A domain to filter the mailing traces
               (default is None).
           Returns:
               MailingTrace: The result of the super() call, typically a
               recordset of MailingTrace objects.
       """
        res = super(MailingTrace, self).set_replied(domain=domain)
        res.marketing_activity_line_id.trigger_next_activity('replied')
        return res

    def set_bounced(self, domain=None, bounce_message=False):
        res = super(MailingTrace, self).set_bounced(
            domain=domain, bounce_message=bounce_message)
        res.marketing_activity_line_id.trigger_next_activity('bounced')
        return res
