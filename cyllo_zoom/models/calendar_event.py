# # -*- coding: utf-8 -*-
import json
import requests
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    """Inheriting Calendar events to create zoom meetings"""
    _inherit = 'calendar.event'

    is_zoom_meet = fields.Boolean(
        string='Zoom Meeting',
        help='Enable to create a Zoom meeting for this event.'
    )
    zoom_meet_url = fields.Char(
        string='Zoom Meeting URL',
        help='URL to join the Zoom meeting.'
    )
    zoom_meet_code = fields.Char(
        string='Zoom Meeting ID',
        help='Zoom meeting ID (used as meeting code).'
    )
    zoom_meet_password = fields.Char(
        string='Zoom Meeting Password',
        help='Passcode required to join by Meeting ID.'
    )
    zoom_event = fields.Char(
        string='Zoom Event ID',
        help='Internal Zoom meeting event ID.'
    )
    video_call_location = fields.Char(
        'Meeting URL',
        related='zoom_meet_url',
        store=True
    )
    description = fields.Html(
        'Description',
        compute="_compute_description",
        store=True,
        readonly=False
    )
    meeting_processed = fields.Boolean(
        string='Meeting Processed',
        help='Enable when meeting is ended'
    )

    # ----------------------------------------------------------------------
    # DESCRIPTION COMPUTE
    # ----------------------------------------------------------------------
    @api.depends('zoom_meet_code', 'zoom_meet_url', 'zoom_meet_password', 'is_zoom_meet')
    def _compute_description(self):
        """Generate readable description with Zoom details OR clear it."""
        for rec in self:

            # If Zoom is disabled → clear description
            if not rec.is_zoom_meet:
                rec.description = ""
                continue

            # Zoom is enabled → build HTML block
            if rec.zoom_meet_code and rec.zoom_meet_url:
                start_str = fields.Datetime.to_string(rec.start)
                stop_str = fields.Datetime.to_string(rec.stop)
                rec.description = Markup(_(f"""
                    <div style="font-family: Arial, sans-serif; color: #333; padding: 16px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 420px;">
                        <h2 style="margin-top: 0; color: #2c3e50; font-size: 20px; text-align: center;">
                            <i class="fa fa-calendar" style="color:#0078ff;"></i> Zoom Meeting
                        </h2>

                        <p style="font-size: 14px; margin: 6px 0;">
                            <b>Start:</b> {start_str}<br>
                            <b>End:</b> {stop_str}<br>
                            <b>Meeting ID:</b> {rec.zoom_meet_code}<br>
                            <b>Password:</b> {rec.zoom_meet_password or 'None'}
                        </p>

                        <div style="text-align: center; margin-top: 18px;">
                            <a href="{rec.zoom_meet_url}" 
                               target="_blank"
                               style="
                                   background-color: #0078ff;
                                   color: white;
                                   padding: 10px 18px;
                                   text-decoration: none;
                                   border-radius: 5px;
                                   font-size: 14px;
                                   display: inline-block;">
                                ▶ Join Zoom Meeting
                            </a>
                        </div>
                    </div>
                """))

    # ----------------------------------------------------------------------
    # ACTION: OPEN ZOOM URL
    # ----------------------------------------------------------------------
    def action_zoom_meet_url(self):
        """Join zoom from Odoo"""
        meet_url = self.zoom_meet_url or 'https://api.zoom.us/v2/'
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': meet_url,
        }

    # ----------------------------------------------------------------------
    # CREATE EVENT
    # ----------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals):
        events = super().create(vals)
        for event in events:
            if event.is_zoom_meet:
                self._create_zoom_meet(event)
                event._send_zoom_invitation_to_attendees()
        return events

    # ----------------------------------------------------------------------
    # WRITE EVENT
    # ----------------------------------------------------------------------
    def write(self, vals):
        old_partners = {rec.id: rec.partner_ids for rec in self}
        res = super().write(vals)

        for event in self:
            if event.is_zoom_meet and not event.zoom_event:
                self._create_zoom_meet(event)
                event._send_zoom_invitation_to_attendees()
            else:
                old = old_partners.get(event.id, self.env['res.partner'])
                new_partners = event.partner_ids - old
                if new_partners:
                    event._send_zoom_invitation_to_attendees(new_partners)
        return res

    # ----------------------------------------------------------------------
    # CREATE ZOOM MEETING (API)
    # ----------------------------------------------------------------------
    def _create_zoom_meet(self, cal_event):
        url = "https://api.zoom.us/v2/users/me/meetings"
        current_uid = self._context.get('uid')
        user_id = self.env['res.users'].browse(current_uid)
        duration = cal_event.duration * 60

        payload = {
            "topic": cal_event.name,
            "type": 2,
            "start_time": cal_event.start.isoformat(),
            "timezone": 'UTC',
            "duration": int(duration),
            "settings": {
                "email_notification": False,
                "waiting_room": True,
                "join_before_host": True,
                "mute_participants_upon_entry": True,
                "auto_recording": "local",
                "auto_start_meeting_summary": True,
            },
        }

        headers = {
            'Authorization': f'Bearer {user_id.zoom_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        res_json = response.json()
        _logger.debug("Zoom API create response: %s", res_json)

        if res_json.get('code') == 124:
            raise UserError(_("Zoom Token Expired. Please refresh token."))

        if res_json.get('id'):
            cal_event.zoom_event = res_json.get('id')
            cal_event.zoom_meet_url = res_json.get('join_url')
            cal_event.zoom_meet_code = res_json.get('id')
            cal_event.zoom_meet_password = res_json.get('password') or ''
        else:
            raise ValidationError(
                _("Failed to create Zoom meeting. Please check authorization."))

    # ----------------------------------------------------------------------
    # ONCHANGE: CLEAR ZOOM WHEN DISABLED
    # ----------------------------------------------------------------------
    @api.onchange("is_zoom_meet")
    def _onchange_is_zoom_meet(self):
        if not self.is_zoom_meet and self.zoom_event:
            current_uid = self._context.get('uid')
            user_id = self.env['res.users'].browse(current_uid)
            url = f'https://api.zoom.us/v2/meetings/{self.zoom_event}'
            headers = {
                'Authorization': f'Bearer {user_id.zoom_token}',
                'Content-Type': 'application/json',
            }

            response = requests.delete(url, headers=headers)
            if response.status_code == 401:
                raise UserError(_("Zoom Token Expired. Please refresh token."))

            # Clear all fields
            self.zoom_meet_url = ''
            self.zoom_meet_code = ''
            self.zoom_meet_password = ''
            self.zoom_event = ''
            # Description clears automatically from compute()

            _logger.info(f"Zoom meeting deleted for event '{self.name}'.")

    # ----------------------------------------------------------------------
    # INVITATIONS
    # ----------------------------------------------------------------------
    def _send_zoom_invitation_to_attendees(self, partners=None):
        template_id = self.env.ref("calendar.calendar_template_meeting_update").id
        if not template_id:
            return

        mail_template = self.env['mail.template'].browse(template_id)
        if not mail_template.exists():
            return

        target_partners = partners or self.attendee_ids.mapped('partner_id')
        target_partners = [partner.id for partner in target_partners]

        mail_template.with_context(
            default_partner_ids=target_partners
        ).send_mail(self.id, force_send=True)

    # ----------------------------------------------------------------------
    # DELETE EVENT
    # ----------------------------------------------------------------------
    def unlink(self):
        for event in self:
            if event.is_zoom_meet and event.zoom_event:
                current_uid = self._context.get('uid')
                user_id = self.env['res.users'].browse(current_uid)
                company_id = user_id.company_id
                url = f'https://api.zoom.us/v2/meetings/{event.zoom_event}'
                headers = {
                    'Authorization': f'Bearer {company_id.zoom_company_access_token}',
                    'Content-Type': 'application/json',
                }

                requests.delete(url, headers=headers)

        return super().unlink()

    def _zoom_alarm_notification(self):
        for rec in self:
            if not rec.is_zoom_meet:
                continue

            start_str = fields.Datetime.to_string(rec.start)
            stop_str = fields.Datetime.to_string(rec.stop)

            message = Markup(f"""
                <div style="font-family: Arial, sans-serif; color: #333; padding: 16px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 420px;">
                    <h2 style="margin-top: 0; color: #2c3e50; font-size: 20px; text-align: center;">
                        <i class="fa fa-calendar" style="color:#0078ff;"></i> Zoom Meeting Reminder
                    </h2>

                    <p style="font-size: 14px; margin: 6px 0;">
                        <b>Start:</b> {start_str}<br>
                        <b>End:</b> {stop_str}<br>
                        <b>Meeting ID:</b> {rec.zoom_meet_code}<br>
                        <b>Password:</b> {rec.zoom_meet_password or 'None'}
                    </p>

                    <div style="text-align: center; margin-top: 18px;">
                        <a href="{rec.zoom_meet_url}"
                           target="_blank"
                           style="
                               background-color: #0078ff;
                               color: white;
                               padding: 10px 18px;
                               text-decoration: none;
                               border-radius: 5px;
                               font-size: 14px;
                               display: inline-block;">
                            ▶ Join Zoom Meeting
                        </a>
                    </div>
                </div>
            """)

            # Post chatter message + inbox notification
            rec.message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=rec.attendee_ids.mapped('partner_id').ids
            )

            # Optional: Real-time browser popup
            for partner in rec.attendee_ids.mapped('partner_id'):
                self.env['bus.bus']._sendone(
                    (self.env.cr.dbname, 'res.partner', partner.id),
                    {
                        'type': 'simple_notification',
                        'title': "Zoom Meeting Reminder",
                        'message': f"Your meeting '{rec.name}' is starting soon!",
                        'zoom_url': rec.zoom_meet_url,
                    }
                )

