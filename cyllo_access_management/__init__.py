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
from . import models
from lxml import etree

def post_init_hook(env):
    post_init_load_buttons(env)
    post_init_load_tabs(env)
    post_init_load_filters(env)

def post_init_load_buttons(env):
    views = env['ir.ui.view'].search([('model', '!=', 'access.manager')])
    for view in views:
        button_model = env["ir.model.buttons"]
        try:
            arch = etree.fromstring(
                view.arch_db)
            for btn in arch.xpath('//button'):
                btn_type = btn.get(
                    'type')
                btn_name = btn.get(
                    'name')
                btn_string = btn.get(
                    'string')

                if btn_type in (
                        'object',
                        'action') and btn_name and btn_string:
                    existing = button_model.search(
                        [("name", "=", btn_name),
                         ("view_id", "=", view.id)],
                        limit=1)
                    if not existing:
                        env[
                            'ir.model.buttons'].create(
                            {
                                'name': btn_name,
                                'string': btn_string,
                                'type': btn_type,
                                'view_id': view.id,
                                'model_id': view.model_id.id,
                            })
        except Exception:
            continue

def post_init_load_tabs(env):
    views = env['ir.ui.view'].search([('model', '!=', 'access.manager')])
    for view in views:
        tab_model = env["ir.model.tabs"]
        try:
            arch = etree.fromstring(
                view.arch_db)
            for page in arch.xpath(
                    '//page'):
                tab_name = page.get(
                    'name') or page.get('string')
                tab_string = page.get(
                    'string')

                if tab_string:
                    existing = tab_model.search(
                        [("name", "=", tab_name),
                         ("view_id", "=", view.id)],
                        limit=1)
                    if not existing:
                        env['ir.model.tabs'].create(
                            {
                                'name': tab_name or tab_string,
                                'string': tab_string,
                                'view_id': view.id,
                                'model_id': view.model_id.id,
                            })
        except Exception:
            continue

def post_init_load_filters(env):
    views = env['ir.ui.view'].search([('model', '!=', 'access.manager')])
    for view in views:
        filter_model = env["ir.model.filters"]
        try:
            arch = etree.fromstring(view.arch_db)
            for flt in arch.xpath('//filter'):
                flt_name = flt.get('name')
                flt_string = flt.get('string')
                if flt_name:
                    existing = filter_model.search(
                        [("name", "=", flt_name),
                         ("view_id", "=", view.id)],
                        limit=1)
                    if not existing:
                        env['ir.model.filters'].create({
                            'name': flt_name,
                            'string': flt_string,
                            'is_group_by': True if flt.get('context') and
                                                   'group_by' in flt.get(
                                'context') else False,
                            'view_id': view.id,
                            'model_id': view.model_id.id
                        })
        except Exception:
            continue
