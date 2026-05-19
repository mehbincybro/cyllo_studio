# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Link Tracker',
    'version': '1.0',
    'category': 'Marketing',
    'summary': 'QR Code Overview, Record QR Status, and Scan Analytics for Cyllo Link Tracker',
    'description': """
        Provides streamlined QR tracking under the Link Tracker menu:
        1. QR Code Overview — every QR token with Tracked / Not Tracked status.
        2. Record QR Status — global scan analytics per record for all models.
        3. Unscanned QR Tokens — tokens with zero scans across all reports.
    """,
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['link_tracker', 'cyllo_studio'],
    'data': [
        'security/ir.model.access.csv',
        'views/qr_token_views.xml',
        'views/qr_record_status_views.xml',
        'views/link_tracker_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
