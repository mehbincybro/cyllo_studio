{
    'name': 'Shop Floor',
    'version': '1.0',
    'summary': 'Shopfloor Interface',
    'depends': ['mrp', 'bus', 'web'],
    'data': [
        'views/cyllo_shopfloor_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_shopfloor/static/src/js/cyllo_shopfloor.js',
            'cyllo_shopfloor/static/src/xml/cyllo_shopfloor_template.xml',
            'cyllo_shopfloor/static/src/js/backend_listener.js',
        ],
    },
    'installable': True,
    'application': True,
}