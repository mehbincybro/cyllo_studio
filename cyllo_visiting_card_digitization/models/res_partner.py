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
##############################################################################

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_from_visiting_card = fields.Boolean(default=False)



    @api.model
    def create(self, vals):
        """Automatic Lead creation from partner."""
        rec = super().create(vals)
        if  rec.is_from_visiting_card == True:
            self.env['crm.lead'].sudo().create({
                'name': f"{rec.name}'s Opportunity",
                'partner_id': rec.id,
            })
        return rec