# -*- coding: utf-8 -*-
from odoo import models, api


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _do_alarm(self):
        """function for triggering the zoom_alarm notification function"""
        res = super()._do_alarm()

        # Events whose reminders are *firing right now*
        for event in self:
            if event.is_zoom_meet:
                event._zoom_alarm_notification()
        return res

