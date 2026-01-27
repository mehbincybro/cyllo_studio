# -*- coding: utf-8 -*-
{
    'name': "Cyllo Gantt",
    'version': '1.0',
    'category': 'Extra tools',
    'summary': """Cyllo Gantt View""",
    'description': """Gantt view for Cyllo""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base'],
    'assets': {
        'web.assets_backend': [
            "cyllo_gantt/static/src/scss/gantt.scss",
            "cyllo_gantt/static/src/lib/vis-timeline/vis-timeline-graph2d.js",
            "cyllo_gantt/static/src/lib/vis-timeline/vis-timeline-graph2d.css",
            "cyllo_gantt/static/src/xml/gantt_view.xml",
            "cyllo_gantt/static/src/js/gantt_controller.js",
            "cyllo_gantt/static/src/js/gantt_renderer.js",
            "cyllo_gantt/static/src/js/gantt_view.js",
        ]
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': True,
    'application': False,
}
