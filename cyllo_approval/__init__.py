# -*- coding: utf-8 -*-
from . import models
from . import wizard
from lxml import etree

def post_init_load_buttons(env):
    """
    Post-init hook to scan all views, extract all object buttons,
    and store them in ir.model.buttons.
    """
    view_model = env['ir.ui.view']
    button_model = env['ir.buttons']

    views = view_model.search([])

    for view in views:
        try:
            arch = etree.fromstring(view.arch_db)

            for btn in arch.xpath('//button'):
                btn_type = btn.get('type')
                btn_name = btn.get('name')
                btn_string = btn.get('string')

                # Only "object" type buttons need approval logic
                if btn_type == 'object' and btn_name and btn_string:

                    existing = button_model.search([
                        ("name", "=", btn_name),
                        ("view_id", "=", view.id),
                    ], limit=1)

                    if not existing:
                        button_model.create({
                            'name': btn_name,
                            'string': btn_string,
                            'view_id': view.id,
                            'model_id': view.model_id.id,
                        })

        except Exception:
            continue
