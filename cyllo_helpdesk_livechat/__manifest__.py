# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Livechat',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Livechat integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'im_livechat'],
    'data': [],
'assets': {
        'web.assets_backend': [
            'cyllo_helpdesk_livechat/static/src/core/common/channel_commands.js'
        ],
},
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
