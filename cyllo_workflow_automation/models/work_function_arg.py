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
import base64
import json as _json_lib
import os
import time
import types
from collections import defaultdict
import logging

import requests as _requests_lib
from lxml import etree

from dateutil.relativedelta import relativedelta

from odoo import _, api, exceptions, fields, models, tools
from odoo.exceptions import AccessError
from odoo.tools import file_open
from odoo.tools.safe_eval import _BUILTINS, safe_eval

_logger = logging.getLogger(__name__)


class WorkFunctionArg(models.Model):
    """
        A model representing an argument for a specific work function.

        This class defines an argument (`WorkArg`) that can be associated with
        a work function (`work.function`). It specifies the name and type of the argument,
        along with a reference to the function it belongs to.

        Fields:
            name (Char): The name of the argument (default: 'arg').
            ttype (Selection): The data type of the argument, which can be one of the following:
                - 'dict': Dictionary
                - 'list': List
                - 'tuple': Tuple
                - 'str': String (default)
                - 'int': Integer
                - 'float': Float
                - 'None': None
                - 'set': Set
                - 'bool': Boolean
                - 'record': Record
                - 'recordset': Record set
                - 'other': Other (custom type)
            function_id (Many2one): A reference to the associated work function (`work.function`).

        Model:
            _name: 'work.function.arg'
        """
    _name = "work.function.arg"

    name = fields.Char('Arg name', default='arg')
    ttype = fields.Selection(
        [
            ('dict', 'Dictionary'), ('list', 'List'),
            ('tuple', 'Tuple'), ('str', 'String'),
            ('int', 'Integer'), ('float', 'Float'),
            ('None', 'None'), ('set', 'Set'),
            ('bool', 'Boolean'), ('record', 'Record'),
            ('recordset', 'Record set'), ('other', 'Other'),
        ],
        'Arg Type',
        default='str'
    )
    function_id = fields.Many2one('work.function')


class ProcessArg(models.Model):
    """
        A model representing an argument for a specific work process, inheriting from 'work.function.arg'.

        This class extends the `WorkArg` model by adding additional fields to specify
        whether the argument is related to the 'before' or 'after' stages of a process.
        It also introduces a value field to store the argument's content.

        Fields:
            value (Char): The value or content of the argument.
            is_before (Boolean): A flag indicating whether the argument is used before a process (default: False).
            is_after (Boolean): A flag indicating whether the argument is used after a process (default: False).

        Methods:
            check_is_before: Validates that either `is_before` or `is_after` is set to True.

        Model:
            _name: 'work.process.arg'
            _inherit: 'work.function.arg'
        """
    _name = "work.process.arg"
    _inherit = "work.function.arg"

    value = fields.Char('Value')
    is_before = fields.Boolean('Is Before')
    is_after = fields.Boolean('Is After')

    @api.constrains('is_before', 'is_after')
    def check_is_before(self):
        """
            Ensure that at least one execution phase is selected.

            This constraint validates that either `is_before` or `is_after`
            is set to True for each record. Raises a ValidationError if both
            are False.

            Raises:
                ValidationError: If neither 'is_before' nor 'is_after' is selected.
            """
        for rec in self:
            if not rec.is_before and not rec.is_after:
                raise exceptions.ValidationError('Should give at least Is Before or Is After')


class WorkFunction(models.Model):
    """
        A model representing a function within a workflow automation system.

        The `WorkFunction` class is responsible for defining a specific function that
        can be linked with arguments (`work.function.arg`), processes (`work.process.arg`),
        and other properties like decorators, return types, and triggers. It can be set to run
        in 'manual' or 'auto' mode, and generates the function code automatically if required.

        Fields:
            name (Char): A human-readable name for the function.
            func_name (Char): The internal name of the function (used in function generation).
            decorator (Char): The name of the decorator (e.g., `@api.model`, `@api.multi`, etc.).
            model_id (Many2one): A reference to the `ir.model` the function belongs to.
            make_function (Text): Optional field for manually providing the function code.
            arg_ids (One2many): Arguments associated with this function, linked to `work.function.arg`.
            process_ids (One2many): Processes associated with this function, linked to `work.process.arg`.
            has_return (Boolean): Whether the function has a return statement (default: True).
            c_make_function (Text): The generated or provided function code (computed field).
            mode (Selection): Mode of the function, either 'manual' or 'auto' (computed field).
            trigger_type (Selection): When the function will be triggered, e.g., on record creation, time-based triggers, etc.
            company_id (Many2one): The company associated with the function.
            icon (Binary): An optional SVG icon representing the function.

        Methods:
            _check_icon_file_type: Validates that the uploaded icon is a valid SVG file by checking its content.

            compute_c_make_function: Automatically generates the function code based on the function's name, arguments,
                                     processes, and whether it has a return statement, unless the `make_function` field is provided.
    """
    _name = "work.function"

    name = fields.Char('Name')
    func_name = fields.Char('Function name')
    decorator = fields.Char('decorator name')
    model_id = fields.Many2one('ir.model')
    make_function = fields.Text('Make function')
    arg_ids = fields.One2many('work.function.arg', 'function_id')
    process_ids = fields.One2many('work.process.arg', 'function_id')
    has_return = fields.Boolean('Has return', default=True)
    c_make_function = fields.Text(
        'Make Function',
        compute='compute_c_make_function', store=True
    )
    mode = fields.Selection(
        [('manual', 'Manual'), ('auto', 'Auto')],
        'mode',
        compute='compute_c_make_function'
    )
    trigger_type = fields.Selection(
        [
            ('create', 'On create'),
            ('write', 'On write'),
            ('unlink', 'On delete'),
            ('time', 'At a time'),
            ('new_action', 'New Action'),
            ('field_change', 'On change'),
            ('other', 'Other functions'),
            ('button_click', 'Button Click (Studio)'),
        ],
        default='other'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    icon = fields.Binary()

    @api.model
    def _is_studio_workflow_func_name(self, func_name):
        return bool(func_name and str(func_name).startswith('studio_wf_'))

    @api.model
    def _normalize_button_click_vals(self, vals):
        vals = dict(vals or {})
        if self._is_studio_workflow_func_name(vals.get('func_name')):
            vals['trigger_type'] = 'button_click'
        return vals

    @api.constrains('icon')
    def _check_icon_file_type(self):
        """
            Validate that the uploaded icon is a valid SVG file.

            This method decodes the binary icon field and checks whether the
            content represents a valid SVG structure.

            Raises:
                ValidationError: If the file is not a valid SVG or cannot be verified.
            """
        for record in self:
            if record.icon:
                try:
                    file_content = base64.b64decode(record.icon)
                    if not file_content.startswith(b'<?xml') and not file_content.startswith(b'<svg'):
                        raise exceptions.ValidationError("The uploaded file is not a valid SVG.")
                    if b'<svg' not in file_content[:1000]:
                        raise exceptions.ValidationError("The uploaded file does not appear to be a valid SVG.")
                except:
                    raise exceptions.ValidationError("Unable to verify the file. Please ensure it's a valid SVG.")

    @api.depends('func_name', 'make_function', 'arg_ids', 'process_ids', 'has_return', 'trigger_type')
    def compute_c_make_function(self):
        """
            Compute the executable function code for workflow triggers.

            This method generates Python code dynamically based on the defined
            function configuration, including arguments, decorators, and trigger type.
            If a manual function definition is provided, it is used directly.

            It also determines whether the function is in 'manual' or 'auto' mode.

            Effects:
                - Populates `c_make_function` with generated or manual code.
                - Sets `mode` to 'manual' or 'auto'.
            """
        for rec in self:
            if rec.make_function:
                rec.c_make_function = rec.make_function
                rec.mode = 'manual'
                continue
            rec.mode = 'auto'
            args = ','.join(rec.arg_ids.mapped('name')) if rec.arg_ids else ''
            trigger_value = f"'{rec.trigger_type}'" if rec.trigger_type else 'None'
            process_payload = f"{{'records': self, 'trigger_type': {trigger_value}}}"
            process_before = process_after = process_payload
            decorator = f'@api.{rec.decorator}' if rec.decorator else ''
            if rec.trigger_type == 'button_click' or self._is_studio_workflow_func_name(rec.func_name):
                make_function = f'''
                def make_{rec.func_name}():
                    {decorator}
                    def {rec.func_name}(self{',' if args else ''}{args}):
                        guard_key = '_workflow_{rec.func_name}_running_' + self._name
                        if self.env.context.get(guard_key):
                            return False
                        automation_ids = self.env['work.auto']._get_actions(self, '{rec.func_name}')
                        before_ids = automation_ids.filtered(lambda x: x.ttype == 'before')
                        for automation in before_ids.with_context(old_values=None):
                            automation._process({process_before})
                        after_ids = automation_ids - before_ids
                        for automation in after_ids.with_context(old_values=None):
                            automation._process({process_after})
                        return False
                    return {rec.func_name}
                '''
                rec.c_make_function = make_function.strip()
                continue
            make_function = f'''
            def make_{rec.func_name}():
                {decorator}
                def {rec.func_name}(self{',' if args else ''}{args}):
                    guard_key = '_workflow_{rec.func_name}_running_' + self._name
                    if self.env.context.get(guard_key):
                        return {rec.func_name}.origin(self{',' if args else ''}{args})
                    automation_ids = self.env['work.auto']._get_actions(self, '{rec.func_name}')
                    if not automation_ids:
                        return {rec.func_name}.origin(self{',' if args else ''}{args})
                    before_ids = automation_ids.filtered(lambda x: x.ttype == 'before')
                    for automation in before_ids.with_context(old_values=None):
                        automation._process({process_before})
                    res = {rec.func_name}.origin(self.with_context(**{{guard_key: True}}).with_env(automation_ids.env){',' if args else ''}{args})
                    after_ids = automation_ids - before_ids
                    for automation in after_ids.with_context(old_values=None):
                        automation._process({process_after})
                    {'return res' if rec.has_return else ''}
                return {rec.func_name}
            '''
            rec.c_make_function = make_function.strip()

    @api.model
    def _ensure_button_trigger(self, model_name, func_name):
        if not model_name or not func_name:
            return self.browse()
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', model_name)], limit=1
        )
        if not model_id:
            return self.browse()
        existing = self.sudo().search([
            ('func_name', '=', func_name),
            ('model_id', '=', model_id.id),
            ('trigger_type', '=', 'button_click'),
        ], limit=1)
        if not existing:
            existing = self.sudo().create({
                'name': func_name.replace('studio_wf_', '').replace('_', ' ').title() or 'Button Click (Studio)',
                'func_name': func_name,
                'model_id': model_id.id,
                'trigger_type': 'button_click',
            })
        if self.env.registry.ready:
            self.env['work.auto']._update_registry()
        return existing

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._normalize_button_click_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        vals = self._normalize_button_click_vals(vals)
        return super().write(vals)


class WorkAuto(models.Model):
    _name = "work.auto"
    _inherit = ['image.mixin']

    name = fields.Char("Name")
    function_id = fields.Many2one('work.function')
    model_id = fields.Many2one('ir.model', ondelete="cascade")
    active = fields.Boolean("Active", default=True)
    code = fields.Text('Code')
    imports = fields.Json("Imports")
    trigger_type = fields.Selection(related='function_id.trigger_type')
    ttype = fields.Selection(
        [('before', 'Before'), ('after', 'After')],
        default="after",
        required=True
    )
    field_id = fields.Many2one(
        'ir.model.fields',
        'On Change Field',
        domain="[('model_id', '=', model_id)]"
    )
    time_trigger_mode = fields.Selection([
        ('hour', 'Every Hour'),
        ('day', 'Every Day'),
        ('month', 'Every Month'),
        ('year', 'Every Year')
    ])
    time_trigger_time = fields.Float('Time')
    time_trigger_day = fields.Integer('Day')
    time_trigger_month = fields.Integer('Month')
    schedule_id = fields.Many2one('ir.cron')
    flow_data = fields.Json(string="Flow data")
    context = fields.Char(string="Context")
    variables = fields.Json(string="Variables")
    trigger_function_ids = fields.Many2many(
        'work.function',
        string="Trigger Functions",
        compute='_compute_trigger_functions',
        store=True,
        copy=False,
    )
    is_reusable = fields.Boolean(string="Reusable", default=False)
    # Reusable automations are always generic: they accept whatever record is
    # passed in by the calling workflow.
    reuse_scope = fields.Selection(
        [('generic', 'Generic (any model)')],
        string='Reuse Scope',
        default='generic',
    )
    node_struct_ids = fields.One2many('node.struct', 'work_auto_id')
    image_1920 = fields.Binary(
        string="Image 1920",
        default=lambda self: self.getDefaultImage1920()
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        default=lambda self: self.env.company
    )
    is_record_saved = fields.Boolean(default=False)

    def _archive_workflows_with_whatsapp_nodes(self):
        """
            Archive active workflows containing WhatsApp nodes.

            This method searches for active workflows that include a node
            named 'WhatsApp' and deactivates them.

            Returns:
                recordset: The workflows that were archived.
            """
        workflows = self.sudo().search([
            ('active', '=', True),
            ('node_struct_ids.name', '=', 'WhatsApp'),
        ])
        if workflows:
            workflows.write({'active': False})
        return workflows

    def save_data(self, data, name, ttype, **kwargs):
        """
            Create or update a workflow automation record.

            This method saves workflow data, links detached node structures,
            and determines trigger functions based on the flow definition.

            Args:
                data (dict): Workflow flow data (drawflow structure).
                name (str): Name of the workflow.
                ttype (bool): Determines 'before' or 'after' execution type.
                **kwargs: إضافي parameters such as model_id, code, variables,
                          trigger_function_ids, and image.

            Returns:
                int: ID of the created or updated workflow.
            """
        workflow_auto_id = self or False
        img = kwargs.get('image', False)
        t_ttype = 'before' if ttype else 'after'
        trigger_function_ids = kwargs.get('trigger_function_ids', []) or []

        # ── Link Detached Nodes ───────────────────────────────────────────────
        # When a new automation is created, node.struct records are created first
        # with work_auto_id=False. We must link them now.
        node_ids = []
        if data:
            drawflow = data.get('drawflow', {}) or {}
            home = drawflow.get('Home', {}) or {}
            nodes = home.get('data', {}) or {}
            for node in nodes.values():
                nid = node.get('data', {}).get('nodeId')
                if nid:
                    node_ids.append(nid)

        if not self:
            values = {
                'name': name,
                'flow_data': data,
                'model_id': kwargs.get('model_id', False),
                'code': kwargs.get('code', False),
                'variables': kwargs.get('variables', []),
                'is_reusable': kwargs.get('is_reusable', False),
                'reuse_scope': kwargs.get('reuse_scope', False),
                'ttype': t_ttype,
                'is_record_saved': True,
            }
            workflow_auto_id = self.create(values)
            if node_ids:
                self.env['node.struct'].sudo().browse(node_ids).write({
                    'work_auto_id': workflow_auto_id.id
                })
        else:
            values = {
                'name': name,
                'flow_data': data,
                'model_id': kwargs.get('model_id', False),
                'code': kwargs.get('code', False),
                'variables': kwargs.get('variables', []),
                'is_reusable': kwargs.get('is_reusable', self.is_reusable),
                'reuse_scope': kwargs.get('reuse_scope', self.reuse_scope),
                'ttype': t_ttype,
                'is_record_saved': True,
            }
            self.write(values)
            if node_ids:
                self.env['node.struct'].sudo().browse(node_ids).write({
                    'work_auto_id': self.id
                })

        # Derive triggers from the saved flow itself. This covers both direct
        # trigger nodes and "Reuse Automation" nodes without relying on the
        # one2many cache being refreshed immediately after linking node.struct
        # rows to a freshly created automation.
        automation = workflow_auto_id or self
        if not trigger_function_ids:
            trigger_function_ids = automation._extract_trigger_function_ids_from_flow(
                data or automation.flow_data
            )

        if trigger_function_ids:
            target_function = trigger_function_ids[0]
            automation.write({
                'trigger_function_ids': [(6, 0, trigger_function_ids)],
                'function_id': target_function,
            })
        else:
            automation.write({
                'trigger_function_ids': [(5, 0, 0)],
                'function_id': False,
            })

        return automation.id

    def clear_all_nodes(self):
        """
            Remove all node structures linked to this workflow.

            Deletes all associated `node.struct` records.
            """
        self.node_struct_ids.unlink()
        return

    def update_flow_data(self, flow_data):
        """
            Update the workflow flow data.

            Args:
                flow_data (dict): Updated drawflow data.

            Returns:
                int: ID of the workflow record.
            """
        self.flow_data = flow_data
        return self.id

    def _extract_trigger_function_ids_from_flow(self, flow_data):
        """
            Extract trigger function IDs from workflow flow data.

            Parses the drawflow structure to identify trigger nodes and
            reusable automation nodes, collecting their associated function IDs.

            Args:
                flow_data (dict): Workflow flow configuration.

            Returns:
                list: Unique list of function IDs.
            """
        if not flow_data:
            return []
        drawflow = flow_data.get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        nodes = home.get('data', {}) or {}
        function_ids = []
        seen_trigger_types = set()
        for node in nodes.values():
            data = node.get('data') or {}
            node_type = data.get('type')

            # 1. Direct Trigger Nodes (type='action')
            if node_type == 'action':
                model_info = data.get('model')
                trigger_type = data.get('trigger_type')
                if trigger_type and trigger_type in seen_trigger_types:
                    continue
                if isinstance(model_info, (list, tuple)) and model_info:
                    func_id = model_info[0]
                elif isinstance(model_info, dict):
                    func_id = model_info.get('id')
                else:
                    func_id = False
                if isinstance(func_id, int) and not isinstance(func_id, bool):
                    function_ids.append(func_id)
                    if trigger_type:
                        seen_trigger_types.add(trigger_type)

            # 2. Reuse Automation Nodes (type='action_to_do')
            elif node_type == 'action_to_do' and data.get('name') == 'Reuse Automation':
                node_id = data.get('nodeId')
                if node_id:
                    struct_node = self.env['node.struct'].sudo().browse(node_id)
                    if struct_node.reused_work_auto_id:
                        inherited = struct_node.reused_work_auto_id.trigger_function_ids.ids
                        function_ids.extend(inherited)

        return list(dict.fromkeys(function_ids))

    def _get_test_node_order(self):
        """
            Return workflow nodes in execution-like traversal order.

            Uses the persisted drawflow graph to walk from root nodes through
            outgoing connections in output order, then appends any disconnected
            nodes that were not reached.
        """
        self.ensure_one()
        flow_data = self.flow_data or {}
        drawflow = flow_data.get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        nodes = home.get('data', {}) or {}
        if not nodes:
            return self.env['node.struct']

        node_by_struct_id = {}
        incoming_counts = defaultdict(int)
        adjacency = defaultdict(list)

        def _output_sort_key(item):
            label = item[0] or ''
            if '_' in label:
                try:
                    return int(label.split('_')[-1])
                except ValueError:
                    return label
            return label

        for draw_node_id, draw_node in nodes.items():
            node_data = draw_node.get('data') or {}
            struct_id = node_data.get('nodeId')
            if struct_id:
                node_by_struct_id[int(struct_id)] = draw_node
            outputs = draw_node.get('outputs', {}) or {}
            for _output_name, output in sorted(outputs.items(), key=_output_sort_key):
                for connection in output.get('connections', []) or []:
                    target_draw_id = str(connection.get('node'))
                    if target_draw_id in nodes:
                        adjacency[str(draw_node_id)].append(target_draw_id)
                        incoming_counts[target_draw_id] += 1

        root_ids = []
        for draw_node_id, draw_node in nodes.items():
            if incoming_counts.get(str(draw_node_id), 0) == 0:
                root_ids.append(str(draw_node_id))
        if not root_ids:
            root_ids = list(nodes.keys())

        ordered_struct_ids = []
        visited_draw_ids = set()

        def _visit(draw_node_id):
            key = str(draw_node_id)
            if key in visited_draw_ids:
                return
            visited_draw_ids.add(key)
            draw_node = nodes.get(key) or {}
            struct_id = (draw_node.get('data') or {}).get('nodeId')
            if struct_id:
                ordered_struct_ids.append(int(struct_id))
            for child_id in adjacency.get(key, []):
                _visit(child_id)

        for root_id in root_ids:
            _visit(root_id)
        for draw_node_id in nodes.keys():
            _visit(draw_node_id)

        if not ordered_struct_ids:
            return self.node_struct_ids.sorted('id')

        node_map = {node.id: node for node in self.node_struct_ids}
        return self.env['node.struct'].browse(
            [node_id for node_id in ordered_struct_ids if node_id in node_map]
        )

    def _get_test_graph_issues(self):
        """
            Detect disconnected workflow branches for test mode.

            Returns:
                dict: Mapping of node.struct id -> validation error message.
        """
        self.ensure_one()
        flow_data = self.flow_data or {}
        drawflow = flow_data.get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        nodes = home.get('data', {}) or {}
        if not nodes:
            return {}

        is_generic_reusable = bool(self.is_reusable and self.reuse_scope == 'generic')
        executable_nodes = {}
        trigger_draw_ids = []
        adjacency = defaultdict(list)
        incoming_counts = defaultdict(int)
        model_reuse_roots = set()

        for draw_node_id, draw_node in nodes.items():
            node_data = draw_node.get('data') or {}
            if node_data.get('type') == 'model':
                continue
            draw_key = str(draw_node_id)
            executable_nodes[draw_key] = node_data
            adjacency.setdefault(draw_key, [])
            if node_data.get('type') == 'action':
                trigger_draw_ids.append(draw_key)

        if not executable_nodes:
            issues = {}
            for node_data in (draw_node.get('data') or {} for draw_node in nodes.values()):
                struct_id = node_data.get('nodeId')
                if struct_id:
                    issues[int(struct_id)] = _(
                        "Add at least one trigger and connect it to a workflow step before testing."
                    )
            return issues

        for draw_node_id, draw_node in nodes.items():
            node_data = draw_node.get('data') or {}
            if node_data.get('type') == 'model':
                outputs = draw_node.get('outputs', {}) or {}
                for output in outputs.values():
                    for connection in output.get('connections', []) or []:
                        target_id = str(connection.get('node'))
                        target_node = nodes.get(target_id, {}) or {}
                        target_data = target_node.get('data') or {}
                        if (
                            target_data.get('type') == 'action_to_do' and
                            target_data.get('name') == 'Reuse Automation'
                        ):
                            model_reuse_roots.add(target_id)
                continue
            draw_key = str(draw_node_id)
            outputs = draw_node.get('outputs', {}) or {}
            for output in outputs.values():
                for connection in output.get('connections', []) or []:
                    target_id = str(connection.get('node'))
                    target_node = nodes.get(target_id, {}) or {}
                    target_data = target_node.get('data') or {}
                    if target_data.get('type') == 'model' or target_id not in executable_nodes:
                        continue
                    adjacency[draw_key].append(target_id)
                    incoming_counts[target_id] += 1

        issues = {}
        direct_reuse_root_ids = [
            draw_node_id for draw_node_id, node_data in executable_nodes.items()
            if (
                node_data.get('type') == 'action_to_do' and
                node_data.get('name') == 'Reuse Automation' and
                draw_node_id in model_reuse_roots
            )
        ]

        if not trigger_draw_ids and not direct_reuse_root_ids and not is_generic_reusable:
            for node_data in executable_nodes.values():
                struct_id = node_data.get('nodeId')
                if struct_id:
                    issues[int(struct_id)] = _("Add at least one trigger before testing the workflow.")
            return issues

        if is_generic_reusable:
            root_draw_ids = [
                draw_node_id for draw_node_id in executable_nodes
                if incoming_counts.get(draw_node_id, 0) == 0
            ]
            if not root_draw_ids and executable_nodes:
                root_draw_ids = [next(iter(executable_nodes))]
            if len(root_draw_ids) > 1:
                for draw_node_id in root_draw_ids:
                    node_data = executable_nodes[draw_node_id]
                    struct_id = node_data.get('nodeId')
                    label = node_data.get('label') or node_data.get('name') or _("Node")
                    if struct_id:
                        issues[int(struct_id)] = _(
                            "%s is disconnected from the reusable workflow. Connect it before testing."
                        ) % label
                return issues
        else:
            root_draw_ids = list(dict.fromkeys(trigger_draw_ids + direct_reuse_root_ids))

        reachable = set()

        def _visit(draw_node_id):
            draw_key = str(draw_node_id)
            if draw_key in reachable:
                return
            reachable.add(draw_key)
            for child_id in adjacency.get(draw_key, []):
                _visit(child_id)

        for root_draw_id in root_draw_ids:
            _visit(root_draw_id)

        if not is_generic_reusable:
            for trigger_draw_id in trigger_draw_ids:
                if adjacency.get(trigger_draw_id):
                    continue
                struct_id = executable_nodes[trigger_draw_id].get('nodeId')
                label = (
                    executable_nodes[trigger_draw_id].get('label')
                    or executable_nodes[trigger_draw_id].get('name')
                    or _("Trigger")
                )
                if struct_id:
                    issues[int(struct_id)] = _("%s is not connected to any workflow step.") % label

        for draw_node_id, node_data in executable_nodes.items():
            if node_data.get('type') == 'action':
                continue
            if draw_node_id in reachable:
                continue
            struct_id = node_data.get('nodeId')
            label = node_data.get('label') or node_data.get('name') or _("Node")
            if struct_id:
                issues[int(struct_id)] = _(
                    "%s is disconnected from the workflow. Connect it to a trigger path before testing."
                ) % label

        return issues

    def dry_run(self):
        """
            Validate workflow nodes without executing side effects.

            Returns:
                dict: Summary payload with node-level validation results.
        """
        self.ensure_one()
        is_generic_reusable = bool(self.is_reusable and self.reuse_scope == 'generic')
        if not self.is_record_saved:
            raise exceptions.ValidationError(
                _("Save the workflow before running a test.")
            )
        if not is_generic_reusable and not self.model_id:
            raise exceptions.ValidationError(
                _("Select an object before running a test.")
            )

        results = []
        counts = {
            'success': 0,
            'error': 0,
            'warning': 0,
        }
        flow_nodes = {}
        drawflow = (self.flow_data or {}).get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        if not (home.get('data') or {}):
            raise exceptions.ValidationError(
                _("Add at least one trigger and connect it to a workflow step before testing.")
            )
        for draw_node in (home.get('data', {}) or {}).values():
            node_data = draw_node.get('data') or {}
            struct_id = node_data.get('nodeId')
            if struct_id:
                flow_nodes[int(struct_id)] = node_data
        graph_issues = self._get_test_graph_issues()

        external_nodes = {'Mail', 'SMS', 'WhatsApp', 'Window', 'Webhook'}
        trigger_labels = {'On Create', 'On Write', 'On Unlink', 'On Field Change', 'On Time'}

        def _is_empty(value):
            if value in (False, None):
                return True
            if isinstance(value, str):
                return not value.strip()
            if isinstance(value, (list, tuple, dict, set)):
                return len(value) == 0
            return False

        def _has_configured_create_value(entry):
            if not isinstance(entry, dict):
                return not _is_empty(entry)
            value_key = 'field_value' if 'field_value' in entry else 'value'
            if value_key not in entry:
                return False
            value = entry.get(value_key)
            field_type = entry.get('type')
            if field_type == 'boolean':
                return True
            if field_type in ('integer', 'float', 'monetary'):
                return value not in (None, False, '')
            return not _is_empty(value)

        def _get_create_validation(node):
            required_fields = node.create_required_field or []
            provided = node.create_req_fields_values or []
            tree_values = node.create_tree_fields_values or []

            if not node.model_id:
                return 'error', _("Select a model to create records.")

            if not required_fields:
                if provided or tree_values:
                    return 'success', _("Create values configured.")
                return 'error', _("Add at least one field to create.")

            filled_names = set()
            for entry in provided:
                if not isinstance(entry, dict):
                    continue
                field_name = (
                    entry.get('name') or entry.get('field_name') or
                    entry.get('technical_name') or entry.get('value')
                )
                if field_name and _has_configured_create_value(entry):
                    filled_names.add(field_name)

            for field in required_fields:
                if not isinstance(field, dict):
                    continue
                field_name = (
                    field.get('name') or field.get('field_name') or
                    field.get('technical_name')
                )
                if field_name and _has_configured_create_value(field):
                    filled_names.add(field_name)

            missing = []
            for field in required_fields:
                if isinstance(field, dict):
                    field_name = (
                        field.get('name') or field.get('field_name') or
                        field.get('technical_name')
                    )
                else:
                    field_name = field
                if field_name and field_name not in filled_names:
                    missing.append(field_name)
            if not missing:
                return 'success', _("Create values configured.")

            if tree_values:
                return (
                    'warning',
                    _("Required create fields are missing in test input: %s. Node was simulated without creating data.") % ', '.join(missing)
                )

            return (
                'warning',
                _("Mandatory create fields are not mapped for test mode: %s. Add sample values to fully validate this node.") % ', '.join(missing)
            )

        def _validate_node(node):
            label = node.label or node.name or _("Node")
            node_name = node.name or ''
            flow_node = flow_nodes.get(node.id, {})
            flow_node_type = flow_node.get('type')

            if node.id in graph_issues:
                return 'error', graph_issues[node.id]

            if node.type == 'model':
                return 'success', _("Object selected.")
            if node.type in ('action', 'trigger') or flow_node_type == 'action':
                trigger_type = node.trigger_type or flow_node.get('trigger_type')
                trigger_label = node.ttype or flow_node.get('ttype') or node_name
                model_info = flow_node.get('model')
                has_function_link = (
                    isinstance(model_info, (list, tuple)) and bool(model_info and model_info[0])
                ) or (
                    isinstance(model_info, dict) and bool(model_info.get('id'))
                )
                if trigger_type or trigger_label in trigger_labels or has_function_link:
                    return 'success', _("Trigger configured.")
                return 'error', _("Select a trigger type.")
            if node_name == 'Window':
                if node.window_action_id:
                    return 'success', _("Window action configured.")
                return 'error', _("Select a window action to open.")
            if node_name in external_nodes:
                return 'success', _("Validated in test mode. It will execute during real workflow runtime.")
            if node_name == 'Condition':
                if not _is_empty(node.condition_tree_value):
                    return 'success', _("Condition configured.")
                return 'error', _("Add a condition before testing.")
            if node_name == 'Loop':
                if not _is_empty(node.loop_collection):
                    return 'success', _("Loop source configured.")
                return 'error', _("Choose a loop collection.")
            if node_name == 'Create':
                return _get_create_validation(node)
            if node_name == 'Write':
                if not _is_empty(node.write_selected_record) and not _is_empty(node.write_field_value):
                    return 'success', _("Write target configured.")
                return 'error', _("Choose a record and at least one field to write.")
            if node_name == 'Variable':
                if node.variable_name and not _is_empty(node.variable_value):
                    return 'success', _("Variable configured.")
                return 'error', _("Set both variable name and value.")
            if node_name == 'Activity':
                if not _is_empty(node.activity_type) and not _is_empty(node.activity_user):
                    return 'success', _("Activity configured.")
                return 'error', _("Select an activity type and responsible user.")
            if node_name == 'Warning':
                if node.warning_type and node.warning_text:
                    return 'success', _("Warning configured.")
                return 'error', _("Add a warning type and message.")
            if node_name == 'Search':
                has_tree_domain = (
                    isinstance(node.search_domain_tree, dict)
                    and bool(node.search_domain_tree.get('children'))
                )
                if not _is_empty(node.search_domain) or has_tree_domain:
                    return 'success', _("Search domain configured.")
                return 'error', _("Define a search domain.")
            if node_name == 'Code':
                if _is_empty(node.code_code):
                    return 'error', _("Add Python code to validate.")
                try:
                    compile(node.code_code.strip(), '<workflow_test>', 'exec')
                except Exception as exc:
                    return 'error', _("Code syntax error: %s") % exc
                return 'success', _("Code syntax is valid.")
            if node_name == 'Button Click':
                if not _is_empty(node.function_name):
                    return 'success', _("Function configured.")
                return 'error', _("Select a function to call.")
            if node_name == 'Reuse Automation':
                reused = node.reused_work_auto_id
                if reused and reused.active:
                    return 'success', _("Reusable automation is available.")
                return 'error', _("Select an active reusable automation.")
            if node_name == 'Follower':
                if not _is_empty(node.followers):
                    return 'success', _("Followers configured.")
                return 'error', _("Select at least one follower.")
            if node_name == 'Duplicate':
                if not _is_empty(node.duplicate_record):
                    return 'success', _("Duplicate record configured.")
                return 'error', _("Select a record to duplicate.")
            if node_name == 'Webhook':
                if _is_empty(node.webhook_url):
                    return 'error', _("Webhook URL is required.")
                action_count = len(node.webhook_actions or [])
                if action_count:
                    return 'success', _(
                        "Webhook configured with %d response action(s)."
                    ) % action_count
                return 'success', _("Webhook configured (no response actions).")
            if node_name == 'Try Catch':
                err_var = (node.try_catch_error_variable or '').strip()
                err_types = (node.try_catch_error_types or '').strip()
                if not err_var:
                    return 'error', _("Set an error variable name for the Try/Catch node.")
                if not err_types:
                    return 'error', _("Specify at least one exception type to catch.")
                return 'success', _(
                    "Try/Catch configured — catches %s as '%s'."
                ) % (err_types, err_var)
            if node.code and node.code.strip():
                return 'success', _("%s configured.") % label
            return 'error', _("%s is not configured.") % label

        node_order = self._get_test_node_order()
        record_info = False

        try:
            with self.env.cr.savepoint():
                recordset = self.env[self.model_id.model].search([], limit=1) if self.model_id else self.env['res.partner'].browse()
                if recordset:
                    record_info = {
                        'id': recordset.id,
                        'display_name': recordset.display_name,
                    }

                for node in node_order:
                    start_time = time.perf_counter()
                    status, message = _validate_node(node)
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    counts[status] = counts.get(status, 0) + 1
                    results.append({
                        'node_id': node.id,
                        'name': node.name,
                        'label': node.label or node.name,
                        'status': status,
                        'message': message,
                        'duration_ms': duration_ms,
                    })
                raise exceptions.UserError("__cyllo_test_workflow_rollback__")
        except exceptions.UserError as exc:
            if exc.args and exc.args[0] != "__cyllo_test_workflow_rollback__":
                raise

        return {
            'results': results,
            'summary': {
                'total': len(results),
                'success': counts.get('success', 0),
                'error': counts.get('error', 0),
                'warning': counts.get('warning', 0),
            },
            'record': record_info,
        }

    @api.depends('flow_data')
    def _compute_trigger_functions(self):
        """
           Compute trigger functions based on workflow flow data.

           Updates the `trigger_function_ids` field by extracting function IDs
           from the workflow configuration.
           """
        for automation in self:
            function_ids = automation._extract_trigger_function_ids_from_flow(automation.flow_data)
            automation.trigger_function_ids = self.env['work.function'].browse(function_ids)

    @api.constrains('trigger_function_ids')
    def _check_unique_trigger_types(self):
        """
            Ensure unique trigger types within a workflow.

            Prevents multiple functions with the same trigger type from being
            assigned to a single workflow.

            Raises:
                ValidationError: If duplicate trigger types are found.
            """
        for automation in self:
            trigger_types = [
                fn.trigger_type for fn in automation.trigger_function_ids if fn.trigger_type
            ]
            duplicates = [t for t in set(trigger_types) if trigger_types.count(t) > 1]
            if duplicates:
                duplicate_type = duplicates[0]
                trigger = automation.trigger_function_ids.filtered(
                    lambda f: f.trigger_type == duplicate_type
                )
                trigger_name = trigger and trigger[0].name or duplicate_type
                raise exceptions.ValidationError(
                    _("Trigger %s is already part of this automation. "
                      "Each trigger type can only be used once.") % trigger_name
                )

    def initial_model_setup(self):
        """
            Prepare initial model configuration for workflow nodes.

            Identifies primary model and search nodes and returns their
            configuration details.

            Returns:
                list: List of dictionaries describing node setup.
            """
        data = []
        for node in self.node_struct_ids:
            if node.name in ['model', 'Search']:
                data.append({
                    'id': int(node.id) if node.name == 'Search' else 0,
                    'model_id': int(node.model_id),
                    'type': 'primary' if node.name == 'model' else 'Search'
                })
        return data

    def getDefaultImage1920(self):
        """
            Load the default workflow image.

            Reads a default SVG image from module static files and encodes it.

            Returns:
                str: Base64-encoded SVG image.
            """
        with file_open(
                'cyllo_workflow_automation/static/src/img/Record/default_record.svg',
                'rb') as svg_file:
            svg_data = svg_file.read()
            return base64.b64encode(svg_data).decode('utf-8')

    def _register_hook(self):
        """
        Register workflow automation hooks on target models.

        Model._onchange_methods is initialized once during model class creation
        and shared across runtime access, so appending handlers updates the
        registry in place and keeps the trigger active.

            Model._onchange_methods[field_name].append(handler)

        When a watched field changes in the form view, all registered handlers
        for that field are executed automatically before record persistence.

        On Create / Write / Unlink — patch the corresponding ORM methods on
        the target ModelClass.
        """
        patched_models = defaultdict(set)
        patched_function_ids = set()

        def patch(model, name, method):
            """Patch method `name` on `model` unless already patched."""
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = type(model)
                method.origin = getattr(ModelClass, name, None)
                setattr(ModelClass, name, method)

        def make_button_click_method(function):
            func_name = function.func_name

            def button_click(self, *args, **kwargs):
                guard_key = f'_workflow_{func_name}_running_' + self._name
                if self.env.context.get(guard_key):
                    return False
                automation_ids = self.env['work.auto']._get_actions(self, func_name)
                before_ids = automation_ids.filtered(lambda x: x.ttype == 'before')
                action_result = False
                for automation in before_ids.with_context(old_values=None):
                    res = automation._process({'records': self, 'trigger_type': 'button_click'})
                    if isinstance(res, dict) and 'type' in res:
                        action_result = res
                after_ids = automation_ids - before_ids
                for automation in after_ids.with_context(old_values=None):
                    res = automation._process({'records': self, 'trigger_type': 'button_click'})
                    if isinstance(res, dict) and 'type' in res:
                        action_result = res
                return action_result or False

            button_click.__name__ = func_name
            return button_click

        for auto in self.with_context(active_test=False).search([('active', '=', True)]):
            functions = auto.trigger_function_ids
            if not functions:
                continue
            Model = self.env.get(auto.model_id.model)
            if Model is None:
                _logger.warning(
                    "Automation '%s' (ID %d) depends on model %s which does not exist.",
                    auto.name, auto.id,
                    auto.model_id.model if auto.model_id else 'unknown',
                )
                continue

            # ── On Field Change ───────────────────────────────────────────────
            field_change_functions = functions.filtered(
                lambda f: f.trigger_type == 'field_change'
            )
            if field_change_functions:
                if not auto.field_id:
                    _logger.warning(
                        "Automation '%s' (ID %d) has a field-change trigger but "
                        "no 'field_id' configured — skipping.",
                        auto.name, auto.id,
                    )
                else:
                    field_name = auto.field_id.name

                    def make_onchange_fn(watched_auto, watched_field):
                        def on_change_field(rec):
                            """ Guard: only fire for existing saved records.
                            rec is a virtual NewId record in all onchange calls.
                            rec._origin is the real DB record for existing records,
                            or an empty recordset when creating a new record.
                            Skip when there is no real DB record to avoid raising
                            errors (ValidationError, res_id=0, etc.) that block
                            new record creation."""
                            origin = getattr(rec, '_origin', None)
                            if not origin or not origin.id:
                                return

                            # Pass origin (the real saved record) so that
                            # current_record in generated code points to the
                            # actual DB record, not the virtual copy.
                            # trigger_type enables the per-branch code guard.
                            auto_live = watched_auto.with_env(rec.env)
                            try:
                                with rec.env.cr.savepoint():
                                    auto_live._process({
                                        'record': origin,
                                        'records': origin,
                                        'trigger_type': 'field_change',
                                    })
                            except exceptions.ValidationError:
                                raise  # Surface warnings to the form
                            except Exception as exc:
                                _logger.error(
                                    "Field-change automation '%s' failed "
                                    "for record %s on field '%s': %s",
                                    watched_auto.name, origin.id, watched_field, exc,
                                )
                        on_change_field._is_workflow_automation = True
                        return on_change_field

                    # Remove stale handlers before re-appending to prevent
                    # accumulation across multiple _update_registry() calls.
                    existing = Model._onchange_methods.get(field_name, [])
                    Model._onchange_methods[field_name] = [
                        fn for fn in existing
                        if not getattr(fn, '_is_workflow_automation', False)
                    ]
                    Model._onchange_methods[field_name].append(
                        make_onchange_fn(auto, field_name)
                    )

            # ── Create / Write / Unlink and other ORM triggers ────────────────
            for function in functions.filtered(
                lambda f: f.trigger_type not in ('field_change', 'time')
            ):
                if function.trigger_type == 'button_click' or self.env['work.function']._is_studio_workflow_func_name(function.func_name):
                    func = make_button_click_method(function)
                else:
                    if not function.c_make_function:
                        continue
                    code_obj = compile(function.c_make_function, '<string>', 'exec')
                    func = types.FunctionType(
                        code_obj.co_consts[0], globals(), function.func_name
                    )()
                patch(Model, function.func_name, func)
                patched_function_ids.add(function.id)

        for function in self.env['work.function'].with_context(active_test=False).search([]):
            if function.id in patched_function_ids or not function.model_id:
                continue
            if not (
                function.trigger_type == 'button_click'
                or self.env['work.function']._is_studio_workflow_func_name(function.func_name)
            ):
                continue
            Model = self.env.get(function.model_id.model)
            if Model is None:
                continue
            func = make_button_click_method(function)
            patch(Model, function.func_name, func)

        return super()._register_hook()

    def get_dependents(self):
        """
        Return the names and IDs of all ACTIVE automations that reference this
        reusable automation via a 'Reuse Automation' node.
        Returns a list of dicts: [{'id': int, 'name': str}, ...]
        """
        self.ensure_one()
        dependent_nodes = self.env['node.struct'].sudo().search([
            ('reused_work_auto_id', '=', self.id),
        ])
        dependent_autos = dependent_nodes.mapped('work_auto_id').filtered(
            lambda a: a.active and a.id != self.id
        )
        return [{'id': a.id, 'name': a.name} for a in dependent_autos]

    @api.model
    def _get_actions(self, record, func):
        """
           Retrieve applicable workflow automations for a given record and function.

           Args:
               record (recordset): Target record.
               func (str): Function name triggering the automation.

           Returns:
               recordset: Matching active workflow automations.
           """
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', record._name)], limit=1
        )
        function_ids = self.env['work.function'].search([
            ('model_id', 'in', [model_id.id, False]),
            ('func_name', '=', func),
        ])
        if not model_id or not function_ids:
            return self
        auto_ids = self.search([
            ('model_id', '=', model_id.id),
            ('active', '=', True),
            ('trigger_function_ids', 'in', function_ids.ids),
        ])
        return auto_ids

    def _process(self, args: dict):
        """
            Execute workflow automation logic.

            Handles execution of workflow code with safeguards such as:
                - Circular reuse detection
                - Deduplication of repeated triggers
                - Access validation
                - Context preparation for safe execution

            Args:
                args (dict): Execution context including records, trigger type, etc.

            Raises:
                ValidationError: If execution fails or circular dependency is detected.
            """
        # ── Active guard for reuse calls ──────────────────────────────────────
        # If this automation is invoked as a reusable automation from another
        # workflow, check self.active first. If it has been deactivated, skip
        # silently so the parent workflow continues uninterrupted.
        _pre_stack = args.get('__workflow_stack__', [])
        if _pre_stack and not self.active:
            _logger.warning(
                "Reusable automation '%s' (ID %d) is inactive — skipping reuse call "
                "from stack %s.",
                self.name, self.id, _pre_stack,
            )
            return

        # ── Reuse-guard: block circular automation chains ─────────────────────
        stack = args.get('__workflow_stack__', [])
        if not isinstance(stack, list):
            stack = list(stack)
        if self.id in stack:
            raise exceptions.ValidationError(
                _('Circular automation reuse detected for %s.', self.name)
            )
        stack = [*stack, self.id]
        args = dict(args, __workflow_stack__=stack)

        incoming_trigger = args.get('trigger_type', '')
        records = args.get('records', False)

        # ── Normalise time-trigger args ───────────────────────────────────────
        # Scheduled workflows are attached to a model but don't receive an
        # incoming recordset from ir.cron. Resolve the workflow model records so
        # downstream nodes such as Activity can operate on actual records.
        if incoming_trigger == 'time' and not records and self.model_id:
            model_name = self.model_id.sudo().model
            records = self.env[model_name].search([])
            args = dict(args, records=records, current_record=records)

        # ── Empty recordset safety guard ──────────────────────────────────────
        # Skip execution of triggers if the recordset is empty (no records).
        # This prevents Expected singleton or access errors in downstream nodes
        # when background actions write to empty recordsets.
        if hasattr(records, '_name') and not records:
            _logger.info(
                "Skipping workflow automation '%s' (ID %d) because the target recordset is empty.",
                self.name, self.id
            )
            return

        # ── Transaction-level dedup (create / write / unlink only) ────────────
        # Prevents N duplicate actions when write() is triggered multiple times
        # per single form save (computed fields, chatter, state machine).
        # field_change is deliberately excluded — it fires from the onchange
        # RPC which is a single call per user interaction.
        # Only dedup top-level automations (direct ORM triggers).
        # Reusable automations called from another automation have a non-empty
        # __workflow_stack__ — skip dedup for them so they always execute.
        is_reuse_call = len(stack) > 1  # stack has at least [parent_id, self.id]
        if records and incoming_trigger and incoming_trigger != 'field_change' and not is_reuse_call:
            cr = self.env.cr
            if not hasattr(cr, '_workflow_done'):
                cr._workflow_done = set()
            try:
                rec_ids = tuple(sorted(records._ids))
            except Exception:
                rec_ids = ()
            dedup_key = (self.id, rec_ids, incoming_trigger)
            if dedup_key in cr._workflow_done:
                return
            cr._workflow_done.add(dedup_key)

        # ── Access check (skip for field_change and unlink) ───────────────────
        # field_change passes a virtual onchange record — checking write access
        # on a virtual record raises errors. Skip it.
        if records and incoming_trigger not in ('field_change', 'unlink'):
            try:
                records.check_access_rule('write')
            except AccessError:
                _logger.warning(
                    "Forbidden action %r executed while the user %s does not "
                    "have access to %s.",
                    self.name, self.env.user.login, records
                )
                raise

        # ── Normalise field_change args ───────────────────────────────────────
        # on_change_field passes {'record': rec} (singular).
        # Inject 'records' and 'current_record' so the generated code can use
        # either alias.
        single_record = args.get('record', False)
        if single_record and not records:
            args = dict(args)
            args['records'] = single_record
            args['current_record'] = single_record

        # ── Reuse call trigger override ───────────────────────────────────────
        # When this automation is called as a reuse call from another workflow,
        # the frontend sends the REUSED automation's own trigger_type as a
        # literal string (e.g. 'create' for an On-Create automation).
        #
        # Backend safety net: if the incoming trigger is the sentinel value
        # '__reuse__' (used for generic reusable automations that have no
        # trigger), we override it with self.trigger_type so the internal code
        # guard matches correctly. If self.trigger_type is also empty (truly
        # generic), we set it to '__reuse__' which simply won't match any
        # `if trigger_type == 'create':` guard — that is correct because
        # generic reusable code is generated WITHOUT a trigger guard at all.
        #
        # For non-generic reusables where the frontend correctly passes the
        # reused automation's trigger_type (e.g. 'create'), no override is
        # needed — the guard will match as expected.
        if is_reuse_call and incoming_trigger == '__reuse__':
            # Generic reusable: override with the automation's own trigger_type.
            # If self.trigger_type is False/empty, keep '__reuse__' as-is
            # (harmless since generic code has no trigger guard).
            effective_trigger = self.trigger_type or '__reuse__'
            args = dict(args, trigger_type=effective_trigger)
            incoming_trigger = effective_trigger

        # Resolve records now (may have been set by normalise block above)
        resolved_records = args.get('records', False)
        context = self.get_context(records=resolved_records)
        context.update(args)
        context['trigger_type'] = args.get('trigger_type')
        context.update(_BUILTINS)

        def _safe_schedule_activity(rec, **kwargs):
            """Schedule an activity only for real DB records (id > 0)."""
            if not rec:
                return False
            valid = rec.filtered(lambda r: isinstance(r.id, int) and r.id > 0)
            if not valid:
                return False
            return valid.activity_schedule(**kwargs)

        context['_safe_schedule_activity'] = _safe_schedule_activity

        if self.code:
            code_obj = compile(self.code.strip(), "", 'exec')
            try:
                local_dict = {}
                eval(code_obj, context, local_dict)
                if 'action' in local_dict:
                    context['action'] = local_dict['action']
            except Exception as e:
                import traceback as _tb
                _logger.error(
                    "Workflow '%s' code execution error:\n%s",
                    getattr(self, 'name', '?'),
                    _tb.format_exc()
                )
                err_str = str(e)
                if 'mail_activity_check_res_id_is_set' in err_str or (
                    'mail_activity' in err_str and 'res_id' in err_str
                ):
                    _logger.warning(
                        "Workflow '%s' tried to schedule an activity with "
                        "res_id=0 — re-save the workflow to fix this.",
                        self.name
                    )
                    return
                if isinstance(
                    e,
                    (
                        exceptions.UserError,
                        exceptions.ValidationError,
                        exceptions.AccessError,
                        exceptions.AccessDenied,
                        exceptions.MissingError,
                    ),
                ):
                    raise
                raise exceptions.ValidationError(e)
            
            return context.get('action')

    def get_context(self, records=None):
        """
            Build execution context for workflow evaluation.

            Provides environment variables, utilities, and safe helpers for
            executing workflow code.

            Args:
                records (recordset, optional): Target records.

            Returns:
                dict: Execution context dictionary.
            """
        # For generic reusable automations (no fixed model), resolve the model
        # from the records that were passed in by the calling workflow.
        if self.is_reusable and self.reuse_scope == 'generic' and records:
            model = records
        elif self.model_id:
            model = self.env[self.model_id.sudo().model]
        else:
            model = self.env['res.partner']  # safe fallback
        rec = records if records else model.browse()
        if hasattr(rec, '_name') and len(rec) > 1:
            rec = rec[:1]

        return {
            'env': self.env,
            'model': model,
            'records': records,
            'record': rec,
            'current_record': rec,
            'UserError': exceptions.UserError,
            'ValidationError': exceptions.ValidationError,
            'uid': self._uid,
            'user': self.env.user,
            'time': tools.safe_eval.time,
            'datetime': tools.safe_eval.datetime,
            'dateutil': tools.safe_eval.dateutil,
            'relativedelta': relativedelta,
            'fields': fields,
            '_logger': _logger,
            'requests': _requests_lib,
            'json': _json_lib,
        }

    @api.model
    def create(self, vals_list):
        """
            Create a new workflow automation record.

            Automatically updates the name, creates a cron job if needed,
            and refreshes the registry.

            Args:
                vals_list (dict): Values for record creation.

            Returns:
                recordset: Created record.
            """
        res = super().create(vals_list)
        res.name = f"{res.name}-({res.id})"
        res.create_cron()
        res._update_registry()
        return res

    def write(self, vals):
        """
            Update workflow automation record.

            Handles:
                - Validation for reusable workflows
                - Cron job updates
                - Registry refresh
                - Trigger function updates

            Args:
                vals (dict): Values to update.

            Returns:
                bool: True if update is successful.

            Raises:
                ValidationError: If attempting to deactivate a reused workflow.
            """
        # ── Guard: cannot deactivate a reusable automation that is in use ──
        # Only raises if active is explicitly set to False AND the automation
        # is reusable AND other active workflows depend on it.
        if vals.get('active') is False:
            for automation in self:
                if not automation.is_reusable:
                    continue
                dependents = automation.get_dependents()
                if dependents:
                    dep_names = ', '.join(d['name'] for d in dependents)
                    raise exceptions.ValidationError(_(
                        "Cannot deactivate '%(name)s' because it is used as a "
                        "reusable automation in the following active workflow(s): "
                        "%(deps)s. "
                        "Please remove or disconnect the 'Reuse Automation' node(s) "
                        "in those workflows first.",
                        name=automation.name,
                        deps=dep_names,
                    ))

        res = super().write(vals)
        time_fields = {
            'time_trigger_mode', 'time_trigger_time',
            'time_trigger_day', 'time_trigger_month', 'active',
        }
        if time_fields & vals.keys():
            self.create_cron()
        self._update_registry()
        if 'flow_data' in vals:
            self._update_primary_function()
        return res

    def _update_primary_function(self):
        """
            Update the primary trigger function of the workflow.

            Sets the first extracted trigger function as the main function.
            """
        for automation in self:
            function_ids = automation._extract_trigger_function_ids_from_flow(automation.flow_data)
            automation.function_id = function_ids[0] if function_ids else False

    def unlink(self):
        """
            Delete workflow automation record.

            Removes associated cron jobs and node structures before deletion.

            Returns:
                bool: Result of deletion.
            """
        self.mapped('schedule_id').sudo().unlink()
        self.mapped('node_struct_ids').unlink()
        return super().unlink()

    def _unregister_hook(self):
        """
        Unregister ORM patches installed by _register_hook().
        Restores patched methods by setting .origin back on ModelClass.
        Does NOT touch _onchange_methods — _register_hook cleans stale
        workflow handlers itself (tagged _is_workflow_automation=True)
        before re-appending, so no cleanup is needed here.
        """
        NAMES = self.env['work.function'].search([]).mapped('func_name')
        for Model in self.env.registry.values():
            ModelClass = type(Model)
            for name in NAMES:
                if name in ModelClass.__dict__:
                    try:
                        patched_fn = ModelClass.__dict__[name]
                        origin = getattr(patched_fn, 'origin', None)
                        if origin is not None:
                            setattr(ModelClass, name, origin)
                        else:
                            delattr(ModelClass, name)
                    except Exception:
                        pass

    def _update_registry(self):
        """
            Refresh the registry for workflow changes.

            Re-registers hooks and marks the registry as invalidated
            to apply updates.
            """
        if self.env.registry.ready:
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def create_cron(self):
        """
            Create or update scheduled actions for time-based triggers.

            Configures `ir.cron` records based on workflow timing settings
            such as hourly, daily, monthly, or yearly execution.
            """
        interval_map = {
            'hour':  (1,  'hours'),
            'day':   (1,  'days'),
            'month': (1,  'months'),
            'year':  (12, 'months'),
        }
        for rec in self:
            if rec.trigger_type != 'time' or not rec.time_trigger_mode:
                if rec.schedule_id:
                    rec.schedule_id.sudo().unlink()
                continue

            interval_number, interval_type = interval_map[rec.time_trigger_mode]

            now = fields.Datetime.now()
            hour = int(rec.time_trigger_time or 0)
            minute = round(((rec.time_trigger_time or 0) - hour) * 60)
            nextcall = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if rec.time_trigger_mode in ('month', 'year'):
                day = max(1, rec.time_trigger_day or 1)
                try:
                    nextcall = nextcall.replace(day=day)
                except ValueError:
                    import calendar
                    last_day = calendar.monthrange(nextcall.year, nextcall.month)[1]
                    nextcall = nextcall.replace(day=last_day)

            if rec.time_trigger_mode == 'year':
                month = max(1, min(12, rec.time_trigger_month or 1))
                try:
                    nextcall = nextcall.replace(month=month)
                except ValueError:
                    nextcall = nextcall.replace(month=month, day=1)

            if nextcall <= now:
                if interval_type == 'hours':
                    nextcall += relativedelta(hours=interval_number)
                elif interval_type == 'days':
                    nextcall += relativedelta(days=interval_number)
                elif interval_type == 'months':
                    nextcall += relativedelta(months=interval_number)

            cron_vals = {
                'name': f'Workflow Automation: {rec.name}',
                'model_id': self.env['ir.model']._get('work.auto').id,
                'state': 'code',
                'code': f"env['work.auto'].browse({rec.id})._run_time_trigger()",
                'interval_number': interval_number,
                'interval_type': interval_type,
                'nextcall': nextcall,
                'numbercall': -1,
                'active': rec.active,
                'user_id': self.env.ref('base.user_root').id,
            }

            if rec.schedule_id:
                rec.schedule_id.sudo().write(cron_vals)
            else:
                cron = self.env['ir.cron'].sudo().create(cron_vals)
                rec.sudo().write({'schedule_id': cron.id})

    def _run_time_trigger(self):
        """
            Execute workflow for time-based trigger.

            Invokes `_process` with 'time' trigger type if the workflow is active.
            """
        if not self.active:
            return
        try:
            self._process({'trigger_type': 'time'})
        except Exception as e:
            _logger.error(
                "Workflow Automation '%s' (id=%s) time trigger failed: %s",
                self.name, self.id, e,
            )

    def copy(self, default=None):
        """
            Duplicate a workflow automation.

            Creates a copy of the workflow along with its node structures
            and updates internal references.

            Args:
                default (dict, optional): Default values for the copy.

            Returns:
                recordset: Copied workflow record.
            """
        res = super().copy()
        res.name = f"{self.name}-copy({res.id})"
        if (self.flow_data.get('drawflow') and
                self.flow_data.get('drawflow').get('Home') and
                self.flow_data.get('drawflow').get('Home').get('data')):
            flow_data = self.flow_data.get('drawflow').get('Home').get('data')
            node_copies = []
            for nid, node in flow_data.items():
                copy_node = self.env["node.struct"].browse(node['data']['nodeId']).copy()
                node_copies.append(copy_node.id)
                node['data']['nodeId'] = copy_node.id
                node['html'] = f"{node['data']['name']}__{copy_node.id}"
            data = {'drawflow': {'Home': {'data': flow_data}}}
            res.flow_data = data
            res.node_struct_ids = node_copies
        return res

    @api.model
    def parse_view_and_fetch_functions(self, model_id):
        """
            Extract triggerable button functions from model views.

            Parses XML views to identify regular object buttons and Studio
            workflow buttons and collects their metadata.

            Args:
                model_id (int): ID of the model.

            Returns:
                list: List of dictionaries containing button function details.
            """
        button_functions = {}
        model = self.env["ir.model"].sudo().browse(model_id)
        model_name = model.model
        views = self.env['ir.ui.view'].sudo().search([('model', '=', model_name)])
        for view in views:
            arch = view.arch_base or view.arch_db
            if not arch:
                continue
            try:
                view_arch = etree.fromstring(arch.encode('utf-8'))
            except Exception:
                continue
            # Include:
            # 1. regular object buttons
            # 2. legacy workflow buttons saved as type='workflow'
            # 3. normalized Studio workflow buttons identified by studio_wf_ name prefix
            button_nodes = view_arch.xpath(
                "//button[@type='object' or @type='workflow' or starts-with(@name, 'studio_wf_')]"
            )
            for button in button_nodes:
                button_name = button.attrib.get('name')
                if button_name:
                    button_string = (
                        button.attrib.get('string', button_name) or
                        button.attrib.get('title', button_name)
                    )
                    field_in_button = button.xpath(".//field[@string]")
                    if field_in_button:
                        button_string = field_in_button[0].attrib.get('string', button_name)
                    unique_key = f"{button_name}_{button_string}"
                    button_context = button.attrib.get('context', button_name)
                    is_studio_workflow_button = button_name.startswith('studio_wf_')
                    if button_context == button_name or is_studio_workflow_button:
                        words = button_string.split('_')
                        formatted_name = " ".join(words).capitalize()
                        button_functions[unique_key] = {
                            'model': model_name,
                            'button_function': button_name,
                            'button_string': formatted_name,
                            'button_val': unique_key,
                        }
        return list(button_functions.values())
