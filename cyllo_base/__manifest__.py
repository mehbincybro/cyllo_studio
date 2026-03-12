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
    'name': 'Cyllo Base',
    'version': '1.0.0',
    'description': 'This is the base module for Cyllo',
    'summary': 'Base module for Cyllo',
    'category': 'Hidden',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'base_setup', 'base_import', 'web', 'mail', 'cyllo_geolocalize'],
    'data': [
        'security/ir.model.access.csv',
        'security/sticky_note_security.xml',
        'data/field_widget_data.xml',
        'data/mail_templates_email_layout.xml',
        'data/auth_signup_mail_template_demo.xml',
        'views/res_users.xml',
        'views/ir_model_fields_views.xml',
        'views/ir_module_views.xml',
        'views/ir_model_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/webclient_templates.xml',
        'wizards/field_create_views.xml',
    ],
    'external_dependencies': {"python": ["python-docx"]},
    'assets': {
        'web.assets_backend': [
            'https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap'
            '/cyllo_base/static/src/css/dashboard.css',
            '/cyllo_base/static/src/font/remixicon.scss',
            '/cyllo_base/static/src/font/remixicon.eot',
            '/cyllo_base/static/src/font/remixicon.ttf',
            '/cyllo_base/static/src/font/remixicon.woff',
            '/cyllo_base/static/src/font/remixicon.woff2',
            '/cyllo_base/static/src/xml/*.xml',
            '/cyllo_base/static/src/js/*.js',
            '/cyllo_base/static/src/css/*.css',
            '/cyllo_base/static/src/webclient/*.js',
            '/cyllo_base/static/src/webclient/*.xml',
            '/cyllo_base/static/src/js/sticky_notes/*.js',
            '/cyllo_base/static/src/xml/sticky_notes/*.xml',
            '/cyllo_base/static/src/js/base_docx/cyllo_base_docx.js',
            '/cyllo_base/static/src/js/base_xlsx/cyllo_base_xlsx.js',
            '/cyllo_base/static/src/scss/cyllo_search_bar.scss',
            '/cyllo_base/static/src/scss/sticky_note.scss',
            '/cyllo_base/static/src/js/journal_dashboard_graph/*.js',
            '/cyllo_base/static/description/icon.svg',
            'https://cdn.jsdelivr.net/npm/@johanaarstein/dotlottie-player@1.5.23/dist/index.min.js'
        ],

        'web.assets_frontend': [
            '/cyllo_base/static/src/scss/email_marketing.scss',
            '/cyllo_base/static/src/scss/website.ui.scss',
        ],

        'hr_attendance.assets_public_attendance': [
            '/cyllo_base/static/src/scss/hr_attendance.scss'
        ],

        'im_livechat.assets_embed_core': [
            '/cyllo_base/static/src/scss/live_chat.ui.scss'
        ],

        'point_of_sale._assets_pos': ['/cyllo_base/static/src/scss/pos_style.scss'],

        'web.qunit_suite_tests': [
            'cyllo_dynamic_field/static/src/tests/form_controller_patch_tests.js',
        ],

        'web_editor.wysiwyg_iframe_editor_assets': [
            '/cyllo_base/static/src/scss/wysiwyg_snippets.scss',
        ],

        'web_editor.assets_wysiwyg': ['/cyllo_base/static/src/scss/wysiwyg_snippets.scss'],

        'web.assets_clickbot': [
            ('replace', 'web/static/src/webclient/clickbot/clickbot.js', '/cyllo_base/static/src/webclient/clickbot/clickbot.js'),
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook'
}
