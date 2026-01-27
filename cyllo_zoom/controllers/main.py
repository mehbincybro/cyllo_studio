# -*- coding: utf-8 -*-
from odoo import fields
from datetime import timedelta
import requests
from odoo import http
from odoo.http import request
import os
import base64
import mimetypes
import logging
from datetime import datetime
import pytz
import tzlocal

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

_logger = logging.getLogger(__name__)

processed_meeting = set()
class ZoomController(http.Controller):

    @http.route('/zoom/callback', type='http', auth='public', csrf=False)
    def zoom_callback(self, **kwargs):
        """function is used for creating the zoom token info"""
        code = kwargs.get('code')
        state = kwargs.get('state')
        error = kwargs.get('error')

        if error:
            return f"<h3>Zoom Authorization Failed: {error}</h3>"
        if not code or not state:
            return "<h3>Missing code or state from Zoom response.</h3>"

        user = request.env['res.users'].sudo().browse(int(state))
        if not user.exists():
            return "<h3>Invalid user reference.</h3>"

        # Zoom credentials from user
        client_id = user.zoom_client
        client_secret = user.zoom_client_secret
        redirect_uri = user.zoom_redirect_uri
        if not all([client_id, client_secret, redirect_uri]):
            return "<h3>Missing Zoom credentials in user settings.</h3>"

        auth_header = base64.b64encode(
            f"{client_id}:{client_secret}".encode()).decode()

        token_url = "https://zoom.us/oauth/token"

        try:
            response = requests.post(
                token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=15
            )
            response.raise_for_status()
            tokens = response.json()

        except requests.exceptions.HTTPError as e:
            return f"<h3>Failed to exchange Zoom token: {response.text}</h3>"

        # Save token info
        user.write({
            'zoom_code': code,
            'zoom_token': tokens.get('access_token'),
            'zoom_status': 'connected',
            'zoom_token_expiry': fields.Datetime.now() + timedelta(
                seconds=tokens.get('expires_in', 3599)),
            'zoom_refresh_token': response.json().get('refresh_token'),
        })
        return request.redirect('/web')


    @http.route('/zoom/webhook', type='json', auth='public', methods=['POST'],
                csrf=False)
    def zoom_webhook(self, **kwargs):
        """Response from the Zoom after meeting ends"""
        data = request.get_json_data()
        meeting_id = str(data['payload']['object']['id'])
        user = request.env['calendar.event'].sudo().search(
            [('zoom_meet_code', '=', meeting_id)],
            limit=1
        )
        if not user.meeting_processed:
            if data.get('event') == 'meeting.ended':
                user.write(
                    {
                        'meeting_processed': True
                    }
                )
                events = user.read(['res_id', 'res_model'])
                path_to_watch = user.user_id.zoom_recordings
                start_time_utc_str = data['payload']['object']['start_time']
                end_time_utc_str = data['payload']['object']['end_time']

                # Parse as UTC aware datetimes
                start_time_utc = datetime.strptime(start_time_utc_str,
                                                   "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=pytz.UTC)
                end_time_utc = datetime.strptime(end_time_utc_str,
                                                 "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=pytz.UTC)

                # Convert to system local timezone
                local_tz = tzlocal.get_localzone()
                start_time_local = start_time_utc.astimezone(local_tz)
                end_time_local = end_time_utc.astimezone(local_tz)

                # Make naive datetimes for Odoo
                start_time_local_naive = start_time_local.replace(tzinfo=None)
                end_time_local_naive = end_time_local.replace(tzinfo=None)

                if not os.path.isdir(path_to_watch):
                    _logger.error(f"No folders found in directory: {path_to_watch}")
                    return {"status": "error", "message": "No folders found."}

                folders = [os.path.join(path_to_watch, f) for f in
                           os.listdir(path_to_watch)]
                folders = [f for f in folders if os.path.isdir(f)]
                if not folders:
                    _logger.error(f"No folders found in directory: {path_to_watch}")
                    return {"status": "error", "message": "No folders found."}

                latest_folder = max(folders, key=os.path.getmtime)
                audio_extensions = {'.mp3', '.m4a', '.wav', '.aac', '.ogg'}

                for root, _, files in os.walk(latest_folder):
                    for file in files:
                        if os.path.splitext(file)[1].lower() in audio_extensions:
                            file_path = os.path.join(root, file)
                            _logger.info(f'Found audio file: {file_path}')

                            audio_mime_type = mimetypes.guess_type(file_path)[
                                                  0] or "audio/mpeg"
                            with open(file_path, "rb") as audio_file:
                                encoded_audio = base64.b64encode(
                                    audio_file.read()).decode("utf-8")
                            # --- Hardcoded API key for testing ---
                            TEST_GOOGLE_API_KEY = request.env[
                                'ir.config_parameter'].sudo().get_param(
                                'cyllo_agent.api_key')
                            message = HumanMessage(
                                content=[
                                    {"type": "text",
                                     "text": f"Transcribe the audio recording from the Zoom meeting. The meeting starts at {start_time_local_naive} (system time) and ends at {end_time_local_naive} (system time). Generate the meeting summary and include the duration calculated from the provided start and end times. Also provide the starting time and ending time clearly in the output, using the system time format. Provide only the summary. Do not mention that the summary is based on the audio; present it solely as the meeting summary."},
                                    {
                                        "type": "media",
                                        "data": encoded_audio,
                                        "mime_type": audio_mime_type,
                                    },
                                ]
                            )
                            # Initialize LLM with the hardcoded key
                            llm = ChatGoogleGenerativeAI(
                                model='gemini-2.5-flash',
                                google_api_key=TEST_GOOGLE_API_KEY
                            )

                            response = llm.invoke([message])
                            _logger.info(f"Response for audio: {response.content}")
                            if response:
                                res_id = events[0]['res_id']
                                res_model = events[0]['res_model']
                                record = request.env[res_model].sudo().browse(res_id)
                                message = response.content
                                record.message_post(
                                    body=message,
                                    subject='Latest Meeting'
                                )
