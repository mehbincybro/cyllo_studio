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
import requests


def get_country_phone_codes(env):
    """
    Retrieves country phone codes from an external API and creates records in the 'country.code' model.
    Args:
        env (odoo.api.Environment): Odoo environment
    Returns:
        None
    """
    url = "https://restcountries.com/v2/all"
    response = requests.get(url)
    if response.status_code == 200:
        countries = response.json()
        for country in countries:
            phone_code = country['callingCodes'][0] if country['callingCodes'][0] else None
            if phone_code:
                env['country.code'].sudo().create({
                    'country': f"{country['name']}({phone_code})",
                    'code': phone_code
                })
