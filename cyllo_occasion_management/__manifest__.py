# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    'name': 'Occasion Management',
    'version': '17.0.1.0.0',
    'summary': 'All-in-One Venue, Catering, Transport and Event Booking System',
    'description': 'Manage Venue Booking, Catering Services, Transportation Services '
               'and Event Booking in one platform. Supports Event Planning, '
               'Venue Reservation, Food Services, Transport Logistics, Guest '
               'Management, Scheduling, Hall Booking, Wedding, '
               'Party and Event Coordination',
    "category": "Account/Website",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'depends': ['base', 'account', 'website', 'event', 'hr', 'product'],
    'website': 'https://www.cyllo.com',
    'data': [
        'security/venue_booking_management_groups.xml',
        'security/venue_booking_secruity.xml',
        'security/ir.model.access.csv',
        'data/venue_type_data.xml',
        'data/catering_booking_data.xml',
        'data/catering_sample_data.xml',
        'data/cancellation_email_template_data.xml',
        'data/confirmation_email_template_data.xml',
        'views/catering_booking_views.xml',
        'views/catering_category_views.xml',
        'views/catering_food_category_views.xml',
        'views/platter_type_views.xml',
        'views/event_event_views.xml',
        'views/venue_booking_views.xml',
        'views/venue_type_views.xml',
        'views/amenities_views.xml',
        'views/product_template_views.xml',
        'views/venue_views.xml',
        'views/dashboard_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/check_venue_availability_views.xml',
        'report/venue_booking_report_views.xml',
        'report/venue_booking_report_templates.xml',
        'report/venue_booking_rerports.xml',
        'wizards/venue_booking_analysis_views.xml',
        'views/website_venue_booking_templates.xml',
        'views/website_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_occasion_management/static/src/css/website_page.css',
            'cyllo_occasion_management/static/src/js/website_venue_booking.js'
        ],
        'web.assets_backend': [
            'https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&amp;display=swap',
            'cyllo_occasion_management/static/src/css/venue_dashboard.css',
            'cyllo_occasion_management/static/src/scss/venue_booking.scss',
            'cyllo_occasion_management/static/src/xml/dashboard_templates.xml',
            'cyllo_occasion_management/static/src/js/action_manager.js',
            'cyllo_occasion_management/static/src/js/dashboard_action.js',
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js'
        ]
    },
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
}

