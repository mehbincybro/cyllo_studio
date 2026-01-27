# -*- coding: utf-8 -*-
from odoo.fields import Command


def _post_init_hook(env):
    """ When installing enable the analytic accounting in settings"""
    res_group = env.ref('base.group_user')
    implied_id = env.ref('analytic.group_analytic_accounting')
    res_group.write({'implied_ids': [Command.link(implied_id.id)]})
