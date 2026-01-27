# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.http import request


class IrUiMenu(models.Model):
    """Inherits ir.ui.menu to pass value to js."""
    _inherit = 'ir.ui.menu'

    @api.model
    def get_menu(self):
        """When action not equals None, models are searched using search_read()
        and the list is retrieved."""
        menu_ids = list(self._visible_menu_ids(request.session.debug if request else False))
        if request.session.debug == '1':
            domain = [('action', '!=', None), ('id', 'in', menu_ids)]
        else:
            domain = [('action', '!=', None), ('id', 'in', menu_ids), ('groups_id', '!=', False)]
        search = self.search_read(domain, ['complete_name', 'name', 'groups_id'])
        return search
