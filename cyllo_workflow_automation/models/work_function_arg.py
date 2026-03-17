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
import os
import types
from collections import defaultdict
import logging

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

    name = fields.Char(
        'Arg name',
        default='arg'
    )
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
            decorator (Char): The name of the Odoo decorator (e.g., `@api.model`, `@api.multi`, etc.).
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
    arg_ids = fields.One2many(
        'work.function.arg',
        'function_id'
    )
    process_ids = fields.One2many(
        'work.process.arg',
        'function_id'
    )
    has_return = fields.Boolean(
        'Has return',
        default=True
    )
    c_make_function = fields.Text(
        'Make Function',
        compute='compute_c_make_function', store=True
    )
    mode = fields.Selection(
        [
            ('manual', 'Manual'),
            ('auto', 'Auto')
        ],
        'mode',
        compute='compute_c_make_function'
    )
    trigger_type = fields.Selection(
        [
            ('create', 'On create'),
            ('time', 'At a time'),
            ('new_action', 'New Action'),
            ('field_change', 'On change'),
            ('other', 'Other functions'),
        ],
        default='other'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    icon = fields.Binary()

    @api.constrains('icon')
    def _check_icon_file_type(self):
        """
            Ensures that the uploaded icon is a valid SVG file.

            The method decodes the base64 content of the uploaded file and checks
            if it starts with the SVG header or contains the <svg> tag. If these
            conditions are not met, a ValidationError is raised.
        """
        for record in self:
            if record.icon:
                try:
                    # Decode the base64 content
                    file_content = base64.b64decode(record.icon)
                    # Check if it starts with the SVG header
                    if not file_content.startswith(b'<?xml') and not file_content.startswith(b'<svg'):
                        raise exceptions.ValidationError("The uploaded file is not a valid SVG.")
                    # Additional check: look for <svg tag in the first 1000 bytes
                    if b'<svg' not in file_content[:1000]:
                        raise exceptions.ValidationError("The uploaded file does not appear to be a valid SVG.")
                except:
                    raise exceptions.ValidationError("Unable to verify the file. Please ensure it's a valid SVG.")

    @api.depends(
        'func_name',
        'make_function',
        'arg_ids',
        'process_ids',
        'has_return'
    )
    def compute_c_make_function(self):
        """
            Automatically generates the function code if 'make_function' is not provided.

            This method builds a Python function using the provided `func_name`, `arg_ids`, and
            process details, and stores the result in the `c_make_function` field. The function
            can be set in 'manual' mode (where `make_function` is provided) or 'auto' mode (where
            the function is generated automatically).
        """
        for rec in self:
            if rec.make_function:
                rec.c_make_function = rec.make_function
                rec.mode = 'manual'
                continue
            rec.mode = 'auto'
            args = ','.join(rec.arg_ids.mapped('name')) if rec.arg_ids else ''
            process_before = process_after = '{'
            process_before += f"'records': self,"
            process_after += f"'records': self,"
            process_before += '}'
            process_after += '}'
            decorator = f'@api.{rec.decorator}' if rec.decorator else ''
            make_function = f'''
            def make_{rec.func_name}():
                {decorator}
                def {rec.func_name}(self{',' if args else ''}{args}):
                    automation_ids = self.env['work.auto']._get_actions(self, '{rec.func_name}')
                    if not automation_ids:
                        return {rec.func_name}.origin(self{',' if args else ''}{args})
                    before_ids = automation_ids.filtered(lambda x: x.ttype == 'before')
                    for automation in before_ids.with_context(old_values=None):
                        automation._process({process_before})
                    res = {rec.func_name}.origin(self.with_env(automation_ids.env){',' if args else ''}{args})
                    after_ids = automation_ids - before_ids
                    for automation in after_ids.with_context(old_values=None):
                        automation._process({process_after})
                    {'return res' if rec.has_return else ''}
                return {rec.func_name}
            '''
            rec.c_make_function = make_function.strip()


class WorkAuto(models.Model):
    _name = "work.auto"
    _inherit = ['image.mixin']

    name = fields.Char("Name")
    function_id = fields.Many2one('work.function')
    model_id = fields.Many2one('ir.model', ondelete="cascade")
    active = fields.Boolean(
        "Active",
        default=True
    )
    code = fields.Text('Code')
    imports = fields.Json("Imports")
    trigger_type = fields.Selection(related='function_id.trigger_type')
    ttype = fields.Selection(
        [
            ('before', 'Before'),
            ('after', 'After')
        ],
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
    node_struct_ids = fields.One2many(
        'node.struct',
        'work_auto_id'
    )
    image_1920 = fields.Binary(
        string="Image 1920",
        default=lambda self: self.getDefaultImage1920()
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        default=lambda self: self.env.company)
    is_record_saved = fields.Boolean(default=False)

    def save_data(self, data, name, ttype, **kwargs):
        """
            Save or update workflow automation data for a given model.

            This function either creates a new record or updates an existing one based on the presence of `self`.
            It takes various parameters to store or update flow information, including model ID, function ID,
            image, code, and variables.

            Args:
                data (dict): Workflow automation data to be saved.
                name (str): Name of the workflow automation.
                ttype (bool): Type flag indicating whether the flow is executed before or after an event.
                **kwargs: Additional parameters including:
                    - model_id (int): ID of the model associated with the workflow.
                    - function_id (int): ID of the function to be triggered.
                    - image (str): Base64-encoded image string (e.g., a workflow diagram).
                    - code (str): Code associated with the workflow.
                    - variables (list): List of variables to be used in the workflow.
            Returns:
                tuple: ID of the saved workflow automation record.
            """
        workflow_auto_id = self or False
        img = kwargs.get('image', False)
        t_ttype = 'before' if ttype else 'after'
        trigger_function_ids = kwargs.get('trigger_function_ids', []) or []
        trigger_commands = [(6, 0, trigger_function_ids)] if trigger_function_ids else [(6, 0, [])]
        target_function = trigger_function_ids[0] if trigger_function_ids else False
        values = {
            'flow_data': data,
            'model_id': kwargs.get('model_id', False),
            'code': kwargs.get('code', False),
            'variables': kwargs.get('variables', []),
            'ttype': t_ttype,
            'is_record_saved': True,
            'trigger_function_ids': trigger_commands,
            'function_id': target_function,
        }
        if not self:
            workflow_auto_id = self.create(values)
        else:
            values.update({'name': name})
            self.write(values)
        return workflow_auto_id.id

    def clear_all_nodes(self):
        """
        Clear all node structures related to the current workflow automation.

        This function deletes all node structure records by iterating over the `node_struct_ids` and
        applying the Odoo command to remove them.
        """
        self.node_struct_ids.unlink()
        return

    def update_flow_data(self, flow_data):
        """
        Update the flow data of the current workflow automation.

        Args:
            flow_data (dict): The updated flow data that needs to be set for the workflow.

        Returns:
            int: The ID of the updated workflow automation record.
        """
        self.flow_data = flow_data
        return self.id

    @staticmethod
    def _extract_trigger_function_ids_from_flow(flow_data):
        """
        Helper to extract unique trigger function ids from the drawflow data.
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
            if data.get('type') != 'action':
                continue
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
            if isinstance(func_id, int):
                function_ids.append(func_id)
                if trigger_type:
                    seen_trigger_types.add(trigger_type)
        # preserve insertion order while removing duplicates
        return list(dict.fromkeys(function_ids))

    @api.depends('flow_data')
    def _compute_trigger_functions(self):
        for automation in self:
            function_ids = automation._extract_trigger_function_ids_from_flow(automation.flow_data)
            automation.trigger_function_ids = self.env['work.function'].browse(function_ids)

    @api.constrains('trigger_function_ids')
    def _check_unique_trigger_types(self):
        for automation in self:
            trigger_types = [
                fn.trigger_type for fn in automation.trigger_function_ids if fn.trigger_type
            ]
            duplicates = [t for t in set(trigger_types) if trigger_types.count(t) > 1]
            if duplicates:
                duplicate_type = duplicates[0]
                trigger = automation.trigger_function_ids.filtered(lambda f: f.trigger_type == duplicate_type)
                trigger_name = trigger and trigger[0].name or duplicate_type
                raise exceptions.ValidationError(
                    _("Trigger %s is already part of this automation. Each trigger type can only be used once.") % trigger_name
                )

    def initial_model_setup(self):
        """
        Set up initial data for model and search nodes in the workflow automation.

        This function identifies nodes with the name 'model' or 'Search' and constructs a list of dictionaries
        that contain relevant details such as the node ID, model ID, and type ('primary' for model nodes and
        'Search' for search nodes).

        Returns:
            list: A list of dictionaries representing the initial model setup data.
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
        Retrieve the default image for the workflow automation record in base64 format.

        This function reads an SVG file located in the static folder and returns its content encoded in base64.

        Returns:
            str: Base64 encoded string of the default SVG image.
        """
        current_directory = os.path.dirname(os.path.realpath(__file__))
        relative_path = os.path.join(current_directory, 'static/src/img/Record/default_record.svg')
        with file_open(
                'cyllo_workflow_automation/static/src/img/Record/default_record.svg',
                'rb') as svg_file:
            svg_data = svg_file.read()
            return base64.b64encode(svg_data).decode('utf-8')

    def _register_hook(self):
        """
            Register a hook that patches methods or adds automation to models based on defined triggers.

            This method is responsible for applying dynamic patches to models when specific conditions are met,
            such as when a field changes or time-based triggers are activated. The method either patches a function
            on a model or registers an onchange handler, depending on the trigger type.

            A helper function `patch` is defined inside to ensure methods are only patched once per model.

            The following trigger types are handled:
            - 'field_change': Automatically processes changes on specified fields by adding onchange handlers.
            - 'time': (Currently a placeholder).
            - Other custom function triggers: Executes the custom function stored in `function_id`.

            Args:
                None (The function works on the model's records directly).

            Returns:
                tuple: Result from the superclass `_register_hook()` method call.

            Helper Functions:
                patch(model, name, method):
                    Patches the method `name` on the `model` unless it has already been patched.

            """
        patched_models = defaultdict(set)

        def patch(model, name, method):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = type(model)
                method.origin = getattr(ModelClass, name)
                setattr(ModelClass, name, method)

        for auto in self.with_context({}).search([]):
            functions = auto.trigger_function_ids
            if not functions:
                continue
            Model = self.env.get(auto.model_id.model)
            if Model is None:
                _logger.warning(
                    "Automation rule with name '%s' (ID %d) depends on model %s",
                    auto.name,
                    auto.id,
                    auto.model_id.model if auto.model_id else 'unknown')
                continue

            field_change_functions = functions.filtered(lambda f: f.trigger_type == 'field_change')
            if field_change_functions:
                if not auto.field_id:
                    continue

                def make_onchange_fn(auto_id, field_name):
                    def on_change_field(rec):
                        auto_live = auto_id.with_env(rec.env)
                        try:
                            with rec.env.cr.savepoint():
                                auto_live._process({'record': rec})
                        except exceptions.ValidationError:
                            raise  # Surface user-facing warnings to the form
                        except Exception as e:
                            _logger.error(
                                "Field-change onchange %r failed for %s: %s",
                                field_name, rec.id, e)
                    return on_change_field

                Model._onchange_methods[auto.field_id.name].append(
                    make_onchange_fn(auto, auto.field_id.name))

            for function in functions.filtered(lambda f: f.trigger_type not in ('field_change', 'time')):
                if not function.c_make_function:
                    continue
                code_obj = compile(function.c_make_function, '<string>', 'exec')
                func = types.FunctionType(code_obj.co_consts[0], globals(),
                                          function.func_name)()
                patch(Model, function.func_name, func)
        return super()._register_hook()

    @api.model
    def _get_actions(self, record, func):
        """
            Retrieve automation records associated with a specific model and function.

            This method searches for workflow automation records that match the provided model (based on the `record`)
            and function name (`func`). It uses the model name to identify the corresponding model ID and then searches
            for functions with the matching function name. If both the model and function are found, it returns the
            automation records related to that combination.

            Args:
                record (model instance): The record instance whose model is used for searching automation actions.
                func (str): The name of the function to search for within the workflow automation functions.

            Returns:
                recordset: The automation records (`auto_ids`) that match the given model and function.
                If no matching model or function is found, it returns an empty recordset.
            """
        model_id = self.env['ir.model'].sudo().search([
            ('model', '=', record._name)
        ], limit=1)
        function_id = self.env['work.function'].search([
            ('model_id', 'in', [model_id.id, False]),
            ('func_name', '=', func)
        ], limit=1)
        if not model_id or not function_id:
            return self
        auto_ids = self.search([
            ('model_id', '=', model_id.id),
            ('trigger_function_ids', 'in', function_id.ids)
        ])
        return auto_ids

    def _process(self, args: dict):
        """
           Execute the workflow automation by processing the provided arguments and running the associated code.

           This method checks if records are provided in the `args` dictionary, verifies write access for those records,
           and executes the code defined in the workflow automation within a modified context. The method also handles
           access errors and exceptions during code execution.

           Args:
               args (dict): A dictionary containing key-value pairs that are passed into the workflow process. It may include:
                   - 'records' (recordset): The records to process. If present, the method checks the write access for these records.
                   - Other custom key-value pairs which are merged into the execution context.

           Raises:
               AccessError: If the user does not have write access to the provided records.
               ValidationError: If any exception occurs during the execution of the workflow code.

           Returns:
               None: The function executes the workflow code, but does not return a value.
        """
        stack = args.get('__workflow_stack__', [])
        if not isinstance(stack, list):
            stack = list(stack)
        if self.id in stack:
            raise exceptions.ValidationError(
                _('Circular automation reuse detected for %s. Review nested reusable nodes to avoid recursion.', self.name)
            )
        stack = [*stack, self.id]
        args = dict(args, __workflow_stack__=stack)

        records = args.get('records', False)
        if records:
            try:
                records.check_access_rule('write')
            except AccessError:
                _logger.warning(
                    "Forbidden action %r executed while the user %s does not have access to %s.",
                    self.name, self.env.user.login, records)
                raise
        # When called from a field_change onchange, args carries a single
        # 'record' key.  The generated Python preamble checks for 'records'
        # (plural) and assigns current_record from it.  Inject both aliases
        # so the condition and action nodes see the triggering record correctly.
        single_record = args.get('record', False)
        if single_record and not records:
            args = dict(args)
            args['records'] = single_record
            args['current_record'] = single_record
        context = self.get_context()
        context.update(args)
        context.update(_BUILTINS)
        if self.code:
            code_obj = compile(self.code.strip(), "", 'exec')
            try:
                eval(code_obj, context, {})
            except Exception as e:
                raise exceptions.ValidationError(e)

    def get_context(self):
        """
         Prepare and return the execution context for workflow automation.

         This method constructs a context dictionary that contains important variables and objects
         needed for the execution of the workflow automation code. The context includes the environment,
         the model being processed, user information, exception classes, and utility libraries for time
         and date handling.

         Returns:
             dict: A dictionary containing the following keys:
                 - 'env': The Odoo environment (self.env).
                 - 'model': The model corresponding to `self.model_id`.
                 - 'UserError': Reference to Odoo's `UserError` exception class.
                 - 'ValidationError': Reference to Odoo's `ValidationError` exception class.
                 - 'uid': The user ID of the current user (`self._uid`).
                 - 'user': The current user (`self.env.user`).
                 - 'time': Safe access to the `time` module.
                 - 'datetime': Safe access to the `datetime` module.
                 - 'dateutil': Safe access to the `dateutil` module.
                 - '_logger': Logger object for logging information or warnings.
         """
        model = self.env[self.model_id.sudo().model]
        return {
            'env': self.env,
            'model': model,
            'UserError': exceptions.UserError,
            'ValidationError': exceptions.ValidationError,
            'uid': self._uid,
            'user': self.env.user,
            'time': tools.safe_eval.time,
            'datetime': tools.safe_eval.datetime,
            'dateutil': tools.safe_eval.dateutil,
            '_logger': _logger,
        }

    @api.model
    def create(self, vals_list):
        """
        Override the create method to customize the creation of records.

        This method creates a new record, appends the record ID to the name, and triggers
        additional actions such as creating a cron job and updating the registry.

        Args:
            vals_list (dict): The values used to create the new record.

        Returns:
            recordset: The newly created record with updated name and other post-creation actions.
        """
        res = super().create(vals_list)
        res.name = f"{res.name}-({res.id})"
        res.create_cron()
        res._update_registry()
        return res

    def write(self, vals):
        """
        Override the write method to update records and trigger a registry update.

        Also re-syncs the linked ir.cron whenever any time-trigger field or the
        `active` flag changes, so the scheduled job always reflects the latest
        configuration.

        Args:
            vals (dict): A dictionary of values used to update the record.

        Returns:
            bool: True if the write operation was successful.
        """
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
        for automation in self:
            function_ids = automation._extract_trigger_function_ids_from_flow(automation.flow_data)
            automation.function_id = function_ids[0] if function_ids else False

    def unlink(self):
        """
        Override unlink to remove any linked ir.cron jobs before deleting the
        automation record, preventing orphaned scheduled actions.

        Returns:
            bool: True if the unlink operation was successful.
        """
        self.mapped('schedule_id').sudo().unlink()
        self.mapped('node_struct_ids').unlink()
        return super().unlink()

    def _unregister_hook(self):
        """
        Unregister patches installed by the `_register_hook` method.

        This method removes dynamic method patches applied to models by the `_register_hook` method.
        It loops through all models and removes methods that match the function names in the `work.function` model.

        Returns:
            None
        """
        NAMES = self.env['work.function'].search([]).mapped('func_name')
        for Model in self.env.registry.values():
            for name in NAMES:
                try:
                    delattr(Model, name)
                except Exception as exp:
                    pass

    def _update_registry(self):
        """
        Update the Odoo registry by unregistering and re-registering patches.

        This method checks if the registry is ready, unregisters the existing hooks, re-registers them,
        and invalidates the registry to ensure the updates are applied.

        Returns:
            None
        """
        if self.env.registry.ready:
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def create_cron(self):
        """
        Create or update an ir.cron scheduled action for time-based workflow
        automations.

        Called automatically on record creation and whenever time-trigger fields
        are modified. Only acts on automations whose linked trigger has
        `trigger_type == 'time'` and whose `time_trigger_mode` is set.

        Interval mapping:
            - 'hour'  → every 1 hour
            - 'day'   → every 1 day
            - 'month' → every 1 month
            - 'year'  → every 12 months

        The `nextcall` datetime is computed from `time_trigger_time` (a float
        representing hours, e.g. 14.5 = 14:30). For monthly/yearly modes,
        `time_trigger_day` and `time_trigger_month` are also applied. If the
        computed nextcall is in the past it is advanced by one interval.
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

            # Build nextcall from time_trigger_time (float hours, e.g. 14.5 → 14:30)
            now = fields.Datetime.now()
            hour = int(rec.time_trigger_time or 0)
            minute = round(((rec.time_trigger_time or 0) - hour) * 60)
            nextcall = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if rec.time_trigger_mode in ('month', 'year'):
                day = max(1, rec.time_trigger_day or 1)
                try:
                    nextcall = nextcall.replace(day=day)
                except ValueError:
                    # Day out of range for the current month — clamp to last day
                    import calendar
                    last_day = calendar.monthrange(nextcall.year, nextcall.month)[1]
                    nextcall = nextcall.replace(day=last_day)

            if rec.time_trigger_mode == 'year':
                month = max(1, min(12, rec.time_trigger_month or 1))
                try:
                    nextcall = nextcall.replace(month=month)
                except ValueError:
                    nextcall = nextcall.replace(month=month, day=1)

            # If nextcall is already in the past, advance by one interval
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
        Entry point called by the ir.cron scheduled action for time-based
        workflow automations.

        Executes the automation's generated Python code via `_process`. Errors
        are caught and logged so that a single failure does not prevent future
        cron runs.
        """
        if not self.active:
            return
        try:
            self._process({})
        except Exception as e:
            _logger.error(
                "Workflow Automation '%s' (id=%s) time trigger failed: %s",
                self.name, self.id, e,
            )

    def copy(self, default=None):
        """
        Override the copy method to duplicate a record and its associated node structure.

        This method creates a duplicate of the current record, appending "-copy(ID)" to the new record's name.
        It also duplicates the node structure (`node.struct` records) associated with the original record, updating
        the flow data with references to the new node copies.

        Args:
            default (dict, optional): Optional default values to override in the new record.

        Returns:
            recordset: The newly created copy of the record with updated name, flow data, and node structure.
        """
        res = super().copy()
        res.name = f"{self.name}-copy({res.id})"
        if self.flow_data.get('drawflow') and self.flow_data.get('drawflow').get('Home') and self.flow_data.get(
                'drawflow').get('Home').get('data'):
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
        Parse views of a specific model to extract custom button functions.

        This method searches for all views associated with a given model, extracts any object buttons
        (buttons with type="object"), and collects their function names and display strings.
        It returns a list of button functions, formatted for easy reference.

        Args:
            model_id (int): The ID of the model whose views and functions are to be parsed.

        Returns:
            list: A list of dictionaries containing button function information, including:
                - 'model': The name of the model.
                - 'button_function': The technical name of the button function.
                - 'button_string': A formatted string for display purposes.
        """
        button_functions = {}
        model = self.env["ir.model"].sudo().browse(model_id)
        model_name = model.model
        # Get views related to the model
        views = self.env['ir.ui.view'].sudo().search([('model', '=', model_name)])
        # Parse each view
        for view in views:
            view_arch = etree.fromstring(view.arch_db)
            # Only consider top-level buttons, avoiding buttons in nested (one2many, etc.) views
            for button in view_arch.xpath("//button[@type='object'][not(ancestor::tree)]"):
                button_name = button.attrib.get('name')
                if button_name:
                    button_string = button.attrib.get('string', button_name) or button.attrib.get('title', button_name)
                    field_in_button = button.xpath(".//field[@string]")
                    if field_in_button:
                       button_string = field_in_button[0].attrib.get('string', button_name)  # Get the 'string' from the field
                    unique_key = f"{button_name}_{button_string}"
                    button_context = button.attrib.get('context', button_name)
                    if button_context == button_name :
                        words = button_string.split('_')
                        formatted_name = " ".join(words).capitalize()
                        button_functions[unique_key] = {
                            'model': model_name,
                            'button_function': button_name,
                            'button_string': formatted_name,
                            'button_val':unique_key,
                        }
        return list(button_functions.values())
