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
import logging

from odoo import api, fields, models
from odoo.tools import json

_logger = logging.getLogger(__name__)


class ChatbotHistory(models.Model):
    _name = 'chatbot.history'
    _description = 'Chatbot Conversation History'

    user_id = fields.Many2one('res.users', required=True)
    session_id = fields.Char()
    title = fields.Char()
    user_message = fields.Text()  # store as JSON string
    response_message = fields.Text()
    chart_config = fields.Text()
    interrupted = fields.Boolean(string='interrupted', default=False)
    create_date = fields.Datetime(readonly=True, default=fields.Datetime.now())
    company_ids = fields.Many2many('res.company', default=lambda self: self.env.company, index=True)

    @api.model
    def get_user_sessions(self, company_ids=None):
        """Get distinct sessions with first message as title"""
        user_id = self.env.user.id
        if not company_ids:
            company_ids = [self.env.company.id]

        company_ids_sorted = sorted(company_ids)

        # SQL to find records with EXACT company match
        query = """
            WITH record_companies AS (
                SELECT 
                    chatbot_history_id,
                    array_agg(res_company_id ORDER BY res_company_id) as company_array
                FROM {rel_table}
                GROUP BY chatbot_history_id
            )
            SELECT DISTINCT ON (ch.session_id)
                ch.session_id, ch.user_message,ch.title, ch.create_date, ch.id
            FROM chatbot_history ch
            INNER JOIN record_companies rc ON rc.chatbot_history_id = ch.id
            WHERE ch.user_id = %s
              AND rc.company_array = %s
              AND ch.session_id IS NOT NULL
              AND ch.session_id != ''
            ORDER BY ch.session_id, ch.create_date ASC
        """.format(rel_table='chatbot_history_res_company_rel')

        self.env.cr.execute(query, (user_id, company_ids_sorted))
        results = self.env.cr.dictfetchall()

        sessions = []
        for row in results:
            # Parse message if JSON
            if row['title']:
                display_title = row['title']
            else:
                message = row['user_message'] or ''
                try:
                    msg_data = json.loads(message)
                    if isinstance(msg_data, dict):
                        message = msg_data.get('content', '') or msg_data.get('text', '') or message
                except (json.JSONDecodeError, TypeError) as e:
                    _logger.debug('Failed to parse message as JSON, using raw message: %s', str(e), exc_info=True)

                # Generate clean title
                display_title = message.strip()[:60] or 'New chat'
                if len(message) > 60:
                    display_title += '...'
                self.env.cr.execute(
                    "UPDATE chatbot_history SET title = %s WHERE id = %s",
                    (display_title, row['id'])
                )

            sessions.append({
                'session_id': row['session_id'],
                'title': display_title,
                'timestamp': row['create_date'].isoformat() if row['create_date'] else None,
                'id': row['id']
            })

        # Sort by most recent first
        sessions.sort(key=lambda x: x['timestamp'] or '', reverse=True)

        return sessions

    @api.model
    def rename_session(self,session_id, new_title):
        current_record = self.search([('session_id','=',session_id),('title', '!=', False)],limit=1)
        if current_record:
            current_record.title = new_title

    @api.model
    def delete_session(self, session_id, companyIds):
        """
        Delete a full chat session by its session_id.
        Removes ALL chatbot_history rows belonging to that session.
        """
        if not session_id:
            return False

        # Delete all records with this session_id
        records = self.search([('session_id', '=', session_id)])
        if records:
            records.unlink()
            records = self.search([('session_id', '=', session_id)])
            return True
        return False
