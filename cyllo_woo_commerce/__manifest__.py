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
    'name': 'Cyllo WooCommerce Connector',
    'version': '1.0',
    'category': 'Ecommerce',
    'summary': 'Cyllo WooCommerce Connector for smooth integration and '
               'real-time synchronization between Cyllo and WooCommerce. '
               'Effortlessly manage imports and exports, streamline your '
               'workflow, and optimize data synchronization with queue jobs. '
               'Stay responsive and efficient with instant notifications, '
               'enhancing overall business operations',
    'description': 'Effortlessly sync customers, products, and orders in '
                   'real-time between Cyllo and WooCommerce with our powerful '
                   'connector. Streamline your workflow with seamless imports '
                   'from WooCommerce to Cyllo and simplify exports for a '
                   'smooth data flow. Optimize synchronization using queue '
                   'jobs, overcoming challenges and ensuring an efficient, '
                   'uninterrupted business workflow. Elevate your '
                   'coordination and responsiveness with instant '
                   'notifications for a seamless integration experience.',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['website_sale', 'stock', 'sale_management', 'account',
                'sale_stock'],
    'data': [
        'data/woo_commerce_data.xml',
        'data/ir_action_data.xml',
        'data/ir_cron_data.xml',
        'security/ir.model.access.csv',
        'views/woo_logs_views.xml',
        'views/woo_commerce_instance_views.xml',
        'views/product_product_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_tax_views.xml',
        'views/job_cron_views.xml',
        'views/product_category_views.xml',
        'views/product_attribute_views.xml',
        'wizard/woo_update_views.xml',
        'wizard/woo_operation_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_woo_commerce/static/src/xml/dashboard.xml',
            'cyllo_woo_commerce/static/src/css/dashboard.css',
            'cyllo_woo_commerce/static/src/js/lib/Chart.bundle.js',
            'cyllo_woo_commerce/static/src/js/dashboard.js',
        ],
    },
    "external_dependencies": {"python": ["WooCommerce"]},
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
