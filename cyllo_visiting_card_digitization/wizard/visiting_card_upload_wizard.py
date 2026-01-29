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
from odoo import models, fields


class VisitingCardUploadWizard(models.TransientModel):
    _name = 'visiting.card.upload.wizard'
    _description = 'Upload Visiting Card Wizard'

    visiting_card_file = fields.Binary(
        string="Upload Visiting Card",
        required=True
    )

    visiting_card_filename = fields.Char(
        string="File Name"
    )

    def action_upload(self):
        self.ensure_one()
        self.env['cyllo.visiting.card'].create({
            'visiting_card_file': self.visiting_card_file,
            'visiting_card_filename': self.visiting_card_filename,
        })

        return {'type': 'ir.actions.act_window_close'}
