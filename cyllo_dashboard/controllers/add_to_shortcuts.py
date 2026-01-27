# -*- coding: utf-8 -*-

from odoo import http

from odoo.http import Controller, request, route


class AddToShortcuts(Controller):
    """Controller for managing user shortcuts."""

    @route('/add_to_shortcuts', type='json', auth='user')
    def add_to_shortcuts(self, actionId, name, model):
        """
            Adds a specific action identified by 'actionId' from the user's
            shortcuts.

            Parameters: actionId (int): The ID of the action to be removed from
                the user's shortcuts.
        """
        request.env['shortcut.menu'].sudo().create({
            'name': name,
            'menu_id': request.env['ir.ui.menu'].sudo().search(
                [('action', 'like', f'ir.actions.act_window,{actionId}')], limit=1).id,
            'window_action_id': actionId,
            'res_model': request.env['ir.model'].sudo().search([('model', '=', model)]).id,
        })
        return True

    @route('/remove_from_shortcuts', type='json', auth='user')
    def remove_from_shortcuts(self, actionId):
        """
            Removes a specific action identified by 'actionId' from the user's
            shortcuts.

            Parameters: actionId (int): The ID of the action to be removed from
            the user's shortcuts.
        """
        request.env['shortcut.menu'].sudo().search([('window_action_id', '=', actionId)]).unlink()
        return True

    @http.route('/get_idle_time/timer', auth='public', type='json')
    def get_idle_time(self):
        """
        Getting the idle time set inside res.user.
        """
        if request.env.user.idle_timer:
            return request.env.user.idle_time
