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
import re
import logging

from io import StringIO
from lxml import etree

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.view_validation import valid_view

_logger = logging.getLogger(__name__)


class View(models.Model):
    """Extend ir.ui.view with Studio-specific logic."""
    _inherit = 'ir.ui.view'

    is_studio = fields.Boolean(string='Studio Field', default=False,
                               help="View created through Studio", ondelete='cascade')

    def _postprocess_access_rights(self, tree):
        """
        Apply group restrictions: elements with a 'groups' attribute should
        be removed from the view to people who are not members.

        Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views.
        """
        # Check if 'studio' is not in the debug session
        studio = request.session.studio
        is_not_studio_debug = '1' not in studio if studio else True
        # Check if the user is not part of the 'base.group_erp_manager' group
        is_not_erp_manager = not request.env.user.has_group('base.group_erp_manager')

        if is_not_studio_debug or is_not_erp_manager:
            return super()._postprocess_access_rights(tree)
        for node in tree.xpath('//*[@groups]'):
            attrib_groups = node.attrib.pop('groups')
            if node.tag == 't' and node.get('postprocess_added'):
                for child in reversed(node):
                    child_group = child.get("groups", "")
                    combined_groups = set(child_group.split(",") + attrib_groups.split(","))
                    combined_groups_str = ",".join(filter(None, combined_groups))
                    child.set("default_groups", attrib_groups)
                    node.addnext(child)
                node.getparent().remove(node)
            else:
                node.set("groups", attrib_groups)

        arch = etree.tostring(tree, encoding="unicode").replace(
            '\t', '')

        parser = etree.XMLParser()
        arch_tree = etree.parse(StringIO(arch), parser)
        elements = arch_tree.xpath("//*")
        for element in elements:
            xpath = arch_tree.getpath(element)
            for path in tree.xpath(f'//{xpath}'):
                path.set('cy-xpath', xpath)
                if tree.tag == "kanban" or (tree.tag == "form" and any(
                        parent.tag == "kanban" for parent in path.iterancestors())):
                    if path.get('t-if') or path.get('t-elif') or path.get('t-else'):
                        path.set('data-restrict', '1')
                    if path.tag == "div":
                        if 'ribbon' in path.get('class', ''):
                            path.set('class', f"{path.get('class', '').strip()}")
                            path.set('data-ribbon', '1')

                            for attr in ['invisible', 't-if', 't-elif', 't-else']:
                                val = path.attrib.pop(attr, None)
                                if val is not None:
                                    path.set(f"data-{attr}", val)

                            for child in path.iter():
                                for attr in ['invisible', 't-if', 't-elif', 't-else']:
                                    val = child.attrib.pop(attr, None)
                                    if val is not None:
                                        child.set(f"data-{attr}", val)
                        else:
                            path.set('data-drag', '1')

        if tree.tag == 'search':
            filters_without_context = tree.xpath('//filter[not(@context)]')
            filters_with_context = tree.xpath('//filter[@context]')
            last_filter_without_context = filters_without_context[-1] if filters_without_context else None
            last_filter_with_context = filters_with_context[-1] if filters_with_context else None
            new_element = etree.Element("studio")
            if last_filter_without_context is not None:
                new_element.set('filter', last_filter_without_context.get('cy-xpath'))
            if last_filter_with_context is not None:
                new_element.set('group_by', last_filter_with_context.get('cy-xpath'))

            tree.append(new_element)
        elif tree.tag == 'form':
            header = tree.xpath('//header')
            sheet = tree.xpath(".//sheet")
            if not sheet:
                new_sheet = etree.Element("sheet")
                new_sheet.set('cy-xpath', '/form/sheet')
                new_sheet.set('sheet', 'true')
                children_to_move = [child for child in tree if child.getparent() is tree and child.tag != "header"]
                for child in children_to_move:
                    new_sheet.append(child)
                tree.insert(0, new_sheet)
            if not header:
                new_header = etree.Element("header")
                new_header.set('cy-xpath', '/form/header')
                new_header.set('studio-header', f'/form/{tree[0].tag if tree else ""}')
                tree.insert(0, new_header)
            status_bar = tree.xpath('//header/field[@widget="statusbar"]') or tree.xpath(
                '//header/field[@widget="statusbar_duration"]')
            if status_bar:
                header = tree.xpath('//header')
                header[0].set('status-bar', 'true')
            avatar = tree.xpath('//sheet//field[contains(@class, "oe_avatar") and @widget="image"]')
            if avatar:
                sheet = tree.xpath('./sheet')
                sheet[0].set('avatar', 'true')

        for node in tree.xpath('//*[@groups]'):
            attrib_groups = node.attrib.get('groups')
            if node.tag == 't' and (not node.attrib or (len(node.attrib) == 2 and 'groups' in node.attrib)):
                for child in reversed(node):
                    node.addnext(child)
                node.getparent().remove(node)
                continue
            if attrib_groups and not self.user_has_groups(attrib_groups):
                if tree.tag in ['tree', 'kanban'] and request.session.get('invisible', 'False') != "False":
                    node.set('striped', 'true')
                elif tree.tag == 'form' and request.session.get('invisible', 'False') != "False":
                    if node.tag == 'div' and 'class' in node.attrib and 'o_row' in node.attrib['class'].split():
                        node.set('class', f"{node.attrib['class']} cy-studio-striped")
                    else:
                        node.set('striped', 'true')
                elif tree.tag == 'search' and request.session.get('show_invisible_search'):
                    node.set('striped', 'true')
                elif tree.tag == 'search' and node.tag == 'searchpanel':
                    node.set('isInvisible', 'true')
                else:
                    node.getparent().remove(node)
                    continue
                # ToDO Need to find better way for handle default group fields.
                if 'model_access_rights' in node.attrib:
                    node.getparent().remove(node)

        if tree.tag == 'form':
            button_box = tree.findall(".//div[@class='oe_button_box']")
            button_box_child = []
            for box in button_box:
                child = box.findall(".//button")
                if child:
                    button_box_child.append(child)
            if not button_box_child:
                new_button_box = etree.Element("div")
                new_button_box.set('cy-xpath', '//form/sheet/div[@class="oe_button_box"]')
                new_button_box.set('class', 'oe_button_box')
                new_button_box.set('name', 'button_box')
                child_div = etree.Element("div")
                child_div.set('class', 'button-box-container')
                new_button_box.append(child_div)
                sheet = tree.xpath('./sheet')
                form = tree.xpath('./form')
                if sheet:
                    sheet[0].insert(0, new_button_box)
        base_model = tree.get('model_access_rights')
        for node in tree.xpath('//*[@model_access_rights]'):
            model = self.env[node.attrib.pop('model_access_rights')]
            if node.tag == 'field':
                can_create = model.check_access_rights('create',
                                                       raise_exception=False)
                can_write = model.check_access_rights('write',
                                                      raise_exception=False)
                node.set('can_create', str(bool(can_create)))
                node.set('can_write', str(bool(can_write)))
            else:
                is_base_model = base_model == model._name
                for action, operation in (
                        ('create', 'create'), ('delete', 'unlink'),
                        ('edit', 'write')):
                    if not node.get(action) and not model.check_access_rights(
                            operation, raise_exception=False):
                        node.set(action, 'False')
                if node.tag == 'kanban':
                    group_by_name = node.get('default_group_by')
                    group_by_field = model._fields.get(group_by_name)
                    if group_by_field and group_by_field.type == 'many2one':
                        group_by_model = model.env[group_by_field.comodel_name]
                        for action, operation in (
                                ('group_create', 'create'),
                                ('group_delete', 'unlink'),
                                ('group_edit', 'write')):
                            if not node.get(
                                    action) and not group_by_model.check_access_rights(
                                operation, raise_exception=False):
                                node.set(action, 'False')

        return tree

    def _get_x2many_missing_view_archs(self, field, field_node, node_info):
        """Add model and view info for x2many fields."""
        result = super()._get_x2many_missing_view_archs(field, field_node, node_info)
        field_node.set('model', f'{field.comodel_name}')
        for _, view in result:
            field_node.set(f'{view.type}', f'{view.id}')
        return result

    # Overriding this method to fix the issue in the tree view drag and drop,adding help parameter
    @api.constrains('arch_db')
    def _check_xml(self):
        """Validate Studio views and ensure XML correctness."""
        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        partial_validation = self.env.context.get('ir_ui_view_partial_validation')
        self = self.with_context(validate_view_ids=(self._ids if partial_validation else True))
        for view in self:
            try:
                # verify the view is valid xml and that the inheritance resolves
                if view.inherit_id:
                    view_arch = etree.fromstring(view.arch)
                    view._valid_inheritance(view_arch)
                combined_arch = view._get_combined_arch()
                if view.type == 'qweb':
                    continue
            except (etree.ParseError, ValueError) as e:
                err = ValidationError(_(
                    "Error while parsing or validating view:\n\n%(error)s",
                    error=tools.ustr(e),
                    view=view.key or view.id,
                )).with_traceback(e.__traceback__)
                err.context = getattr(e, 'context', None)
                raise err from None
            try:
                # verify that all fields used are valid, etc.
                view._validate_view(combined_arch, view.model)
                combined_archs = [combined_arch]

                if combined_arch.xpath('//*[@attrs]') or combined_arch.xpath('//*[@states]'):
                    view_name = f'{view.name} ({view.xml_id})' if view.xml_id else view.name
                    err = ValidationError(
                        _('Since 17.0, the "attrs" and "states" attributes are no longer used.\nView: %(name)s in %(file)s',
                          name=view_name, file=view.arch_fs
                          ))
                    err.context = {'name': 'invalid view'}
                    raise err

                if combined_archs[0].tag == 'data':
                    # A <data> element is a wrapper for multiple root nodes
                    combined_archs = combined_archs[0]
                for view_arch in combined_archs:

                    if view_arch.tag == "activity":
                        # Remove the 'delete' attribute from the root if it exists
                        if view_arch.attrib.get('delete'):
                            del view_arch.attrib['delete']

                    for node in view_arch.xpath('//*[@__validate__]'):
                        del node.attrib['__validate__']

                    check = valid_view(view_arch, env=self.env, model=view.model)
                    if not check and view.type != 'tree':
                        view_name = f'{view.name} ({view.xml_id})' if view.xml_id else view.name
                        raise ValidationError(_(
                            'Invalid view %(name)s definition in %(file)s',
                            name=view_name, file=view.arch_fs
                        ))
            except ValueError as e:
                if hasattr(e, 'context'):
                    lines = etree.tostring(combined_arch, encoding='unicode').splitlines(keepends=True)
                    fivelines = "".join(lines[max(0, e.context["line"] - 3):e.context["line"] + 2])
                    err = ValidationError(_(
                        "Error while validating view near:\n\n%(fivelines)s\n%(error)s",
                        fivelines=fivelines, error=tools.ustr(e),
                    ))
                    err.context = e.context
                    raise err.with_traceback(e.__traceback__) from None
                else:
                    err = ValidationError(_(
                        "Error while validating view (%(view)s):\n\n%(error)s", view=self.key or self.id,
                        error=tools.ustr(e.__context__),
                    ))
                    err.context = {'name': 'invalid view'}
                    raise err.with_traceback(e.__context__.__traceback__) from None
        return True


class Model(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        Hide Chatter Views, Tabs, Buttons, Fields, Duplicate option, Filters,
        Groups and set readonly the user profile(preference) based on the
        access manager
         """

        views = ["tree", "form", "kanban", 'calendar', 'activity', 'hierarchy', 'graph', 'pivot']

        if type(self).__name__ == 'ir.model.access' or type(self).__name__ == 'ir.rule':
            views.remove('tree')
        if type(self).__name__ == 'mail.template':
            views.remove('kanban')
            views.remove("form")
        if type(self).__name__ == 'ir.actions.report':
            views.remove('kanban')

        result = super().get_view(view_id, view_type, **options)
        studio = request.session.studio
        is_not_studio_debug = '1' not in studio if studio else True
        is_not_erp_manager = not request.env.user.has_group('base.group_erp_manager')

        if is_not_studio_debug or is_not_erp_manager:
            return result
        if view_type in views:
            xml_string = re.sub(r'\s+js_class="[^"]*"', '', result['arch'])
            xml_string = re.sub(r'(<group[^>]*?)\s+col="4"', r'\1', xml_string)
            xml_string = re.sub(r'<t[^>]*groups="stock.group_stock_manager"[^>]*>.*?</t>', '', xml_string,
                                flags=re.DOTALL)

            result['arch'] = xml_string
        return result