# -*- coding: utf-8 -*-

{
    'name': 'Sale Analytics',
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': """
        This module helps businesses to identify customers who are at risk of discontinuing their relationship with the company.
    """,
    'description': """
        By analyzing historical data and relevant factors of the customers, churn prediction dashboard 
        helps organizations proactively take measures to retain valuable customers and reduce attrition, ultimately improving 
        customer retention and business profitability.
    """,
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'license': 'LGPL-3',
    'depends': ['cyllo_analytics', 'sale_management'],
    "external_dependencies": {
        'python': ['pandas', 'scikit-learn', 'prophet', 'statsmodels']
    },
    'data': [
        'reports/churn_prediction_templates.xml',
        'reports/demand_prediction_template.xml',
        'reports/sale_prediction_templates.xml',
        'views/cyllo_sale_analytics_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap',
            'cyllo_sale_analytics/static/src/js/churn_prediction.js',
            'cyllo_sale_analytics/static/src/js/sales_prediction.js',
            'cyllo_sale_analytics/static/src/js/demand_prediction.js',
            'cyllo_sale_analytics/static/src/js/customer_details.js',
            'cyllo_sale_analytics/static/src/xml/churn_prediction.xml',
            'cyllo_sale_analytics/static/src/xml/customer_details.xml',
            'cyllo_sale_analytics/static/src/xml/demand_prediction.xml',
            'cyllo_sale_analytics/static/src/xml/sales_prediction.xml',
        ],
    },
    'images': [],
    'installable': True,
    'application': True,
    'auto_install': True,
}
