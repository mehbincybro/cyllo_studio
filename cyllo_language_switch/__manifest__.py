# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Language Switch',
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': 'Add Language Switching Option in Systray',
    'description': "Add the language switching option in systray. "
                   "User can see all available languages and switching option.",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base'],
    'data': [
        'data/res_lang_data.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_language_switch/static/src/xml/switch_language.xml',
            'cyllo_language_switch/static/src/js/switch_language.js',
            'cyllo_language_switch/static/src/css/switch_language.css',
        ],
        'web.qunit_suite_tests': [
            'cyllo_language_switch/static/tests/test.js'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
