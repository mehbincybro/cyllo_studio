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
from odoo import fields, models
from odoo.tools import date_utils


class ResPartner(models.Model):
    _inherit = 'res.partner'

    move_ids = fields.One2many(
        'account.move',
        'partner_id',
        string="Invoice Details",
        domain=[
            ('payment_state', '!=', 'paid'),
            ('state', '=', 'posted'),
            ('invoice_date_due', '<', fields.Date.today()),
        ],
        readonly=True,
    )

    check_followups = fields.Boolean(
        compute='_compute_check_followups',
        store=False,
    )

    # ---------------------------------------------------------
    # COMPUTE
    # ---------------------------------------------------------

    def _compute_check_followups(self):
        FollowupLine = self.env['accounting.followup.line']

        for partner in self:
            partner.check_followups = False

            for move in partner.move_ids:
                if not move.invoice_date_due:
                    continue

                due_days = (fields.Date.today() - move.invoice_date_due).days

                followup = FollowupLine.search(
                    [('due_date', '=', due_days)],
                    limit=1
                )

                if (
                    followup
                    and followup != move.last_follow_up_id
                    and not move.next_follow_up_id
                ):
                    move.next_follow_up_id = followup

            partner.check_followups = True

    # ---------------------------------------------------------
    # FOLLOWUP ACTION
    # ---------------------------------------------------------

    def change_followup_action(self, moves):
        for move in moves:
            followup = move.next_follow_up_id
            if not followup:
                continue

            if followup.send_mail and followup.mail_template_id:
                followup.mail_template_id.sudo() \
                    .with_context(move_id=move.id) \
                    .send_mail(self.id, force_send=True)

            # ✅ ALWAYS update fields
            move.write({
                'next_follow_up_id': False,
                'last_follow_up_id': followup.id,
            })

    # ---------------------------------------------------------
    # CRON
    # ---------------------------------------------------------

    def _execute_followup(self):
        moves = self.env['account.move'].search([
            ('next_follow_up_id', '!=', False)
        ])
        if moves:
            self.change_followup_action(moves)
