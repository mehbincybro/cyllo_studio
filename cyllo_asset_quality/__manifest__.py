# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Asset Quality Integration',
    'version': '17.0.1.0.0',
    'summary': 'Integration between Cyllo Asset Management and Cyllo Quality',
    'description': """
        This module integrates asset management with quality checks.
        Allows performing quality checks before returning leased or rented assets.
        Automatically creates maintenance requests if quality checks fail.
    """,
    'category': 'Operations',
    'author': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': [
        'cyllo_asset_management',
        'cyllo_quality'
    ],
    'data': [
        'views/quality_control_point_views.xml',
        'views/quality_check_views.xml',
        'views/asset_lease_views.xml',
        'views/asset_rental_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
