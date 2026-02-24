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
# -*- coding: utf-8 -*-
import uuid
import requests
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    is_google_meet = fields.Boolean(string='Google Meeting')
    google_meet_url = fields.Char(string='Google Meet URL', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        # 1. Create the events in Odoo first
        events = super(CalendarEvent, self).create(vals_list)

        for event in events:
            if event.is_google_meet:
                try:
                    # Get Credentials
                    params = self.env['ir.config_parameter'].sudo()
                    refresh_token = params.get_param(
                        'cyllo_google.refresh_token')
                    client_id = params.get_param('cyllo_google.client_id')
                    client_secret = params.get_param(
                        'cyllo_google.client_secret')

                    if not refresh_token:
                        _logger.error(
                            "Missing Google Refresh Token in System Parameters")
                        continue

                    # 2. Get New Access Token
                    token_resp = requests.post(
                        'https://oauth2.googleapis.com/token',
                        data={
                            'grant_type': 'refresh_token',
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'refresh_token': refresh_token,
                        }
                    )

                    if token_resp.status_code != 200:
                        _logger.error(
                            f"Failed to refresh token: {token_resp.text}")
                        continue

                    access_token = token_resp.json().get('access_token')

                    # 3. Create Google Calendar Event with Meet
                    calendar_payload = {
                        'summary': event.name or 'Odoo Meeting',
                        'start': {
                            'dateTime': event.start.strftime(
                                '%Y-%m-%dT%H:%M:%SZ'),
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': event.stop.strftime(
                                '%Y-%m-%dT%H:%M:%SZ'),
                            'timeZone': 'UTC',
                        },
                        'conferenceData': {
                            'createRequest': {
                                'requestId': str(uuid.uuid4()),
                                'conferenceSolutionKey': {
                                    'type': 'hangoutsMeet'}
                            }
                        }
                    }

                    # Note: conferenceDataVersion=1 is REQUIRED
                    meet_resp = requests.post(
                        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                        headers={'Authorization': f'Bearer {access_token}'},
                        params={'conferenceDataVersion': 1},
                        json=calendar_payload
                    )

                    if meet_resp.status_code == 200:
                        data = meet_resp.json()
                        # Extract the Meet URI
                        entry_points = data.get('conferenceData', {}).get(
                            'entryPoints', [])
                        meet_link = next((ep['uri'] for ep in entry_points if
                                          ep['entryPointType'] == 'video'),
                                         None)

                        if meet_link:
                            # Update the record with the URL (sudo to bypass access rights if needed)
                            event.sudo().write({'google_meet_url': meet_link})
                            _logger.info(f"Google Meet created: {meet_link}")
                    else:
                        _logger.error(f"Google API Error: {meet_resp.text}")

                except Exception as e:
                    _logger.error(
                        f"Unexpected error creating Google Meet: {str(e)}")

        return events