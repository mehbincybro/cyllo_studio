{
    'name': "Cyllo Ecommerce Subscription",
    'version': '1.0',
    'summary': "This module extends the Website Sale functionality to support complex, time-based subscription pricing rules",
    'description': """Extends the e-commerce product page to allow for dynamic subscription plan selection and includes custom pricing logic.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': 'Cyllo',
    'website': "https://www.cyllo.com",
    'data': ['data/product_data.xml',
             'views/website_sale_templates.xml'
             ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_website_subscription/static/src/js/website_sale.js',
        ],
    },
    'depends': ['cyllo_base','cyllo_subscription','cyllo_website_sale'],
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': True,
}
