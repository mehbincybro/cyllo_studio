# -*- coding: utf-8 -*-
import geocoder
import requests
from requests.exceptions import ConnectionError, Timeout
from odoo import http
from odoo.http import request


class WeatherNotification(http.Controller):
    """Class defined to fetch weather details based on location"""

    @http.route('/weather/notification/check', type='json', auth="public", methods=['POST'])
    def weather_notification(self):
        """Controller for fetching weather data"""
        try:
            if request.env.user.location_set == 'auto' and request.env.user.api_key:
                if geocoder.ip('me').status_code == 200:
                    lat = round(geocoder.ip('me').latlng[0], 2)
                    lng = round(geocoder.ip('me').latlng[1], 2)
                    url = (f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid='
                           f'{request.env.user.api_key}')
                    try:
                        # Set timeout to 5 seconds
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            return response.json()
                        else:
                            return {'data': False}
                    except Timeout:
                        return {'data': False, 'message': 'Request timed out.'}
                else:
                    return {'data': False,
                            'message': 'Failed to get location data.'}
            elif request.env.user.location_set == 'manual' and request.env.user.api_key:
                url = (f'https://api.openweathermap.org/data/2.5/weather?q={request.env.user.city}&appid='
                       f'{request.env.user.api_key}')
                try:
                    # Set timeout to 5 seconds
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        return response.json()
                except Timeout:
                    return {'data': False, 'message': 'Request timed out.'}
        except ConnectionError:
            return {'data': False,
                    'message': 'No internet connection. Please check your internet connectivity.'}
        else:
            return {'data': False}
