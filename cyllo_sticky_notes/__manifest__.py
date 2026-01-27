# -*- coding: utf-8 -*-
{
    'name': 'Sticky Notes',
    'version': "1.0",
    'category': 'Productivity',
    'summary': 'Manage Sticky Note in Systray',
    'description': """This module helps to manage sticky notes in systray based on user.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base'],
    'icon': '/cyllo_sticky_notes/static/description/sticky-notes.svg',
    'data': [
        'security/ir.model.access.csv',
        'security/sticky_note_security.xml'
    ],
    'assets': {
       'web.assets_backend': [
           'cyllo_sticky_notes/static/src/js/sticky_note.js',
           'cyllo_sticky_notes/static/src/js/sticky_note_icon.js',
           'cyllo_sticky_notes/static/src/js/sticky_notes_item.js',
           'cyllo_sticky_notes/static/src/js/sticky_notes_add.js',
           'cyllo_sticky_notes/static/src/js/sticky_notes_create.js',
           'cyllo_sticky_notes/static/src/js/sticky_notes_update.js',
           'cyllo_sticky_notes/static/src/xml/sticky_note_icon_templates.xml',
           'cyllo_sticky_notes/static/src/xml/sticky_note_templates.xml',
           'cyllo_sticky_notes/static/src/xml/sticky_notes_add_templates.xml',
           'cyllo_sticky_notes/static/src/xml/sticky_notes_create_templates.xml',
           'cyllo_sticky_notes/static/src/xml/sticky_notes_item_templates.xml',
           'cyllo_sticky_notes/static/src/xml/sticky_notes_update_templates.xml',
           'cyllo_sticky_notes/static/src/css/notes.css',
       ],
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
