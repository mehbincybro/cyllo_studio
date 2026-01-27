# -*- coding: utf-8 -*-
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
