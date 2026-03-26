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
import inspect

from odoo import http
from odoo.http import request


class CylloAutoWorkController(http.Controller):

    @http.route('/cyllo_auto_work/find/functions', type="json", auth="user", csrf=False)
    def cyllo_auto_work_find_functions(self, **kwargs):
        """
            Find and return a list of 'action' methods in the specified model.

            This method inspects the specified model, identifies methods starting with "action",
            and returns their names along with their argument specifications.

            Args:
               kwargs (dict): Keyword arguments passed to the route, expecting 'model' key
                              to specify the model name.

            Returns:
               list: A list of dictionaries, each containing the following:
                   - 'name': The name of the method.
                   - 'args': A list of argument names the method takes.
            """
        model = request.env[kwargs['model']]
        model_class = type(model)
        methods = []

        for attr_name in dir(model_class):
            attr = getattr(model_class, attr_name)
            if inspect.isfunction(attr) or inspect.ismethod(attr):
                if not attr_name.startswith(("__")) and attr_name.startswith("action"):
                    argspec = inspect.getfullargspec(attr)
                    method_info = {
                        'name': attr_name,
                        'args': argspec.args
                    }
                    methods.append(method_info)

        return methods
