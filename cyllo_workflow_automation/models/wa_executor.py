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
import base64
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WaWorkflowExecutor(models.AbstractModel):
    _name = 'wa.workflow.executor'
    _description = 'WhatsApp Workflow Executor Helper'

    @api.model
    def _check_whatsapp_installed(self):
        """
            Check whether the WhatsApp module is installed.

            This method verifies if the 'cyllo_whatsapp' module is installed
            in the system by checking its state in the module registry.

            Returns:
                bool: True if the module is installed, False otherwise.
            """
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'cyllo_whatsapp'), ('state', '=', 'installed')],
            limit=1,
        )
        return bool(module)

    @api.model
    def _check_whatsapp_configured(self, user=None):
        """
            Check whether WhatsApp is properly configured for a user.

            This method verifies that the required WhatsApp credentials
            (token, account UID, phone UID, and app UID) are available
            for the given user.

            Args:
                user (res.users, optional): User to check configuration for.
                                            Defaults to the current user.

            Returns:
                bool: True if all required credentials are present, False otherwise.
            """
        user = user or self.env.user
        return bool(user.token and user.account_uid and user.phone_uid and user.app_uid)

    @api.model
    def send_workflow_whatsapp(self, record, partner_path=None, template_id=None, free_message=None, partner_id=None):
        """
            Send a WhatsApp message as part of a workflow execution.

            This method handles sending WhatsApp messages either using a predefined
            template or a free-form message. It ensures that the WhatsApp module is
            installed and properly configured before proceeding.

            Workflow:
                - Validate WhatsApp module installation.
                - Validate user WhatsApp configuration.
                - Resolve the target partner dynamically using the provided partner path.
                - Ensure the partner has a valid WhatsApp number.
                - Create or reuse an existing WhatsApp channel.
                - Send either:
                    * A template-based message (with optional PDF attachment), or
                    * A free-form text message.

            Args:
                record (recordset): The main record from which the partner is resolved.
                partner_path (str): Dot-separated path to locate the partner field
                                    (e.g., 'partner_id' or 'order_id.partner_id').
                template_id (int, optional): ID of the WhatsApp template to use.
                free_message (str, optional): Message content for free-form sending.
                partner_id (int, optional): Explicit res.partner ID to use as recipient.

            Returns:
                bool: True if the message was successfully sent, False if skipped.

            Raises:
                UserError: If WhatsApp is not configured for the current user.
                Exception: Re-raises any exception encountered during message sending.
            """
        if not self._check_whatsapp_installed():
            _logger.warning("Workflow WhatsApp node skipped: cyllo_whatsapp is not installed.")
            return False

        if not self._check_whatsapp_configured():
            raise UserError(_(
                "Please configure WhatsApp first.\n"
                "Go to Settings -> Users -> your user -> WhatsApp Account tab "
                "and fill in Token, Account UID, Phone UID, and App UID."
            ))

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = record
            for attr in (partner_path or '').split('.'):
                if not attr:
                    continue
                if not hasattr(partner, attr):
                    _logger.error(
                        "WA workflow: record %s has no attribute '%s' in path '%s'",
                        record, attr, partner_path,
                    )
                    return False
                partner = getattr(partner, attr)

        if getattr(partner, '_name', None) and len(partner) > 1:
            partner = partner[:1]

        if not partner or not hasattr(partner, 'whatsapp_number') or not partner.whatsapp_number:
            _logger.warning(
                "WA workflow: partner resolved from %r via '%s' has no whatsapp_number. Skipping.",
                record, partner_path,
            )
            return False

        channel = self.env['whatsapp.channel'].search([
            ('partner_id', '=', partner.id),
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if not channel:
            channel = self.env['whatsapp.channel'].create({
                'name': partner.name,
                'partner_id': partner.id,
                'sender_id': self.env.user.partner_id.id,
                'user_id': self.env.user.id,
            })

        try:
            if template_id:
                template = self.env['whatsapp.template'].browse(template_id)
                attachment = None
                if template.report_id:
                    report = template.report_id
                    pdf_content, _content_type = report._render_qweb_pdf([record.id])
                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': '%s.pdf' % report.name,
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': record._name,
                        'res_id': record.id,
                    })
                template.action_send_template(record, attachment, partner)
                _logger.info(
                    "WA workflow: sent template %s to partner %s (%s)",
                    template.display_name, partner.name, partner.whatsapp_number,
                )
            else:
                self.env['whatsapp.message'].send_whatsapp_message({
                    'channel': {'id': channel.id},
                    'message': free_message or '',
                    'attachment': False,
                    'image': False,
                    'video': False,
                })
                _logger.info(
                    "WA workflow: sent free-form message to %s",
                    partner.whatsapp_number,
                )
            return True
        except Exception as exc:
            _logger.error(
                "WA workflow: failed to send WhatsApp to %s - %s",
                partner.whatsapp_number, exc,
            )
            raise
