# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Barcode',
    'version': "1.0",
    'summary': 'Cyllo Inventory Barcode',
    'description': 'Barcode for the Inventory Adjustments and Transfers',
    'category': 'Warehouse',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['stock_picking_batch', 'mrp_subcontracting'],
    'icon': '/cyllo_barcode/static/description/barcode.svg',
    'assets': {
        'web.assets_backend': [
            'cyllo_barcode/static/src/js/cyllo_barcode.js',
            'cyllo_barcode/static/src/js/barcode_adjustment.js',
            'cyllo_barcode/static/src/js/barcode_adjustment_lines.js',
            'cyllo_barcode/static/src/js/barcode_batch.js',
            'cyllo_barcode/static/src/js/barcode_location.js',
            'cyllo_barcode/static/src/js/barcode_location_lines.js',
            'cyllo_barcode/static/src/js/barcode_operation_type.js',
            'cyllo_barcode/static/src/js/barcode_dialog.js',
            'cyllo_barcode/static/src/lib/quagga.js',
            'cyllo_barcode/static/src/xml/barcode_adjustment_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_batch_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_location_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_operation_type_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_dialog.xml',
            'cyllo_barcode/static/src/js/barcode_sound_service.js',
            'cyllo_barcode/static/src/scss/cyllo_barcode.scss',
            'cyllo_barcode/static/src/tests/tour/cyllo_barcode_tour.js'
        ],
        'web.qunit_suite_tests': [
            'cyllo_barcode/static/src/tests/*'
        ]
    },
    'data': [
        'reports/cyllo_barcode_report.xml',
        'reports/cyllo_barcode_templates.xml',
        'views/stock_location_views.xml',
        'views/stock_picking_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/ir_actions_client_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True
}
