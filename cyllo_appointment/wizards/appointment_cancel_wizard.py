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
from odoo import fields, models, _
import logging


class AppointmentCancelWizard(models.TransientModel):
    _name = 'appointment.cancel.wizard'
    _description = 'Cancel Appointment Wizard'

    appointment_id = fields.Many2one(
        'appointment.appointment', string='Appointment',
        required=True, readonly=True
    )
    cancellation_reason = fields.Text(string='Cancellation Reason',
                                      required=True)
    cancelled_by = fields.Selection([
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('system', 'System'),
    ], string='Cancelled By', default='staff', required=True)
    send_notification = fields.Boolean(string='Notify Customer', default=True)

    def action_confirm_cancel(self):
        self.ensure_one()
        appt = self.appointment_id
        appt.write({
            'state': 'cancelled',
            'cancellation_reason': self.cancellation_reason,
            'cancelled_by': self.cancelled_by,
        })
        if self.send_notification:
            appt.message_post(
                body=_(
                    'Appointment cancelled. Reason: %s') % self.cancellation_reason,
                subtype_xmlid='mail.mt_note'
            )
        # Send Staff Cancellation Email
        if appt.staff_id and appt.staff_id.notify_on_cancellation and appt.staff_id.work_email:
            staff_tmpl = self.env.ref(
                'cyllo_appointment.email_template_appointment_cancelled_staff',
                raise_if_not_found=False
            )
            if staff_tmpl:
                try:
                    staff_tmpl.send_mail(appt.id, force_send=True)
                except Exception as e:
                    logging.getLogger(__name__).warning(
                        "Failed to send staff cancellation email for %s: %s",
                        appt.name, str(e)
                    )
        return {'type': 'ir.actions.act_window_close'}
