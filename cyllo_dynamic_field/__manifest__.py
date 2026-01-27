# -*- coding: utf-8 -*-
{
    'name': "Dynamic Field",
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': 'Create fields dynamically from the form view ',
    'description': """Cyllo Dynamic Field module helps to create fields by 
     giving some field attributes in the form view and it also adds in to the 
     tree view""",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/field_widget_data.xml',
        'views/ir_model_fields_views.xml',
        'wizards/field_create_views.xml',
        ],
    'assets': {
        'web.assets_backend': [
            'cyllo_dynamic_field/static/src/css/wizards.css',
            'cyllo_dynamic_field/static/src/js/form_controller.js',
            "cyllo_dynamic_field/static/src/js/form_label.js",
            "cyllo_dynamic_field/static/src/xml/form_label.xml",
        ],
        'web.qunit_suite_tests': [
            'cyllo_dynamic_field/static/src/tests/form_controller_patch_tests.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
