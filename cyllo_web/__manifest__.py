# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': "Cyllo Web",
    'version': '1.0.0',
    'website': "https://www.cyllo.com",
    'summary': 'Module to change UI of login page and database manager',
    'description': """This module facilitates the alteration of the user interface (UI) and user experience (UX) 
    for various components, including the login page, password reset functionality, sign-up page, and database 
    manager""",
    'category': 'Hidden',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['cyllo_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_dark_mode_data.xml',
        'data/res_lang_data.xml',
        'data/ir_module_module.xml',
        'views/auth_signup_fields.xml',
        'views/login_templates.xml',
        'views/auth_signup_login_templates.xml',
        'views/webclient_templates.xml',
        'views/portal_templates.xml',
        'views/res_users_views.xml',
        'views/ir_model_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_web/static/src/lib/carousel/owl.carousel.js',
            'cyllo_web/static/src/js/owlcoursel.js',
            'cyllo_web/static/src/css/style.css',
            'cyllo_web/static/src/css/login_page.css',
            'cyllo_web/static/src/css/owl.carousel.min.css',
            'cyllo_web/static/src/css/owl.theme.default.min.css',
            'cyllo_web/static/src/js/login.js'
        ],
        'web.assets_backend': [
            'cyllo_web/static/src/core/**/*',
            'cyllo_web/static/src/lib/**/*',
            'cyllo_web/static/src/js/effect/**/*',
            'cyllo_web/static/src/js/popups/**/*',
            'cyllo_web/static/src/js/service/*',
            'cyllo_web/static/src/js/systray/**/*',
            'cyllo_web/static/src/js/views/fields/color_picker/*',
            'cyllo_web/static/src/js/views/gantt/*',
            'cyllo_web/static/src/js/views/pivot/*',
            ('after', 'web/static/src/views/**/*', 'cyllo_web/static/src/js/views/graph/graph_controller.js'),
            ('after', 'web/static/src/views/**/*', 'cyllo_web/static/src/js/views/graph/graph_arch_parser.js'),
            ('after', 'web/static/src/views/**/*', 'cyllo_web/static/src/js/views/graph/graph_model.js'),
            ('after', 'web/static/src/views/**/*', 'cyllo_web/static/src/js/views/graph/graph_renderer.js'),
            ('after', 'web/static/src/views/**/*', 'cyllo_web/static/src/js/views/graph/graph_view.js'),
            'cyllo_web/static/src/js/views/graph/graph_controller.xml',
            'cyllo_web/static/src/js/widgets/**/*',
            'cyllo_web/static/src/js/hooks/*',
            'cyllo_web/static/src/js/navbar/*',
            'cyllo_web/static/src/js/settings/SettingsFormCompiler.js',
            'cyllo_web/static/src/xml/*',
            'cyllo_web/static/src/css/pivot.css',
            'cyllo_web/static/src/css/systray.css',
        ],
        'web.qunit_suite_tests': [
            'cyllo_web/static/src/tests/*',
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'uninstall_hook': 'uninstall_hook',
    'auto_install': True,
    'application': False,
}
