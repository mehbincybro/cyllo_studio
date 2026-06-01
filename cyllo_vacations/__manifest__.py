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
{
    'name': 'Cyllo Vacations',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Complete Tours and Travel Management System with Website Booking, CRM, Sales & Portal',
    'description': """
        Tours and Travel Management System
        ===================================
        
        Cyllo Website Tour Agency simplifies travel business management with integrated CRM, website booking, 
        calendar scheduling, contacts, live chat, employee management, purchases, invoicing, and sales.
        
        Key Features:
        * Create & showcase engaging tour packages with images, descriptions, and pricing
        * Enable online tour booking and secure payment integration
        * Manage itineraries, travel schedules, and availability with ease
        * Handle customer inquiries and automate email responses
        * Mobile-friendly design for a smooth user experience
        * Integration with Cyllo CRM, Accounting, and Sales for end-to-end travel business management
        * Customer portal for viewing bookings and tour details
        * Hotel and accommodation management
        * Transportation management
        * Meal planning
        * Attraction and activity management
        * Multi-currency and multi-language support
        
        Manage tour operations, automate bookings, and enhance customer experiences—all in one powerful solution!
    """,
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'license': 'LGPL-3',
    'icon': '/cyllo_vacations/static/description/cyllo_vacations_icon.svg',
    'depends': [
        'base',
        'web',
        'website',
        'portal',
        'crm',
        'sale_management',
        'account',
        'calendar',
        'contacts',
        'mail',
        'hr',
        'purchase',
        'payment',
        'website_payment',
        'website_sale',
    ],
    'data': [
        # Security
        'security/cyllo_vacations_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/tour_package_data.xml',
        'data/email_template_data.xml',
        'data/website_menu_data.xml',
        # Views - Backend
        'views/tour_package_views.xml',
        'views/tour_inquiry_views.xml',
        'views/tour_booking_views.xml',
        'views/tour_itinerary_views.xml',
        'views/tour_hotel_views.xml',
        'views/tour_transportation_views.xml',
        'views/tour_meal_views.xml',
        'views/tour_attraction_views.xml',
        'views/tour_expense_views.xml',
        'views/tour_menu_views.xml',
        'views/inherited_views.xml',
        # Views - Website
        'views/website_homepage.xml',
        'views/website_tour_templates.xml',
        'views/website_tour_package_list.xml',
        'views/website_tour_package_detail.xml',
        'views/website_tour_booking.xml',
        'views/website_tour_inquiry.xml',
        # 'views/website_tour_snippets.xml',
        
        # Views - Portal
        'views/portal_tour_templates.xml',
        # Wizards
        'wizard/tour_booking_wizard_views.xml',
        # Reports
        'report/tour_booking_report.xml',
        'report/tour_itinerary_report.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_vacations/static/src/css/tour_website.css',
            'cyllo_vacations/static/src/js/tour_booking.js',
            'cyllo_vacations/static/src/js/tour_inquiry.js',
        ],
        'web.assets_backend': [
            'cyllo_vacations/static/src/css/tour_backend.css',
        ],
    },
    'demo': [
        'data/tour_demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [
        'static/description/cyllo_vacations_icon.svg',
    ],
}

