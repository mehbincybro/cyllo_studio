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
import odoo
from odoo import models
from odoo.http import request

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _handle_debug(cls):
        try:
            with request.env.registry.cursor() as cr:
                env = odoo.api.Environment(cr,
                                           request.session.uid or
                                           odoo.SUPERUSER_ID,
                                           request.session.context)
                user = env.user
                company_id = env.company.id
                profiles = user.profile_ids

                if profiles:
                    access_mgmt = request.env[
                        'profile.management'].sudo().search([
                        ('profile_ids', 'in', profiles.ids),
                        ('is_activated', '=', True), "|",
                        ('company_ids', 'in', [company_id]),
                        ('company_ids', '=', False)
                    ])
                    if access_mgmt:
                        if company_id in access_mgmt.company_ids.ids:
                            if any(access_mgmt.mapped("disable_debug_mode")):
                                request.session.debug = ""
                                return

        except Exception:
            request.session.debug = request.session.debug or ""

        return super()._handle_debug()
