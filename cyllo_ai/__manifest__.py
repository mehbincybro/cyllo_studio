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
    "name": "Cyllo AI",
    "version": "1.0",
    "summary": "ERP Analytics Chatbot Using LangGraph",
    "category": "Extra Tools",
    'author': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'license': 'LGPL-3',
    "depends": ["base", "web", "cyllo_web", "cyllo_analytics"],
    'icon': '/cyllo_ai/static/src/img/cyllo-ai.png',
    "data": [
            'security/ir.model.access.csv',
            'data/cyllo_llm_data.xml',
            'views/res_config_settings_views.xml',
    ],
    "external_dependencies": {
        'python': [
            'langgraph',
            'langchain-google-genai',
            'langchain-openai',
            'langchain-community',
            'langchain-core',

        ],
    },
    'assets': {
        'web.assets_backend': [
            'https://unpkg.com/lottie-web/build/player/lottie.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css',
            'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
            'https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js',
            'cyllo_ai/static/src/chatsidebar/chatsidebar.js',
            'cyllo_ai/static/src/chatsidebar/chatsidebar.xml',
            'cyllo_ai/static/src/chatsidebar/chatsidebar.css',
            'cyllo_ai/static/src/chatresponse/chatresponse.js',
            'cyllo_ai/static/src/chatresponse/chatresponse.xml',
            'cyllo_ai/static/src/chatresponse/chatresponse.css',
            'cyllo_ai/static/src/chatuser/chatuser.js',
            'cyllo_ai/static/src/chatuser/chatuser.xml',
            'cyllo_ai/static/src/chatuser/chatuser.css',
            'cyllo_ai/static/src/chatbot/chatbot.js',
            'cyllo_ai/static/src/chatbot/chatbot.css',
            'cyllo_ai/static/src/chatbot/chatbot_templates.xml',
            'cyllo_ai/static/src/systray/systray_icon.xml',
            'cyllo_ai/static/src/systray/systray_icon.js',
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False
}
