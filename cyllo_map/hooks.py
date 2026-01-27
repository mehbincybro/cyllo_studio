# -*- coding: utf-8 -*-

def uninstall_hook(env):
    env.ref('contacts.action_contacts').sudo().write({
        'view_mode': 'kanban,tree,form,activity'
    })
